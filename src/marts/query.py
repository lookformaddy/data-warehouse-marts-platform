"""Read/query API over built marts.

Deliberately small: equality filters, a row limit, and a group-by
summary (count + sum of a numeric column). This is the contract the
optional FastAPI service exposes, so service tests and core tests
exercise the same behaviour.
"""

from __future__ import annotations

from .store import Store


def query_mart(store: Store, table: str, filters: dict | None = None,
               limit: int = 100) -> list[dict]:
    rows = store.get(table)
    for col, value in (filters or {}).items():
        rows = [r for r in rows if str(r.get(col)) == str(value)]
    return rows[:limit]


def summarize_mart(store: Store, table: str, group_by: str,
                   sum_column: str) -> list[dict]:
    totals: dict[str, dict] = {}
    for row in store.get(table):
        key = str(row.get(group_by))
        bucket = totals.setdefault(key, {"count": 0, "total": 0.0})
        bucket["count"] += 1
        bucket["total"] = round(bucket["total"] + float(row.get(sum_column, 0) or 0), 2)
    return [{group_by: k, "count": v["count"], f"total_{sum_column}": v["total"]}
            for k, v in sorted(totals.items())]
