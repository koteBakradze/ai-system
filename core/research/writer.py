from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from core.research.models import ResearchReport, SearchResult
from core.tools.file_tools import PROJECT_ROOT, redact_secrets


RESEARCH_REPORT_DIR = PROJECT_ROOT / "workspace" / "research"


def save_research_report(
    report: ResearchReport,
    output_dir: Path | None = None,
) -> Path:
    destination = output_dir or RESEARCH_REPORT_DIR
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slugify(report.query.topic)
    path = destination / f"{timestamp}-{slug}.md"
    path.write_text(redact_secrets(render_research_report(report)), encoding="utf-8")
    return path


def render_research_report(report: ResearchReport) -> str:
    sections = [
        f"# Fresh Research Report: {report.query.topic}",
        "",
        f"- Generated: {report.generated_at}",
        f"- Provider: `{report.provider_name}`",
        f"- Search query: {report.query.topic}",
        f"- Source count: {report.source_count}",
        f"- Max results: {report.query.max_results}",
        "",
        "## Safety Notes",
        "",
        "\n".join(f"- {note}" for note in report.safety_notes),
        "",
        "## Research Questions",
        "",
        "\n".join(f"- {question}" for question in report.query.questions),
        "",
        "## Summary",
        "",
        report.summary,
    ]

    if report.limitations:
        sections.extend(
            [
                "",
                "## Limitations",
                "",
                "\n".join(f"- {limitation}" for limitation in report.limitations),
            ]
        )

    sections.extend(["", "## Sources", ""])
    if report.results:
        for result in report.results:
            sections.append(_render_source(result))
            sections.append("")
    else:
        sections.append("No sources collected.")
        sections.append("")

    sections.extend(["## Source Candidates", ""])
    if report.results:
        for result in report.results:
            sections.append(_render_result(result))
            sections.append("")
    else:
        sections.append("No source candidates collected.")
        sections.append("")

    sections.extend(
        [
            "## Raw Research Notes",
            "",
            _render_raw_notes(report),
            "",
            "## Final Conclusions",
            "",
            "No final conclusions are asserted by the gateway. Review the raw source metadata first.",
            "",
        ]
    )
    return "\n".join(sections).rstrip() + "\n"


def _render_result(result: SearchResult) -> str:
    lines = [
        f"### {result.rank}. {result.title}",
        "",
        f"- URL: {result.url or 'No URL returned'}",
        f"- Search query: {result.query}",
        f"- Provider: `{result.provider}`",
    ]
    if result.published_at:
        lines.append(f"- Published: {result.published_at}")
    lines.extend(["", result.snippet or "(empty snippet)"])
    return "\n".join(lines)


def _render_source(result: SearchResult) -> str:
    return "\n".join(
        [
            f"{result.rank}. [{result.title}]({result.url})",
            f"   - Snippet: {result.snippet or '(empty snippet)'}",
            f"   - Provider: {result.provider}",
            f"   - Query: {result.query}",
        ]
    )


def _render_raw_notes(report: ResearchReport) -> str:
    if not report.results:
        return "No raw source metadata is available."
    return "\n\n".join(
        f"- {result.title}\n  URL: {result.url}\n  Snippet: {result.snippet or '(empty snippet)'}"
        for result in report.results
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "research"
