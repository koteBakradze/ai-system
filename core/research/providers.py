from __future__ import annotations

import importlib
from collections.abc import Iterable, Sequence
from typing import Protocol

from core.research.models import SearchResult, is_valid_source_url


DDGS_INSTALL_MESSAGE = "Real web search requires ddgs. Install with: pip install ddgs"


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, max_results: int = 8) -> Sequence[SearchResult]:
        """Return search-result metadata only; providers must not execute actions."""


class MockSearchProvider:
    name = "mock-offline"

    def __init__(self, results: Iterable[SearchResult] | None = None):
        self._results = tuple(results or ())

    def search(self, query: str, max_results: int = 8) -> Sequence[SearchResult]:
        return tuple(
            SearchResult(
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                provider=self.name,
                query=query,
                rank=index + 1,
                published_at=result.published_at,
            )
            for index, result in enumerate(self._results[:max_results])
        )


class DDGSSearchProvider:
    name = "ddgs"

    def __init__(self, ddgs_factory=None):
        if ddgs_factory is not None:
            self._ddgs_factory = ddgs_factory
            return

        try:
            ddgs_module = importlib.import_module("ddgs")
        except ImportError as exc:
            raise RuntimeError(DDGS_INSTALL_MESSAGE) from exc

        self._ddgs_factory = ddgs_module.DDGS

    def search(self, query: str, max_results: int = 8) -> Sequence[SearchResult]:
        try:
            with self._ddgs_factory() as ddgs:
                rows = ddgs.text(query, max_results=max_results)
        except Exception as exc:
            raise RuntimeError(f"ddgs search failed safely: {exc}") from exc

        results: list[SearchResult] = []
        for index, row in enumerate(rows or [], start=1):
            title = str(row.get("title") or "").strip()
            url = str(row.get("href") or row.get("url") or "").strip()
            snippet = str(row.get("body") or row.get("snippet") or "").strip()
            if not title or not is_valid_source_url(url):
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider=self.name,
                    query=query,
                    rank=index,
                )
            )
        return tuple(results)


def resolve_search_provider(provider_name: str = "auto") -> SearchProvider:
    requested = (provider_name or "auto").strip().lower()
    if requested in {"mock", "offline", "mock-offline"}:
        return MockSearchProvider()
    if requested in {"ddgs", "duckduckgo", "real"}:
        return DDGSSearchProvider()
    if requested == "auto":
        return MockSearchProvider()
    raise ValueError(f"Unknown research search provider: {provider_name}")
