"""Model and column lineage.

Model lineage follows ``depends_on`` edges. Column lineage follows the
``source_columns`` declared on each model's columns: for staging that
is the rename source, for a fact measure it is every input column the
measure reads. ``trace_column`` walks upstream until it reaches a
source table, so an analyst can answer "where did this column come
from?" without reading pipeline code.
"""

from __future__ import annotations

from .models import Model


class LineageGraph:
    def __init__(self, models: list[Model]) -> None:
        self._models = {m.name: m for m in models}

    def upstream(self, name: str) -> list[str]:
        """All ancestors of ``name`` in dependency order (nearest last)."""
        seen: list[str] = []
        stack = list(self._models[name].depends_on)
        while stack:
            node = stack.pop(0)
            if node in seen:
                continue
            seen.append(node)
            # Raw sources are not models: they terminate the walk.
            if node in self._models:
                stack.extend(self._models[node].depends_on)
        return seen

    def downstream(self, name: str) -> list[str]:
        """All models that transitively depend on ``name``."""
        return [m.name for m in self._models.values()
                if name in self.upstream(m.name)]

    def trace_column(self, model_name: str, column: str) -> list[tuple[str, str]]:
        """Walk a column upstream to its source columns.

        Returns ``(model, column)`` pairs from the requested model back
        to source tables. A column with no declared provenance stops at
        itself; unknown models/columns return just the starting pair.
        """
        path = [(model_name, column)]
        current_model, current_col = model_name, column
        while current_model in self._models:
            model = self._models[current_model]
            col_def = next((c for c in model.columns if c.name == current_col), None)
            if col_def is None or not col_def.source_columns:
                break
            # Follow the first source column; multi-input derivations
            # are recorded on the column itself (see column provenance).
            src_col = col_def.source_columns[0]
            if not model.depends_on:
                break
            current_model, current_col = model.depends_on[0], src_col
            path.append((current_model, current_col))
            if model.kind.value == "source":
                break
        return path

    def to_dot(self) -> str:
        lines = ["digraph lineage {"]
        for m in self._models.values():
            for dep in m.depends_on:
                lines.append(f'  "{dep}" -> "{m.name}";')
        lines.append("}")
        return "\n".join(lines)


def build_lineage(models: list[Model]) -> LineageGraph:
    return LineageGraph(models)
