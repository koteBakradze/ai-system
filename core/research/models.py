from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def is_valid_source_url(url: str) -> bool:
    clean_url = (url or "").strip().lower()
    return clean_url.startswith(("http://", "https://"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ResearchQuery:
    topic: str
    questions: tuple[str, ...]
    max_results: int = 8
    provider: str = "auto"

    @classmethod
    def from_topic(
        cls,
        topic: str,
        max_results: int = 8,
        provider: str = "auto",
    ) -> "ResearchQuery":
        clean_topic = " ".join((topic or "").split())
        if not clean_topic:
            raise ValueError("Research topic cannot be empty.")

        questions = (
            clean_topic,
            f"{clean_topic} recent facts sources",
            f"{clean_topic} limitations risks best practices",
        )
        return cls(
            topic=clean_topic,
            questions=questions,
            max_results=max(0, max_results),
            provider=provider,
        )


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    query: str
    rank: int
    published_at: str | None = None

    @property
    def is_valid(self) -> bool:
        return bool(self.title.strip()) and is_valid_source_url(self.url)


@dataclass(frozen=True)
class ResearchReport:
    query: ResearchQuery
    provider_name: str
    results: tuple[SearchResult, ...]
    summary: str
    generated_at: str = field(default_factory=utc_now_iso)
    safety_notes: tuple[str, ...] = (
        "Search results are source leads, not verified truth.",
        "Raw source metadata is kept separate from final conclusions.",
        "Do not make code, shell, or account changes directly from internet content.",
    )
    limitations: tuple[str, ...] = ()

    @property
    def source_count(self) -> int:
        return len(self.results)
