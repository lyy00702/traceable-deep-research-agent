"""Reusable programmatic runner for the interview lab."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from gpt_researcher import GPTResearcher

from .evaluation import summarize_runs
from .source_quality import score_source
from .trace import TraceRecorder


def _safe_filename(value: str, max_length: int = 60) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in "-_ " else "_"
        for char in value.strip()
    )
    cleaned = "_".join(cleaned.split())
    return (cleaned or "research")[:max_length]


async def run_research_task(
    query: str,
    *,
    output_dir: str = "./lab_outputs",
    report_type: str = "research_report",
    write_report: bool = True,
    max_subtopics: int = 3,
) -> dict[str, Any]:
    """Run one research task and persist report, sources, and trace data."""
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    trace = TraceRecorder(query=query, report_type=report_type)
    researcher = None
    result: dict[str, Any] = {
        "query": query,
        "report_type": report_type,
        "run_id": trace.run_id,
        "success": False,
    }

    try:
        researcher = GPTResearcher(
            query=query,
            report_type=report_type,
            verbose=False,
            max_subtopics=max_subtopics,
        )

        with trace.stage("research"):
            context = await researcher.conduct_research()

        source_quality = [
            score_source(
                source.get("url") or source.get("source") or "",
                title=source.get("title") or source.get("name") or "",
                content=source.get("raw_content") or source.get("content") or "",
                published_at=source.get("published_at"),
            )
            for source in researcher.research_sources
            if isinstance(source, dict)
        ]

        report = None
        if write_report:
            with trace.stage("report_generation"):
                report = await researcher.write_report()

        result.update(
            {
                "success": bool(context),
                "context_chars": len(str(context or "")),
                "source_count": len(researcher.research_sources),
                "cost": researcher.get_costs(),
                "sources": researcher.research_sources,
                "source_quality": source_quality,
                "report": report,
            }
        )
        if researcher is not None:
            result["agent_trace"] = researcher.trace.summary()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        trace.event(
            "run_failed",
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        result["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)

    artifact_dir = output_path / f"{_safe_filename(query)}-{trace.run_id}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if result.get("report"):
        (artifact_dir / "report.md").write_text(
            result["report"],
            encoding="utf-8",
        )

    (artifact_dir / "sources.json").write_text(
        json.dumps(result.get("sources", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_dir / "source_quality.json").write_text(
        json.dumps(result.get("source_quality", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_dir / "result.json").write_text(
        json.dumps(
            {key: value for key, value in result.items() if key != "report"},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    trace.event("run_completed", success=result["success"])
    result["trace"] = trace.summary()
    result["artifact_dir"] = str(artifact_dir)
    return result


async def run_evaluation_suite(
    tasks: list[dict[str, Any]],
    *,
    output_dir: str = "./lab_outputs/evaluations",
    write_report: bool = False,
) -> dict[str, Any]:
    """Run a fixed task set and aggregate reproducible metrics."""
    runs = []
    for task in tasks:
        run = await run_research_task(
            task["query"],
            output_dir=output_dir,
            report_type=task.get("report_type", "research_report"),
            write_report=write_report,
            max_subtopics=task.get("max_subtopics", 1),
        )
        runs.append(run)

    return {
        "summary": summarize_runs(runs),
        "runs": runs,
    }
