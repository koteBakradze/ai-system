from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.tools.file_tools import redact_secrets


@dataclass(frozen=True)
class ResearchContextSource:
    title: str
    url: str
    snippet: str
    provider: str = "unknown"
    query: str = ""
    published_at: str | None = None


@dataclass(frozen=True)
class ResearchContextPack:
    topic: str
    summary: str
    useful_facts: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    tools_projects_mentioned: tuple[str, ...]
    sources: tuple[ResearchContextSource, ...]
    original_report_path: str
    generated_at: str
    provider_name: str
    slug: str

    @property
    def source_count(self) -> int:
        return len(self.sources)


KNOWN_TOOL_NAMES = (
    "AI_SYSTEM",
    "Aider",
    "Brave Search",
    "ChatGPT",
    "Claude Code",
    "Codex",
    "Continue",
    "Cursor",
    "DDGS",
    "DuckDuckGo",
    "GitHub Copilot",
    "LM Studio",
    "LangChain",
    "LlamaIndex",
    "Ollama",
    "OpenRouter",
    "Qwen",
    "RAG",
    "VS Code",
    "llama.cpp",
)

COMMON_CAPITALIZED_WORDS = {
    "A",
    "An",
    "And",
    "Best",
    "Guide",
    "LLM",
    "Local",
    "No",
    "Research",
    "Source",
    "The",
    "This",
    "Workflow",
}


def build_context_pack(report_path: Path) -> ResearchContextPack:
    path = Path(report_path)
    report_text = path.read_text(encoding="utf-8")
    topic = _extract_topic(report_text, path)
    sources = tuple(extract_sources_from_report(report_text))
    provider_name = _extract_metadata_value(report_text, "Provider") or _provider_from_sources(sources)

    return ResearchContextPack(
        topic=topic,
        summary=_build_summary(report_text, sources),
        useful_facts=tuple(_build_useful_facts(report_text, sources)),
        recommended_actions=tuple(_build_recommended_actions(topic, sources)),
        tools_projects_mentioned=tuple(_extract_tools_projects(topic, sources)),
        sources=sources,
        original_report_path=_display_path(path),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        provider_name=provider_name or "unknown",
        slug=slugify_title(topic or path.stem),
    )


def save_context_pack(pack: ResearchContextPack, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{pack.slug}.md"
    path.write_text(redact_secrets(render_context_pack(pack)), encoding="utf-8")
    return path


def extract_sources_from_report(report_text: str) -> list[ResearchContextSource]:
    source_section = _extract_section(report_text, "Source Candidates")
    sources = _extract_sources_from_candidate_section(source_section)
    if sources:
        return sources
    return _extract_sources_from_raw_notes(_extract_section(report_text, "Raw Research Notes"))


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"^\d{8}-\d{6}-", "", title.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug[:80] or "research-context"


def render_context_pack(pack: ResearchContextPack) -> str:
    return (
        f"# Research Context: {pack.topic}\n\n"
        "## Summary\n\n"
        f"{pack.summary}\n\n"
        "## Useful Facts\n\n"
        f"{_render_bullets(pack.useful_facts)}\n\n"
        "## Recommended Actions\n\n"
        f"{_render_bullets(pack.recommended_actions)}\n\n"
        "## Tools / Projects Mentioned\n\n"
        f"{_render_bullets(pack.tools_projects_mentioned)}\n\n"
        "## Source Links\n\n"
        f"{_render_source_links(pack.sources)}\n\n"
        "## Metadata\n\n"
        f"- Original report path: `{pack.original_report_path}`\n"
        f"- Generated timestamp: `{pack.generated_at}`\n"
        f"- Source count: {pack.source_count}\n"
        f"- Provider name: `{pack.provider_name}`\n"
    )


def _extract_sources_from_candidate_section(section_text: str) -> list[ResearchContextSource]:
    sources: list[ResearchContextSource] = []
    for match in re.finditer(r"(?ms)^###\s+(?:\d+\.\s+)?(.+?)\n(.*?)(?=^###\s+|\Z)", section_text):
        title = _one_line(match.group(1))
        body = match.group(2)
        url = _extract_bullet_value(body, "URL")
        query = _extract_bullet_value(body, "Search query")
        provider = _strip_markdown_code(_extract_bullet_value(body, "Provider") or "unknown")
        published_at = _extract_bullet_value(body, "Published") or None
        snippet = _extract_snippet_from_source_body(body)
        sources.append(
            ResearchContextSource(
                title=title or "Untitled source",
                url=url or "No URL returned",
                snippet=snippet,
                provider=provider,
                query=query,
                published_at=published_at,
            )
        )
    return sources


def _extract_sources_from_raw_notes(section_text: str) -> list[ResearchContextSource]:
    sources: list[ResearchContextSource] = []
    for match in re.finditer(
        r"(?ms)^-\s+(.+?)\n\s+URL:\s*(.+?)\n\s+Snippet:\s*(.*?)(?=\n-\s+|\Z)",
        section_text,
    ):
        sources.append(
            ResearchContextSource(
                title=_one_line(match.group(1)) or "Untitled source",
                url=_one_line(match.group(2)) or "No URL returned",
                snippet=_one_line(match.group(3)),
            )
        )
    return sources


def _extract_topic(report_text: str, path: Path) -> str:
    match = re.search(r"(?m)^#\s+Fresh Research Report:\s*(.+?)\s*$", report_text)
    if match:
        return _one_line(match.group(1))
    match = re.search(r"(?m)^#\s+(.+?)\s*$", report_text)
    if match:
        return _one_line(match.group(1).replace("Research Context:", "", 1))
    return re.sub(r"^\d{8}-\d{6}-", "", path.stem).replace("-", " ").strip() or path.stem


def _extract_metadata_value(report_text: str, key: str) -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(key)}:\s*(.+?)\s*$", report_text)
    if not match:
        return ""
    return _strip_markdown_code(match.group(1).strip())


