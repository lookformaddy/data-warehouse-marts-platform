import json
import tempfile
from pathlib import Path

from marts.builders import build_model
from marts.catalog import SOURCES, default_models
from marts.dag import plan
from marts.lineage import build_lineage
from marts.manifest import ManifestStore
from marts.query import query_mart, summarize_mart
from marts.seed import seed_v1
from marts.store import Store


def _built():
    store = Store()
    seed_v1(store)
    for m in plan(default_models(), external=SOURCES):
        build_model(m, store, "2026-10-20")
    return store


def test_lineage_upstream_and_downstream():
    g = build_lineage(default_models())
    upstream = g.upstream("fact_order_items")
    # Staging input first, then dimension inputs, then their sources.
    assert upstream[0] == "stg_order_items"
    assert {"dim_customer", "dim_product", "order_items", "stg_customers"} <= set(upstream)
    assert "fact_order_items" in g.downstream("stg_order_items")
    assert g.upstream("stg_customers") == ["customers"]


def test_column_lineage_reaches_source():
    g = build_lineage(default_models())
    path = g.trace_column("fact_order_items", "line_total")
    assert path[0] == ("fact_order_items", "line_total")
    assert path[-1][0] == "order_items"


def test_lineage_dot_export():
    dot = build_lineage(default_models()).to_dot()
    assert '"stg_order_items" -> "fact_order_items"' in dot


def test_manifest_round_trip_and_status():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.jsonl"
        ms = ManifestStore(path)
        rec = ManifestStore.new_record(["fact_order_items"], {"fact_order_items": 2}, 8, 0)
        ms.append(rec)
        assert ms.latest().status == "success"
        assert ManifestStore(path).latest().run_id == rec.run_id
        bad = ManifestStore.new_record(["x"], {}, 0, 1)
        assert bad.status == "tests_failed"


def test_query_filters_and_summary():
    store = _built()
    rows = query_mart(store, "fact_order_items", {"product_id": "P1"})
    assert len(rows) == 1 and rows[0]["line_total"] == 35.0
    summary = summarize_mart(store, "fact_order_items", "product_id", "line_total")
    assert summary == [{"product_id": "P1", "count": 1, "total_line_total": 35.0},
                       {"product_id": "P2", "count": 1, "total_line_total": 45.0}]
