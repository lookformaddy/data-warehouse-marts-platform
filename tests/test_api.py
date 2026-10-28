"""FastAPI service tests; auto-skip on plain system python (no FastAPI)."""

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from marts.app import app  # noqa: E402

client = TestClient(app)


def test_health_lists_tables():
    r = client.get("/health")
    assert r.status_code == 200 and "fact_order_items" in r.json()["tables"]


def test_read_mart_and_404():
    r = client.get("/marts/fact_order_items")
    assert r.status_code == 200 and len(r.json()["rows"]) == 2
    assert client.get("/marts/nope").status_code == 404


def test_summary_endpoint():
    r = client.get("/marts/fact_order_items/summary",
                   params={"group_by": "product_id", "sum_column": "line_total"})
    assert r.status_code == 200
    assert r.json()["summary"][0]["total_line_total"] == 35.0
