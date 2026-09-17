"""Small JSONL trace recorder for long-running agent workflows."""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceRecorder:
    """Write structured stage-level events without adding an observability SDK."""

    def __init__(
        self,
        run_id: str | None = None,
        *,
        query: str | None = None,
        report_type: str | None = None,
        trace_dir: str | None = None,
        enabled: bool | None = None,
    ):
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        self.query = query
        self.report_type = report_type

        if enabled is None:
            enabled = os.getenv("AGENT_TRACE_ENABLED", "false").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        self.enabled = enabled
        self.trace_dir = Path(
            trace_dir or os.getenv("AGENT_TRACE_DIR", "./traces")
        ).expanduser()
        self.path = self.trace_dir / f"{self.run_id}.jsonl"
        self._events: list[dict[str, Any]] = []

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def event(self, stage: str, **fields: Any) -> dict[str, Any]:
        event = {
            "run_id": self.run_id,
            "query": self.query,
            "report_type": self.report_type,
            "stage": stage,
            "timestamp": self._timestamp(),
            **fields,
        }
        self._events.append(event)

        if self.enabled:
            self.trace_dir.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

        return event

    @contextmanager
    def stage(self, stage: str, **fields: Any):
        started = time.perf_counter()
        self.event(f"{stage}_started", **fields)
        try:
            yield
        except Exception as exc:
            self.event(
                f"{stage}_failed",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=f"{type(exc).__name__}: {exc}",
                **fields,
            )
            raise
        else:
            self.event(
                f"{stage}_completed",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                **fields,
            )

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def summary(self) -> dict[str, Any]:
        durations: dict[str, float] = {}
        for event in self._events:
            stage = event.get("stage", "")
            if stage.endswith("_completed") and "duration_ms" in event:
                durations[stage.removesuffix("_completed")] = float(
                    event["duration_ms"]
                )

        return {
            "run_id": self.run_id,
            "event_count": len(self._events),
            "stage_durations_ms": durations,
            "trace_path": str(self.path) if self.enabled else None,
        }
