# data-warehouse-marts-platform

Governed dimensional-modeling / marts platform, dbt-style but
dependency-free: declarative model definitions (sources → staging →
SCD Type 2 dimensions → fact tables), a DAG build engine with
topological ordering and incremental (merge) builds, declarative data
tests, model + column lineage, run manifests + run history, and a
read/query API over built marts. All data is synthetic and generic
(e-commerce-flavored orders/customers/products); all code is original.

## The enterprise problem

Analysts trust a mart only if three questions have auditable answers:
what was built, in what order, and did it pass its tests? In many
warehouses those answers live in tribal knowledge: a hand-maintained
runbook, a test suite bolted on after the fact, and lineage reconstructed
from SQL archaeology. This platform makes each one a first-class,
declarative artefact: models declare dependencies, tests declare
expectations, lineage is derived from those declarations, and every run
writes a manifest. A broken reference or a stale mart fails loudly
instead of shipping a plausible-looking wrong number.

## Architecture overview

```
sources (raw tables)
   │  rename / project only
   ▼
staging models ──────────────┐
   │  SCD Type 2 (tracked attrs)│  facts resolve current surrogate keys
   ▼                            ▼
dimensions (dim_customer,     fact tables (fact_order_items, fact_orders)
dim_product) ─────────────────►  incremental merge on grain key
   │
   ├─ data tests (unique / not-null / relationships / accepted values / freshness)
   ├─ lineage (model graph + column trace to source)
   └─ run manifest (models, row counts, test outcome) → JSONL history
```

See `docs/architecture.md` for the full description and diagram.

Core package (`src/marts/`, pure standard library):

| Module | Responsibility |
| --- | --- |
| `models.py` | Declarative `Model` / `Column` / `TestDefinition` dataclasses |
| `dag.py` | Topological ordering (Kahn), cycle + unknown-dependency errors |
| `builders.py` | Staging projection, SCD2 open/close, fact build + merge |
| `tests_engine.py` | Five declarative test types, fail-closed on unknown types |
| `lineage.py` | Upstream/downstream, column trace, DOT export |
| `manifest.py` | Run records, JSONL history, success/tests_failed status |
| `query.py` | Filtered reads + group-by summaries over built marts |
| `catalog.py` | The sample e-commerce project (sources → facts) |
| `seed.py` | Synthetic seed data, incl. a v2 change set for SCD2 |
| `app.py` | Optional read-only FastAPI service (needs FastAPI) |

## How to run it

```bash
pip install -r requirements.txt   # pytest; fastapi/uvicorn only for the API
PYTHONPATH=src python3 demo.py
PYTHONPATH=src python3 -m pytest -q
```

Demo output: build 1 (seed → staging → dims → facts), build 2 with
tracked-attribute changes (one customer moves city, one product changes
price → each gains a closed old version and a new current version),
data tests, lineage traces, and a revenue-by-product summary.

Optional API (after installing FastAPI):

```bash
PYTHONPATH=src uvicorn marts.app:app --reload
curl localhost:8000/marts/fact_order_items
curl "localhost:8000/marts/fact_order_items/summary?group_by=product_id&sum_column=line_total"
```

## Key design decisions and trade-offs

- **Declarations over code for models.** A new mart is a `Model`
  declaration, not a new pipeline, so lineage and tests stay in sync
  with the build by construction. The cost is expressiveness: exotic
  transforms still need a new builder function, deliberately.
- **Staging does no business logic.** Renames/projection only, so a
  staging failure is always a mapping failure — easy to diagnose.
- **SCD2 with exactly one current row per business key.** Unchanged
  re-runs are no-ops, so full and incremental runs converge. History
  is preserved (closed rows keep `valid_from`/`valid_to`); deletes are
  not tombstoned in this version — a deliberate scope limit, see
  architecture doc.
- **Facts merge on grain key, never append blindly.** Re-running a
  fact build replaces rows with the same grain key, so reruns are
  idempotent. A fact row whose dimension lookup has no current row
  fails the build (fail closed) rather than joining to NULL.
- **Tests fail closed.** An unknown test type, an empty model for a
  freshness test, or a missing model records a failure, never a pass.
- **In-memory store.** The `Store` interface is the seam: swapping it
  for a real warehouse touches one module, not the DAG, builders, or
  tests. The trade-off is scale — this build is for correctness and
  demonstration, not production volume.
- **Deterministic builds.** Surrogate keys are assigned in
  business-key order and DAG ties break alphabetically, so two runs
  over the same input produce the same output.

## What it demonstrates

Dimensional modeling (star schema, SCD Type 2, grain discipline),
incremental/merge builds, declarative data quality, lineage as a
derived artefact (not documentation), run observability via manifests,
and the fail-closed instincts — unknown dependencies, cycles, broken
references, and unknown tests all error instead of silently passing.
