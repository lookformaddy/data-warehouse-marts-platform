"""Declarative model definitions.

A model is data, not code: sources, staging models, SCD Type 2
dimensions and fact tables are all described with the same dataclasses,
so a new mart is a declaration, not a new pipeline. Builders in
``builders.py`` interpret these definitions; nothing here executes SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ModelKind(str, Enum):
    SOURCE = "source"
    STAGING = "staging"
    DIMENSION = "dimension"
    FACT = "fact"


@dataclass(frozen=True)
class Column:
    """One output column and where it comes from.

    ``source_columns`` is the column-level lineage: for a renamed column
    it holds the single upstream column; for a derived measure it holds
    every input column the derivation reads.
    """

    name: str
    source_columns: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class Source:
    name: str
    columns: tuple[str, ...] = ()


@dataclass
class Model:
    name: str
    kind: ModelKind
    depends_on: tuple[str, ...] = ()
    columns: tuple[Column, ...] = ()
    # Staging: {source_column: target_column} renames applied to the
    # single upstream table; empty means "pass through unchanged".
    renames: dict[str, str] = field(default_factory=dict)
    # Dimension: natural/business key column in the staging input.
    business_key: str = ""
    # Dimension: attributes whose change opens a new SCD2 version.
    tracked_attributes: tuple[str, ...] = ()
    # Fact: {input_column: dimension_model} lookups that resolve a
    # business key to a surrogate key at build time.
    dimension_lookups: dict[str, str] = field(default_factory=dict)
    # Fact: the column that uniquely identifies a fact row, used by the
    # incremental merge (re-running a build replaces, never duplicates).
    grain_key: str = ""
    # Fact: derived measures, {output: (input_columns, function-name)}.
    # Supported functions are implemented in builders.MEASURES.
    measures: dict[str, tuple[tuple[str, ...], str]] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class TestDefinition:
    """One declarative data test.

    Types: ``unique``, ``not_null``, ``relationships`` (every value in
    ``column`` exists in ``reference_model.reference_column``),
    ``accepted_values``, ``freshness`` (newest ``column`` timestamp no
    older than ``max_age_days`` before ``reference_time``).
    """

    name: str
    model: str
    test_type: str
    column: str = ""
    reference_model: str = ""
    reference_column: str = ""
    accepted_values: tuple[str, ...] = ()
    max_age_days: int = 30
    # ISO timestamp used as "now" for freshness; tests pass an explicit
    # value so results are deterministic and time-independent.
    reference_time: str = ""
