"""DAG planner: topological ordering with cycle detection.

Models declare ``depends_on``; the planner returns a build order in
which every dependency precedes its dependents. Unknown dependencies
are a definition error, and a cycle raises ``CycleError`` naming the
models involved instead of hanging or silently building out of order.
"""

from __future__ import annotations

from .models import Model


class CycleError(ValueError):
    """Raised when the dependency graph contains a cycle."""


def plan(models: list[Model], external: tuple[str, ...] = ()) -> list[Model]:
    """Order ``models``; ``external`` names raw source tables that are
    allowed as dependencies without being models themselves."""
    by_name = {m.name: m for m in models}
    external_set = set(external)
    for m in models:
        for dep in m.depends_on:
            if dep not in by_name and dep not in external_set:
                raise ValueError(f"model {m.name!r} depends on unknown model {dep!r}")
    # Kahn's algorithm, deterministic: ties broken alphabetically.
    # External dependencies contribute no indegree (they already exist).
    indegree = {m.name: 0 for m in models}
    dependents: dict[str, list[str]] = {m.name: [] for m in models}
    for m in models:
        for dep in m.depends_on:
            if dep in by_name:
                indegree[m.name] += 1
                dependents[dep].append(m.name)
    ready = sorted(n for n, d in indegree.items() if d == 0)
    order: list[str] = []
    while ready:
        name = ready.pop(0)
        order.append(name)
        for nxt in sorted(dependents[name]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort()
    if len(order) != len(models):
        cyclic = sorted(n for n, d in indegree.items() if d > 0)
        raise CycleError(f"dependency cycle involving: {', '.join(cyclic)}")
    return [by_name[n] for n in order]
