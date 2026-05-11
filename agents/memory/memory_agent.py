from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher

from core.tools.file_tools import PROJECT_ROOT, read_project_file


class MemoryAgent:
    def build_memory_audit_context(self, user_prompt: str = "") -> str:
        context_dir = PROJECT_ROOT / "memory" / "context"
        files = sorted(context_dir.glob("*.md")) if context_dir.exists() else []
        summaries = []
        contents: dict[str, str] = {}

        for path in files:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            content = read_project_file(relative, max_bytes=60_000)
            contents[relative] = content
            headings = [
                line.strip()
                for line in content.splitlines()
                if line.lstrip().startswith("#")
            ][:8]
            summaries.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "lines": len(content.splitlines()),
                    "modified_utc": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                    "headings": headings,
                    "signals": self._signals_for(content),
                }
            )

        sections = [
            "# Memory Audit Context",
            "",
            f"- Captured: {datetime.now(timezone.utc).isoformat()}",
            f"- Context files found: {len(files)}",
            f"- User focus: {user_prompt or 'general memory health'}",
            "",
            "## File Summaries",
            "",
            self._format_summaries(summaries),
            "",
            "## Similarity Signals",
            "",
            self._format_similarity(contents),
            "",
            "## Audit Instructions",
            "",
            "- Identify stale, duplicated, missing, or conflicting context.",
            "- Propose concrete fixes but do not rewrite memory files.",
            "- Prioritize context that affects model routing, safety, local tools, and project purpose.",
        ]
        return "\n".join(sections)

    def _signals_for(self, content: str) -> list[str]:
        lowered = content.lower()
        signals = []
        if "todo" in lowered or "fixme" in lowered:
            signals.append("contains todo/fixme")
        if "unavailable" in lowered or "failed" in lowered:
            signals.append("contains unavailable/failed status")
        if "openrouter_api_key" in lowered or "<redacted>" in lowered:
            signals.append("contains redacted secret-related content")
        if len(content.strip()) < 120:
            signals.append("very short")
        return signals or ["no obvious issue"]

    def _format_summaries(self, summaries: list[dict[str, object]]) -> str:
        if not summaries:
            return "- No markdown context files found."

        lines = []
        for summary in summaries:
            headings = ", ".join(summary["headings"]) or "no headings"
            signals = ", ".join(summary["signals"])
            lines.append(
                f"- `{summary['path']}`: {summary['lines']} lines, "
                f"{summary['bytes']} bytes, headings: {headings}; signals: {signals}"
            )
        return "\n".join(lines)

    def _format_similarity(self, contents: dict[str, str]) -> str:
        paths = list(contents)
        if len(paths) < 2:
            return "- Not enough memory files to compare."

        lines = []
        for index, first in enumerate(paths):
            for second in paths[index + 1 :]:
                ratio = SequenceMatcher(
                    None,
                    self._normalize(contents[first]),
                    self._normalize(contents[second]),
                ).ratio()
                if ratio >= 0.55:
                    lines.append(f"- `{first}` and `{second}` similarity: {ratio:.2f}")

        return "\n".join(lines) if lines else "- No high-similarity files detected."

    def _normalize(self, content: str) -> str:
        return " ".join(content.lower().split())[:12_000]


memory_agent = MemoryAgent()
