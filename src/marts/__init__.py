"""Governed dimensional-modeling / marts platform (dbt-style, dependency-free).

Public surface: model definitions, DAG planner, builders, data tests,
lineage, run manifests and a read/query API over built marts.
Core logic is pure standard library; the optional FastAPI service in
``marts.app`` is the only part that needs third-party packages.
"""

from .models import Column, Model, ModelKind, Source, TestDefinition
from .store import Store
from .dag import CycleError, plan
from .builders import build_model, merge_rows
from .tests_engine import TestResult, run_tests
from .lineage import LineageGraph, build_lineage
from .manifest import ManifestStore, RunRecord
from .query import query_mart, summarize_mart

__all__ = [
    "Column", "Model", "ModelKind", "Source", "TestDefinition",
    "Store", "CycleError", "plan", "build_model", "merge_rows",
    "TestResult", "run_tests", "LineageGraph", "build_lineage",
    "ManifestStore", "RunRecord", "query_mart", "summarize_mart",
]
