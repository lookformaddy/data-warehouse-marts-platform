import pytest

from marts.builders import build_model, merge_rows
from marts.catalog import SOURCES, default_models
from marts.dag import plan
from marts.models import Model, ModelKind
from marts.seed import seed_v1, seed_v2_changes
from marts.store import Store


def _built_store():
    store = Store()
    seed_v1(store)
    for m in plan(default_models(), external=SOURCES):
        build_model(m, store, "2026-10-20")
    return store


def test_scd2_opens_new_version_and_closes_old():
    store = _built_store()
    seed_v2_changes(store)
    for m in plan(default_models(), external=SOURCES):
        build_model(m, store, "2026-10-28")
    c1 = [r for r in store.get("dim_customer") if r["customer_id"] == "C1"]
    assert len(c1) == 2
    old, new = sorted(c1, key=lambda r: r["surrogate_key"])
    assert old["city"] == "Springfield" and old["is_current"] is False
    assert old["valid_to"] == "2026-10-28"
    assert new["city"] == "Harborview" and new["is_current"] is True
    assert new["valid_to"] == "9999-12-31"
    # Unchanged customer gets no second version.
    assert len([r for r in store.get("dim_customer") if r["customer_id"] == "C2"]) == 1


def test_scd2_unchanged_rerun_is_noop():
    store = _built_store()
    before = store.get("dim_customer")
    for m in plan(default_models(), external=SOURCES):
        build_model(m, store, "2026-10-28")
    assert store.get("dim_customer") == before


def test_fact_measures_and_surrogate_lookup():
    store = _built_store()
    rows = {r["order_item_id"]: r for r in store.get("fact_order_items")}
    assert rows["OI1"]["line_total"] == 35.0  # 2*20 - 5
    assert rows["OI2"]["line_total"] == 45.0
    assert rows["OI1"]["customer_id_sk"] == 1
    assert rows["OI1"]["product_id_sk"] == 1


def test_fact_merge_is_idempotent():
    store = _built_store()
    for m in plan(default_models(), external=SOURCES):
        build_model(m, store, "2026-10-20")
    assert len(store.get("fact_order_items")) == 2
    assert len(store.get("fact_orders")) == 2


def test_merge_rows_replaces_and_appends():
    merged = merge_rows([{"id": 1, "v": "a"}], [{"id": 1, "v": "b"}, {"id": 2, "v": "c"}], "id")
    assert merged == [{"id": 1, "v": "b"}, {"id": 2, "v": "c"}]


def test_fact_missing_dimension_reference_fails():
    store = Store()
    store.put("order_items", [{"order_item_id": "X", "customer_id": "NOPE", "product_id": "P1",
                               "quantity": 1, "unit_price": 10.0, "discount": 0.0}])
    store.put("dim_customer", [])
    store.put("dim_product", [])
    # Build staging first via catalog-like minimal fact model.
    fact = Model("fact_order_items", ModelKind.FACT, ("order_items",),
                 dimension_lookups={"customer_id": "dim_customer"},
                 grain_key="order_item_id")
    # Use raw source table as dependency: rename not needed for this check.
    store.put("order_items", store.get("order_items"))
    with pytest.raises(ValueError, match="no current"):
        build_model(fact, store)
