"""Declarative data tests (dbt-test style, dependency-free).

Each test returns a TestResult with ``passed`` and the offending rows
(or a count) so failures are diagnosable, not just red. Unknown test
types fail closed: a test that cannot be interpreted must not silently
pass. Freshness takes an explicit reference time so test outcomes are
deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import TestDefinition
from .store import Store


@dataclass
class TestResult:
    name: str
    model: str
    test_type: str
    passed: bool
    detail: str = ""
    failing_rows: tuple[dict, ...] = ()


def _unique(store: Store, t: TestDefinition) -> TestResult:
    rows = store.get(t.model)
    seen, dupes = set(), []
    for r in rows:
        v = r.get(t.column)
        if v in seen:
            dupes.append(r)
        seen.add(v)
    return TestResult(t.name, t.model, t.test_type, not dupes,
                      f"{len(dupes)} duplicate value(s) in {t.column}" if dupes else "all unique",
                      tuple(dupes[:5]))


def _not_null(store: Store, t: TestDefinition) -> TestResult:
    rows = store.get(t.model)
    bad = [r for r in rows if r.get(t.column) is None]
    return TestResult(t.name, t.model, t.test_type, not bad,
                      f"{len(bad)} null value(s) in {t.column}" if bad else "no nulls",
                      tuple(bad[:5]))


def _relationships(store: Store, t: TestDefinition) -> TestResult:
    allowed = {str(r.get(t.reference_column)) for r in store.get(t.reference_model)}
    bad = [r for r in store.get(t.model) if str(r.get(t.column)) not in allowed]
    return TestResult(t.name, t.model, t.test_type, not bad,
                      f"{len(bad)} row(s) with no match in {t.reference_model}.{t.reference_column}" if bad else "all references resolve",
                      tuple(bad[:5]))


def _accepted_values(store: Store, t: TestDefinition) -> TestResult:
    allowed = set(t.accepted_values)
    bad = [r for r in store.get(t.model) if str(r.get(t.column)) not in allowed]
    return TestResult(t.name, t.model, t.test_type, not bad,
                      f"{len(bad)} row(s) outside accepted values" if bad else "all values accepted",
                      tuple(bad[:5]))


def _freshness(store: Store, t: TestDefinition) -> TestResult:
    rows = store.get(t.model)
    if not rows:
        return TestResult(t.name, t.model, t.test_type, False, "model is empty")
    if not t.reference_time:
        return TestResult(t.name, t.model, t.test_type, False, "freshness needs reference_time")
    ref = datetime.fromisoformat(t.reference_time)
    stamps = [datetime.fromisoformat(str(r[t.column])) for r in rows if r.get(t.column)]
    if not stamps:
        return TestResult(t.name, t.model, t.test_type, False, "no timestamps found")
    age_days = (ref - max(stamps)).days
    ok = age_days <= t.max_age_days
    return TestResult(t.name, t.model, t.test_type, ok,
                      f"newest row is {age_days} day(s) old (limit {t.max_age_days})")


_HANDLERS = {
    "unique": _unique,
    "not_null": _not_null,
    "relationships": _relationships,
    "accepted_values": _accepted_values,
    "freshness": _freshness,
}


def run_tests(store: Store, tests: list[TestDefinition]) -> list[TestResult]:
    results = []
    for t in tests:
        handler = _HANDLERS.get(t.test_type)
        if handler is None:
            results.append(TestResult(t.name, t.model, t.test_type, False,
                                      f"unknown test type {t.test_type!r} (fail closed)"))
            continue
        try:
            results.append(handler(store, t))
        except KeyError as exc:
            results.append(TestResult(t.name, t.model, t.test_type, False,
                                      f"model not built: {exc}"))
    return results
