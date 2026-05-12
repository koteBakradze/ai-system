import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.research.gateway import create_research_report
from core.research.models import SearchResult, is_valid_source_url
from core.research.providers import (
    DDGS_INSTALL_MESSAGE,
    DDGSSearchProvider,
    MockSearchProvider,
    resolve_search_provider,
)
from core.research.writer import render_research_report, save_research_report


class FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def text(self, query, max_results=8):
        return [
            {
                "title": "Real Result",
                "href": "https://example.com/real-result",
                "body": f"Snippet for {query}",
            }
        ][:max_results]


class EmptyDDGS(FakeDDGS):
    def text(self, query, max_results=8):
        return []


class FailingDDGS(FakeDDGS):
    def text(self, query, max_results=8):
        raise OSError("network unavailable")


class FreshResearchGatewayTests(unittest.TestCase):
    def test_gateway_returns_structured_results(self):
        provider = MockSearchProvider(
            [
                SearchResult(
                    title="Local LLM Workflow Guide",
                    url="https://example.com/local-llm-workflow",
                    snippet="A guide to local coding models and review loops.",
                    provider="fixture",
                    query="fixture",
                    rank=1,
                )
            ]
        )

        report = create_research_report(
            "local LLM coding workflow",
            provider=provider,
            provider_name="mock",
            max_results=3,
        )

        self.assertEqual(report.query.topic, "local LLM coding workflow")
        self.assertEqual(report.provider_name, "mock-offline")
        self.assertEqual(report.source_count, 1)
        self.assertIn("Collected 1 source", report.summary)

    def test_markdown_report_is_created_and_preserves_source_metadata(self):
        provider = MockSearchProvider(
            [
                SearchResult(
                    title="OpenRouter Limits",
                    url="https://example.com/openrouter-limits",
                    snippet="Free model limits and best practices.",
                    provider="fixture",
                    query="fixture",
                    rank=1,
                )
            ]
        )
        report = create_research_report(
            "OpenRouter free model limits",
            provider=provider,
            provider_name="mock",
            max_results=3,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_research_report(report, output_dir=Path(temp_dir))
            content = path.read_text(encoding="utf-8")

            self.assertIn("# Fresh Research Report: OpenRouter free model limits", content)
            self.assertIn("https://example.com/openrouter-limits", content)
            self.assertIn("OpenRouter Limits", content)
            self.assertIn("Free model limits and best practices.", content)
            self.assertIn("- Provider: `mock-offline`", content)
            self.assertIn("## Sources", content)
            self.assertIn("1. [OpenRouter Limits](https://example.com/openrouter-limits)", content)

    def test_empty_results_are_handled_safely(self):
        report = create_research_report(
            "rare topic with no results",
            provider=MockSearchProvider(),
            provider_name="mock",
            max_results=3,
        )

        self.assertEqual(report.source_count, 0)
        self.assertIn("No source candidates", report.summary)
        self.assertTrue(report.limitations)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_research_report(report, output_dir=Path(temp_dir))
            content = path.read_text(encoding="utf-8")

            self.assertIn("No source candidates collected.", content)
            self.assertIn("No raw source metadata is available.", content)

    def test_provider_selection_chooses_mock_when_requested(self):
        provider = resolve_search_provider("mock")

        self.assertIsInstance(provider, MockSearchProvider)
        self.assertEqual(provider.name, "mock-offline")

    def test_provider_selection_chooses_ddgs_when_requested(self):
        with patch(
            "core.research.providers.importlib.import_module",
            return_value=SimpleNamespace(DDGS=FakeDDGS),
        ):
            provider = resolve_search_provider("ddgs")

        self.assertIsInstance(provider, DDGSSearchProvider)
        self.assertEqual(provider.name, "ddgs")

    def test_ddgs_missing_dependency_gives_clear_error(self):
        with patch(
            "core.research.providers.importlib.import_module",
            side_effect=ImportError("missing ddgs"),
        ):
            with self.assertRaisesRegex(RuntimeError, "pip install ddgs"):
                resolve_search_provider("ddgs")

        self.assertEqual(
            DDGS_INSTALL_MESSAGE,
            "Real web search requires ddgs. Install with: pip install ddgs",
        )

    def test_real_mode_does_not_silently_fall_back_to_mock(self):
        report = create_research_report(
            "real search topic",
            provider=DDGSSearchProvider(ddgs_factory=FailingDDGS),
            provider_name="ddgs",
            max_results=3,
        )

        self.assertEqual(report.provider_name, "ddgs")
        self.assertEqual(report.source_count, 0)
        self.assertNotEqual(report.provider_name, "mock-offline")
        self.assertTrue(any("ddgs search failed safely" in item for item in report.limitations))

    def test_ddgs_provider_returns_structured_valid_results(self):
        provider = DDGSSearchProvider(ddgs_factory=FakeDDGS)

        results = provider.search("local LLM workflow", max_results=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Real Result")
        self.assertEqual(results[0].url, "https://example.com/real-result")
        self.assertEqual(results[0].provider, "ddgs")
        self.assertEqual(results[0].query, "local LLM workflow")

    def test_invalid_urls_are_rejected(self):
        provider = MockSearchProvider(
            [
                SearchResult(
                    title="Invalid URL",
                    url="ftp://example.com/file",
                    snippet="Should not be accepted.",
                    provider="fixture",
                    query="fixture",
                    rank=1,
                )
            ]
        )

        report = create_research_report(
            "invalid source topic",
            provider=provider,
            provider_name="mock",
            max_results=3,
        )

        self.assertEqual(report.source_count, 0)
        self.assertTrue(any("Skipped invalid search result" in item for item in report.limitations))

    def test_search_ad_redirect_urls_are_rejected(self):
        self.assertFalse(
            is_valid_source_url("https://www.bing.com/aclick?ld=tracking-token")
        )
        self.assertFalse(is_valid_source_url("https://googleadservices.com/pagead/aclk"))
        self.assertFalse(is_valid_source_url("https://duckduckgo.com/y.js?ad_domain=example.com"))
        self.assertTrue(is_valid_source_url("https://example.com/source-page"))

    def test_empty_real_results_do_not_create_fake_sources(self):
        report = create_research_report(
            "empty real topic",
            provider=DDGSSearchProvider(ddgs_factory=EmptyDDGS),
            provider_name="ddgs",
            max_results=3,
        )
        content = render_research_report(report)

        self.assertEqual(report.provider_name, "ddgs")
        self.assertEqual(report.source_count, 0)
        self.assertIn("No sources collected.", content)
        self.assertIn("No source candidates collected.", content)
        self.assertNotIn("https://example.com", content)
        self.assertNotIn("No URL returned", content)


if __name__ == "__main__":
    unittest.main()
