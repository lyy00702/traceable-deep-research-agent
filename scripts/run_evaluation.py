"""Run a deterministic JSON task suite and write aggregate metrics."""

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

from gpt_researcher.lab.runner import run_evaluation_suite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GPT Researcher evaluation suite")
    parser.add_argument("--tasks", default="./lab_tasks.json")
    parser.add_argument("--output-dir", default="./lab_outputs/evaluations")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--with-reports", action="store_true")
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    if args.limit > 0:
        tasks = tasks[: args.limit]

    result = await run_evaluation_suite(
        tasks,
        output_dir=args.output_dir,
        write_report=args.with_reports,
    )
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / "summary.json"
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"summary_path={summary_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
