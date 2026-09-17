"""Unit tests for interview-lab utilities."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gpt_researcher.lab.evaluation import percentile, summarize_runs
from gpt_researcher.lab.source_quality import score_source
from gpt_researcher.lab.trace import TraceRecorder
from gpt_researcher.lab.url_utils import dedupe_urls, normalize_url


class UrlUtilsTest(unittest.TestCase):
    def test_normalize_removes_tracking_and_fragment(self):
        url = "HTTPS://Example.COM:443/report/?utm_source=x&b=2&a=1#section"
        self.assertEqual(normalize_url(url), "https://example.com/report?a=1&b=2")

    def test_dedupe_preserves_first_seen_order(self):
        urls = [
            "https://example.com/a?utm_source=x",
            "https://example.com/a",
            "https://example.com/b",
        ]
        self.assertEqual(
            dedupe_urls(urls),
            ["https://example.com/a", "https://example.com/b"],
        )


class SourceQualityTest(unittest.TestCase):
    def test_authoritative_source_scores_higher(self):
        authoritative = score_source(
            "https://www.gov.cn/example",
            title="人工智能政策意见",
            content="内容" * 1200,
        )
        commercial = score_source(
            "https://example.com/blog",
            title="短文",
            content="内容" * 20,
        )
        self.assertGreater(authoritative["score"], commercial["score"])


class EvaluationTest(unittest.TestCase):
    def test_percentile_and_summary(self):
        self.assertEqual(percentile([100, 200, 300], 0.5), 200)
        summary = summarize_runs(
            [
                {"success": True, "duration_ms": 100, "source_count": 4},
                {"success": False, "duration_ms": 300, "source_count": 8},
            ]
        )
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["average_source_count"], 6)


class TraceTest(unittest.TestCase):
    def test_stage_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = TraceRecorder(
                run_id="unit-test",
                query="test",
                trace_dir=directory,
                enabled=True,
            )
            with trace.stage("search"):
                pass

            path = Path(directory) / "unit-test.jsonl"
            content = path.read_text(encoding="utf-8")
            self.assertIn("search_started", content)
            self.assertIn("search_completed", content)


if __name__ == "__main__":
    unittest.main()
