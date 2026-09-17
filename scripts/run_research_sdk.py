"""Run one GPT Researcher task from the command line."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from gpt_researcher.lab.runner import run_research_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GPT Researcher with trace output")
    parser.add_argument("query", help="Research question")
    parser.add_argument("--output-dir", default="./lab_outputs")
    parser.add_argument("--report-type", default="research_report")
    parser.add_argument("--max-subtopics", type=int, default=3)
    parser.add_argument(
        "--research-only",
        action="store_true",
        help="Collect sources without generating the final report",
    )
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    result = await run_research_task(
        args.query,
        output_dir=args.output_dir,
        report_type=args.report_type,
        write_report=not args.research_only,
        max_subtopics=args.max_subtopics,
    )
    print(
        json.dumps(
            {
                "success": result.get("success"),
                "sources": result.get("source_count"),
                "context_chars": result.get("context_chars"),
                "cost": result.get("cost"),
                "artifact_dir": result.get("artifact_dir"),
                "trace": result.get("trace"),
                "error": result.get("error"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
