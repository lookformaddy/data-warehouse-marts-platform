"""Optional FastAPI service over a built store.

Run ``python demo.py`` first (or build via the engine) and then start
with ``uvicorn marts.app:app``. This module requires FastAPI; the core
engine and its tests do not. The service is deliberately read-only:
marts are built by the engine, never mutated through the API.
"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from marts.catalog import SOURCES, default_models, default_tests  # noqa: E402
from marts.dag import plan  # noqa: E402
from marts.builders import build_model  # noqa: E402
from marts.query import query_mart, summarize_mart  # noqa: E402
from marts.seed import seed_v1  # noqa: E402
from marts.store import Store  # noqa: E402

store = Store()
seed_v1(store)
for _model in plan(default_models(), external=SOURCES):
    build_model(_model, store)

app = FastAPI(title="Warehouse Marts Platform")


@app.get("/marts/{table}")
def read_mart(table: str, limit: int = 100):
    try:
        return {"table": table, "rows": query_mart(store, table, limit=limit)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown mart: {table}")


@app.get("/marts/{table}/summary")
def mart_summary(table: str, group_by: str, sum_column: str):
    try:
        return {"table": table, "summary": summarize_mart(store, table, group_by, sum_column)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown mart: {table}")


@app.get("/health")
def health():
    return {"status": "ok", "tables": store.tables()}
