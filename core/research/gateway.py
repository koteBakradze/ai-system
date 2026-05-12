from __future__ import annotations

from collections.abc import Sequence
from math import ceil

from core.research.models import ResearchQuery, ResearchReport, SearchResult
from core.research.providers import SearchProvider, resolve_search_provider


def create_research_report(
    topic: str,
    provider: SearchProvider | None = None,
    provider_name: str = "mock",
    max_results: int = 8,
) -> ResearchReport:
    research_query = ResearchQuery.from_topic(
        topic=topic,
        max_results=max_results,
        provider=provider_name,
    )
    search_provider = provider or resolve_search_provider(provider_name)

    results, provider_errors = _collect_results(search_provider, research_query)
    limitations = _build_limitations(search_provider.name, results, provider_errors)
    summary = _summarize_results(research_query, results)

    return ResearchReport(
        query=research_query,
        provider_name=search_provider.name,
        results=tuple(results),
        summary=summary,
        limitations=tuple(limitations),
    )


def _collect_results(
    provider: SearchProvider,
    research_query: ResearchQuery,
) -> tuple[list[SearchResult], list[str]]:
    collected: list[SearchResult] = []
    provider_errors: list[str] = []
    seen: set[str] = set()
    per_question_limit = max(
        1,
        ceil(research_query.max_results / len(research_query.questions)),
    )

    for question in research_query.questions:
        if len(collected) >= research_query.max_results:
            break
        try:
            results = provider.search(question, max_results=per_question_limit)
        except Exception as exc:
            provider_errors.append(f"{provider.name} failed safely for `{question}`: {exc}")
            break

        for result in results:
            if not result.is_valid:
                provider_errors.append(
                    f"Skipped invalid search result from {provider.name} for `{question}`: "
                    "missing title or valid http(s) URL."
                )
                continue
            key = _dedupe_key(result)
            if key in seen:
                continue
            seen.add(key)
            collected.append(
                SearchResult(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    provider=result.provider,
                    query=result.query,
                    rank=len(collected) + 1,
                    published_at=result.published_at,
                )
            )
            if len(collected) >= research_query.max_results:
                break

    return collected, provider_errors


def _dedupe_key(result: SearchResult) -> str:
    if result.url:
        return result.url.strip().lower()
    return result.title.strip().lower()


def _summarize_results(
    research_query: ResearchQuery,
    results: Sequence[SearchResult],
) -> str:
    if not results:
        return (
            f"No source candidates were collected for `{research_query.topic}`. "
            "Keep conclusions empty until at least two independent sources are available."
        )

    provider_names = sorted({result.provider for result in results})
    source_word = "source" if len(results) == 1 else "sources"
    return (
        f"Collected {len(results)} {source_word} for `{research_query.topic}` "
        f"from {', '.join(provider_names)}. Treat this as raw research context: "
        "compare sources before drawing conclusions, and prefer primary sources when available."
    )


def _build_limitations(
    provider_name: str,
    results: Sequence[SearchResult],
    provider_errors: Sequence[str],
) -> list[str]:
    limitations: list[str] = []
    limitations.extend(provider_errors)
    if provider_name == "mock-offline":
        limitations.append(
            "Offline mock provider was used; install/configure a real free provider for fresh internet results."
        )
    if len(results) < 2:
        limitations.append(
            "Fewer than two independent source candidates were collected, so conclusions should remain tentative."
        )
    return limitations