def _provider_from_sources(sources: tuple[ResearchContextSource, ...]) -> str:
    providers = sorted({source.provider for source in sources if source.provider and source.provider != "unknown"})
    return ", ".join(providers)


def _extract_section(report_text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)", report_text)
    return match.group(1).strip() if match else ""


def _extract_bullet_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(key)}:\s*(.+?)\s*$", text)
    return _one_line(match.group(1)) if match else ""


def _extract_snippet_from_source_body(body: str) -> str:
    snippet_lines: list[str] = []
    metadata_line = re.compile(r"^-\s+(URL|Search query|Provider|Published):")
    for line in body.splitlines():
        if not line.strip() or metadata_line.match(line):
            continue
        snippet_lines.append(line.strip())
    return _one_line(" ".join(snippet_lines))


def _build_summary(report_text: str, sources: tuple[ResearchContextSource, ...]) -> str:
    source_sentences = _sentences_from_text(" ".join(source.snippet for source in sources if source.snippet))
    if source_sentences:
        return " ".join(source_sentences[:2])

    report_summary = _extract_section(report_text, "Summary")
    summary_sentences = _sentences_from_text(report_summary)
    if summary_sentences:
        return " ".join(summary_sentences[:2])

    return "The report does not include enough source content to summarize safely."


def _build_useful_facts(
    report_text: str,
    sources: tuple[ResearchContextSource, ...],
) -> list[str]:
    facts = _unique_lines(_sentences_from_text(" ".join(source.snippet for source in sources if source.snippet)))
    if not facts:
        facts = _unique_lines(_sentences_from_text(_extract_section(report_text, "Summary")))
    return facts[:6] or ["No source-backed facts were available in the report."]


def _build_recommended_actions(topic: str, sources: tuple[ResearchContextSource, ...]) -> list[str]:
    if not sources:
        return [
            f"Suggested: Re-run research for `{topic}` with a real free provider before changing AI_SYSTEM guidance.",
            "Suggested: Keep this context pack as a marker that the report had no source links.",
        ]

    return [
        "Suggested: Review the preserved source links before changing AI_SYSTEM docs or memory.",
        "Suggested: Move only verified, source-backed guidance into `memory/context/`.",
        "Suggested: Keep the raw report in `workspace/research/` and use this compact pack for local model prompts.",
    ]


def _extract_tools_projects(
    topic: str,
    sources: tuple[ResearchContextSource, ...],
) -> list[str]:
    searchable = " ".join([topic, *[source.title for source in sources], *[source.snippet for source in sources]])
    found: list[str] = []

    for name in KNOWN_TOOL_NAMES:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", searchable, flags=re.IGNORECASE):
            found.append(name)

    for match in re.finditer(r"\b[A-Z][A-Za-z0-9.+#/-]*(?:\s+[A-Z][A-Za-z0-9.+#/-]*){0,3}\b", searchable):
        candidate = _one_line(match.group(0))
        if candidate in COMMON_CAPITALIZED_WORDS or len(candidate) < 2:
            continue
        if candidate not in found:
            found.append(candidate)

    return found[:12] or ["None confidently extracted from the report."]


def _sentences_from_text(text: str) -> list[str]:
    normalized = _one_line(_strip_markdown_code(text))
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [_truncate_sentence(part) for part in parts if _truncate_sentence(part)]


def _truncate_sentence(sentence: str, limit: int = 180) -> str:
    clean = _one_line(sentence).strip("- ")
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "."


def _unique_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
    return unique


def _render_bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _render_source_links(sources: tuple[ResearchContextSource, ...]) -> str:
    if not sources:
        return "- No source links available in the report."
    return "\n".join(f"- {_one_line(source.title)} — {_one_line(source.url)}" for source in sources)


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _strip_markdown_code(text: str) -> str:
    return text.strip().strip("`").strip()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()
