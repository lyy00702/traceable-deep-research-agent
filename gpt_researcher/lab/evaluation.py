"""Aggregate metrics for repeatable Agent evaluations."""

from __future__ import annotations

from statistics import median
from typing import Iterable


def percentile(values: Iterable[float], ratio: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * max(0.0, min(1.0, ratio))
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_runs(runs: list[dict]) -> dict:
    if not runs:
        return {
            "task_count": 0,
            "success_rate": 0.0,
            "p50_duration_ms": None,
            "p95_duration_ms": None,
        }

    successes = [bool(run.get("success")) for run in runs]
    durations = [
        float(run["duration_ms"])
        for run in runs
        if run.get("duration_ms") is not None
    ]
    source_counts = [
        int(run.get("source_count", 0))
        for run in runs
        if run.get("source_count") is not None
    ]

    return {
        "task_count": len(runs),
        "success_count": sum(successes),
        "success_rate": round(sum(successes) / len(successes), 4),
        "p50_duration_ms": percentile(durations, 0.5),
        "p95_duration_ms": percentile(durations, 0.95),
        "median_source_count": median(source_counts) if source_counts else None,
        "average_source_count": (
            round(sum(source_counts) / len(source_counts), 2)
            if source_counts
            else None
        ),
    }
