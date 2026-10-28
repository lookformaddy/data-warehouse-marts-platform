import pytest

from marts.dag import CycleError, plan
from marts.models import Model, ModelKind


def _m(name, deps=()):
    return Model(name, ModelKind.STAGING, deps)


def test_ordering_respects_dependencies():
    models = [_m("fact", ("dim",)), _m("dim", ("stg",)), _m("stg", ("src",)), _m("src")]
    names = [m.name for m in plan(models)]
    assert names.index("src") < names.index("stg") < names.index("dim") < names.index("fact")


def test_cycle_detection_names_participants():
    models = [_m("a", ("b",)), _m("b", ("a",))]
    with pytest.raises(CycleError, match="a"):
        plan(models)


def test_self_cycle_and_unknown_dependency():
    with pytest.raises(CycleError):
        plan([_m("a", ("a",))])
    with pytest.raises(ValueError, match="unknown"):
        plan([_m("a", ("missing",))])


def test_empty_plan():
    assert plan([]) == []
