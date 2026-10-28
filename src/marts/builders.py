"""Builders: staging, SCD Type 2 dimensions, and incremental facts.

Design decisions (see docs/architecture.md for trade-offs):
- Staging is a pure rename/projection pass: no business logic, so a
  staging failure can only be a mapping failure, never a logic bug.
- SCD2 keeps exactly one current row per business key. A tracked
  attribute change closes the old row (``valid_to`` set, ``is_current``
  cleared) and opens a new one; an unchanged re-run is a no-op, which
  makes full rebuilds and incremental runs converge on the same state.
- Facts merge on ``grain_key``: re-running a fact build with the same
  input replaces rows instead of duplicating them (idempotent merge).
- Surrogate keys are sequential integers assigned in business-key
  order, so builds are deterministic across runs and machines.
"""

from __future__ import annotations

from .models import Model, ModelKind
from .store import Store

END_OF_TIME = "9999-12-31"


def _line_total(row: dict) -> float:
    return round(float(row["quantity"]) * float(row["unit_price"]) - float(row.get("discount", 0)), 2)


def _order_total(row: dict) -> float:
    return round(float(row["quantity"]) * float(row["unit_price"]), 2)


MEASURES = {"line_total": _line_total, "order_total": _order_total}


def merge_rows(existing: list[dict], incoming: list[dict], key: str) -> list[dict]:
    """Merge ``incoming`` into ``existing`` keyed by ``key``.

    Rows sharing a key are replaced (newest wins); new keys append.
    Order is preserved: original rows keep their position, appended
    rows follow in incoming order. Pure function, heavily tested.
    """
    index = {row[key]: i for i, row in enumerate(existing)}
    merged = list(existing)
    for row in incoming:
        if row[key] in index:
            merged[index[row[key]]] = row
        else:
            index[row[key]] = len(merged)
            merged.append(row)
    return merged


def _build_staging(model: Model, store: Store) -> list[dict]:
    if len(model.depends_on) != 1:
        raise ValueError(f"staging model {model.name!r} needs exactly one dependency")
    rows = store.get(model.depends_on[0])
    out = []
    for row in rows:
        new = {}
        for col, value in row.items():
            new[model.renames.get(col, col)] = value
        out.append(new)
    return out


def _build_dimension(model: Model, store: Store, effective_date: str) -> list[dict]:
    if len(model.depends_on) != 1 or not model.business_key:
        raise ValueError(f"dimension {model.name!r} needs one dependency and a business_key")
    incoming = sorted(store.get(model.depends_on[0]), key=lambda r: str(r[model.business_key]))
    existing = store.get(model.name) if store.has(model.name) else []
    by_key: dict[str, list[dict]] = {}
    for row in existing:
        by_key.setdefault(str(row[model.business_key]), []).append(row)
    next_sk = 1 + max((int(r["surrogate_key"]) for r in existing), default=0)
    result = [dict(r) for r in existing]
    current_index = {str(r[model.business_key]): r for r in result if r.get("is_current")}
    for row in incoming:
        key = str(row[model.business_key])
        current = current_index.get(key)
        if current is not None:
            changed = any(current.get(attr) != row.get(attr) for attr in model.tracked_attributes)
            if not changed:
                continue  # unchanged: SCD2 no-op, keeps history stable
            current["valid_to"] = effective_date
            current["is_current"] = False
        new_row = dict(row)
        new_row["surrogate_key"] = next_sk
        next_sk += 1
        new_row["valid_from"] = effective_date
        new_row["valid_to"] = END_OF_TIME
        new_row["is_current"] = True
        result.append(new_row)
        current_index[key] = new_row
    return result


def _build_fact(model: Model, store: Store) -> list[dict]:
    if not model.depends_on:
        raise ValueError(f"fact model {model.name!r} needs a staging dependency")
    # depends_on[0] is the staging input; later entries are dimensions
    # already built before this model (see DAG ordering in catalog).
    rows = store.get(model.depends_on[0])
    # Resolve business keys to current surrogate keys, once per
    # dimension. Dimensions stamp their business-key value in "_bk"
    # at build time (see _build_dimension), so fact lookups do not
    # need to know the dimension's business-key column name.
    lookups: dict[str, dict[str, int]] = {}
    for input_col, dim_name in model.dimension_lookups.items():
        mapping = {}
        for dim_row in store.get(dim_name):
            if dim_row.get("is_current"):
                mapping[str(dim_row.get("_bk", ""))] = dim_row["surrogate_key"]
        lookups[input_col] = mapping
    out = []
    for row in rows:
        new = dict(row)
        for input_col, dim_name in model.dimension_lookups.items():
            sk = lookups[input_col].get(str(row.get(input_col)))
            if sk is None:
                raise ValueError(
                    f"fact {model.name!r}: no current {dim_name} row for "
                    f"{input_col}={row.get(input_col)!r} (referential break)"
                )
            new[f"{input_col}_sk"] = sk
        for out_col, (inputs, fn_name) in model.measures.items():
            if fn_name not in MEASURES:
                raise ValueError(f"unknown measure {fn_name!r}")
            new[out_col] = MEASURES[fn_name](row)
        out.append(new)
    if model.grain_key and store.has(model.name):
        return merge_rows(store.get(model.name), out, model.grain_key)
    return out


def build_model(model: Model, store: Store, effective_date: str = "2026-10-28") -> list[dict]:
    """Build one model and store the result. Returns the built rows."""
    if model.kind == ModelKind.STAGING:
        rows = _build_staging(model, store)
    elif model.kind == ModelKind.DIMENSION:
        rows = _build_dimension(model, store, effective_date)
        # Stamp the business-key value on each row so fact lookups can
        # resolve it without knowing the dimension's column name.
        for r in rows:
            r["_bk"] = str(r.get(model.business_key, ""))
    elif model.kind == ModelKind.FACT:
        rows = _build_fact(model, store)
    else:
        raise ValueError(f"cannot build kind {model.kind!r} for {model.name!r}")
    store.put(model.name, rows)
    return rows
