"""Run manifests and run history.

Every build run records what was built, how many rows each model
produced, and the data-test outcome, so a run is auditable after the
fact and a bad run can be compared with the previous good one.
Manifests are plain JSON and append to a JSONL history file.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunRecord:
    run_id: str
    started_at: str
    models_built: list[str]
    row_counts: dict[str, int]
    tests_passed: int
    tests_failed: int
    status: str = "success"

    def to_dict(self) -> dict:
        return asdict(self)


class ManifestStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.history: list[RunRecord] = []
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.history.append(RunRecord(**json.loads(line)))

    @staticmethod
    def new_record(models_built: list[str], row_counts: dict[str, int],
                   tests_passed: int, tests_failed: int) -> RunRecord:
        return RunRecord(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
            models_built=models_built,
            row_counts=row_counts,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            status="success" if tests_failed == 0 else "tests_failed",
        )

    def append(self, record: RunRecord) -> None:
        self.history.append(record)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                fh.write(json.dumps(record.to_dict()) + "\n")

    def latest(self) -> RunRecord | None:
        return self.history[-1] if self.history else None
