"""In-memory table store: the warehouse the engine builds into.

Rows are plain ``dict`` records so the core stays dependency-free and
trivially serialisable. A production port would swap this for a real
warehouse behind the same ``Store`` interface; the DAG, builders and
tests never touch anything else.
"""

from __future__ import annotations

import copy
from typing import Iterable


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict]] = {}

    def put(self, name: str, rows: Iterable[dict]) -> None:
        self._tables[name] = [copy.deepcopy(r) for r in rows]

    def get(self, name: str) -> list[dict]:
        if name not in self._tables:
            raise KeyError(f"table not built yet: {name!r}")
        return [copy.deepcopy(r) for r in self._tables[name]]

    def has(self, name: str) -> bool:
        return name in self._tables

    def tables(self) -> list[str]:
        return sorted(self._tables)

    def row_counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in sorted(self._tables.items())}
