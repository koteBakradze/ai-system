import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.research.context_builder import (
    build_context_pack,
    extract_sources_from_report,
    save_context_pack,
    slugify_title,
)


FAKE_REPORT = """# Fresh Research Report: best local LLM coding workflow 2026

- Generated: 2026-05-12T10:52:27+00:00
- Provider: `mock-offline`
- Sources found: 2
- Max results: 8

## Safety Notes

- Search results are source leads, not verified truth.

## Research Questions

- best local LLM coding workflow 2026

## Summary

Collected 2 sources for `best local LLM coding workflow 2026` from mock-offline.

## Source Candidates

### 1. Ollama Coding Workflow Guide

- URL: https://example.com/ollama-workflow
- Search query: local LLM coding workflow
- Provider: `mock-offline`

Ollama can run local coding models and keep review loops on a developer machine.

### 2. Continue Local Models

- URL: https://example.com/continue-local
- Search query: local LLM coding workflow
- Provider: `mock-offline`

Continue can connect editors to local models for coding assistance.

## Raw Research Notes

- Ollama Coding Workflow Guide
  URL: https://example.com/ollama-workflow
  Snippet: Ollama can run local coding models.

## Final Conclusions

No final conclusions are asserted by the gateway.
"""


class ResearchContextBuilderTests(unittest.TestCase):
    def test_context_file_is_created_and_preserves_source_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "workspace" / "research" / "fake-report.md"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(FAKE_REPORT, encoding="utf-8")

            pack = build_context_pack(report_path)
            output_path = save_context_pack(pack, root / "memory" / "context" / "research")
            content = output_path.read_text(encoding="utf-8")

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.name, "best-local-llm-coding-workflow-2026.md")
            self.assertIn("# Research Context: best local LLM coding workflow 2026", content)
            self.assertIn("Ollama Coding Workflow Guide — https://example.com/ollama-workflow", content)
            self.assertIn("Continue Local Models — https://example.com/continue-local", content)
            self.assertIn("- Provider name: `mock-offline`", content)
            self.assertIn("- Source count: 2", content)

    def test_extract_sources_from_report_reads_titles_urls_snippets_and_provider(self):
        sources = extract_sources_from_report(FAKE_REPORT)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].title, "Ollama Coding Workflow Guide")
        self.assertEqual(sources[0].url, "https://example.com/ollama-workflow")
        self.assertEqual(sources[0].provider, "mock-offline")
        self.assertIn("local coding models", sources[0].snippet)

    def test_empty_or_weak_reports_are_handled_safely(self):
        weak_report = """# Fresh Research Report: rare topic

- Provider: `mock-offline`
- Sources found: 0

## Summary

No source candidates were collected for `rare topic`.

## Source Candidates

No source candidates collected.
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "rare.md"
            report_path.write_text(weak_report, encoding="utf-8")
            pack = build_context_pack(report_path)
            output_path = save_context_pack(pack, Path(temp_dir) / "context")
            content = output_path.read_text(encoding="utf-8")

            self.assertEqual(pack.source_count, 0)
            self.assertIn("No source links available in the report.", content)
            self.assertIn("Suggested: Re-run research", content)

    def test_slug_filename_is_safe(self):
        self.assertEqual(
            slugify_title("20260512-105227-Best Local LLM Coding Workflow 2026!?"),
            "best-local-llm-coding-workflow-2026",
        )

    def test_no_internet_or_paid_api_key_is_required(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(os.environ, {}, clear=True):
            report_path = Path(temp_dir) / "fake.md"
            report_path.write_text(FAKE_REPORT, encoding="utf-8")

            pack = build_context_pack(report_path)
            output_path = save_context_pack(pack, Path(temp_dir) / "context")

            self.assertTrue(output_path.exists())
            self.assertEqual(pack.provider_name, "mock-offline")


if __name__ == "__main__":
    unittest.main()
