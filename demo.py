"""End-to-end demo: seed -> staging -> SCD2 dims -> facts -> tests.

Run:  PYTHONPATH=src python3 demo.py
Second build applies the v2 changes, showing SCD2 history (closed +
new current rows) and idempotent fact merging (no duplicate lines).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from marts.builders import build_model
from marts.catalog import SOURCES, default_models, default_tests
from marts.dag import plan
from marts.lineage import build_lineage
from marts.manifest import ManifestStore
from marts.query import summarize_mart
from marts.seed import seed_v1, seed_v2_changes
from marts.store import Store
from marts.tests_engine import run_tests


def build_all(store: Store, effective_date: str) -> list[str]:
    built = []
    for model in plan(default_models(), external=SOURCES):
        build_model(model, store, effective_date)
        built.append(model.name)
    return built


def main() -> None:
    store = Store()
    seed_v1(store)
    built = build_all(store, "2026-10-20")
    print("Build 1 models:", ", ".join(built))
    print("Row counts:", store.row_counts())

    # Second load with tracked-attribute changes -> SCD2 versions.
    seed_v2_changes(store)
    build_all(store, "2026-10-28")
    print("Build 2 row counts:", store.row_counts())
    customers = store.get("dim_customer")
    print("dim_customer versions for C1:",
          [(r["city"], r["is_current"]) for r in customers if r["customer_id"] == "C1"])
    print("fact_order_items rows (idempotent merge):", len(store.get("fact_order_items")))

    results = run_tests(store, default_tests())
    passed = sum(r.passed for r in results)
    print(f"Data tests: {passed}/{len(results)} passed")
    for r in results:
        if not r.passed:
            print(f"  FAILED {r.name}: {r.detail}")

    lineage = build_lineage(default_models())
    print("fact_order_items upstream:", lineage.upstream("fact_order_items"))
    print("Column lineage fact_order_items.line_total:",
          lineage.trace_column("fact_order_items", "line_total"))
    print("Revenue by product:", summarize_mart(store, "fact_order_items", "product_id", "line_total"))

    manifest = ManifestStore.new_record(built, store.row_counts(), passed, len(results) - passed)
    print(f"Run manifest: status={manifest.status} tests={passed}/{len(results)}")


if __name__ == "__main__":
    main()
