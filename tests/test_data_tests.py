import pytest

from marts.models import TestDefinition
from marts.store import Store
from marts.tests_engine import run_tests


def _store_with(table, rows, ref=None):
    s = Store()
    s.put(table, rows)
    if ref:
        s.put(ref[0], ref[1])
    return s


def test_unique_pass_and_fail():
    s = _store_with("t", [{"id": 1}, {"id": 2}])
    assert run_tests(s, [TestDefinition("u", "t", "unique", "id")])[0].passed
    s = _store_with("t", [{"id": 1}, {"id": 1}])
    r = run_tests(s, [TestDefinition("u", "t", "unique", "id")])[0]
    assert not r.passed and len(r.failing_rows) == 1


def test_not_null_pass_and_fail():
    s = _store_with("t", [{"id": 1}])
    assert run_tests(s, [TestDefinition("n", "t", "not_null", "id")])[0].passed
    s = _store_with("t", [{"id": None}])
    assert not run_tests(s, [TestDefinition("n", "t", "not_null", "id")])[0].passed


def test_relationships_pass_and_fail():
    s = _store_with("fact", [{"cid": "C1"}], ("dim", [{"cid": "C1"}]))
    t = TestDefinition("r", "fact", "relationships", "cid", "dim", "cid")
    assert run_tests(s, [t])[0].passed
    s = _store_with("fact", [{"cid": "C9"}], ("dim", [{"cid": "C1"}]))
    assert not run_tests(s, [t])[0].passed


def test_accepted_values_pass_and_fail():
    s = _store_with("t", [{"status": "completed"}])
    t = TestDefinition("a", "t", "accepted_values", "status", accepted_values=("completed",))
    assert run_tests(s, [t])[0].passed
    s = _store_with("t", [{"status": "weird"}])
    assert not run_tests(s, [t])[0].passed


def test_freshness_pass_and_fail():
    t = TestDefinition("f", "t", "freshness", "ts", max_age_days=30,
                       reference_time="2026-10-28T00:00:00")
    s = _store_with("t", [{"ts": "2026-10-20"}])
    assert run_tests(s, [t])[0].passed
    s = _store_with("t", [{"ts": "2026-01-01"}])
    assert not run_tests(s, [t])[0].passed


def test_unknown_test_type_fails_closed():
    s = _store_with("t", [{"id": 1}])
    r = run_tests(s, [TestDefinition("x", "t", "mystery", "id")])[0]
    assert not r.passed
