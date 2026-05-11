from __future__ import annotations

from datetime import datetime, timezone

from core.tools.file_tools import PROJECT_ROOT, list_project_files, read_project_file


SYSTEM_REVIEW_FILES = [
    "README.md",
    "main.py",
    "core/router/router.py",
    "core/models/model_manager.py",
    "core/models/openrouter_client.py",
    "core/models/usage_manager.py",
    "core/tools/tool_registry.py",
    "core/tools/safe_shell.py",
    "core/tools/file_tools.py",
    "core/tools/memory_writer.py",
    "tests/test_safe_tools.py",
    "tests/test_openrouter_safety.py",
]


class PlannerAgent:
    def build_system_review_context(self, user_prompt: str = "") -> str:
        return self._build_selected_project_context(
            title="AI_SYSTEM Self-Review Context",
            user_prompt=user_prompt or "review architecture, safety, and maintainability",
            instructions=[
                "Review correctness, safety, maintainability, and test coverage.",
                "Prioritize actionable issues over broad commentary.",
                "Respect local-first behavior and free-only OpenRouter constraints.",
            ],
        )

    def build_tool_ideas_context(self, user_prompt: str = "") -> str:
        files = list_project_files(max_depth=4, max_files=180)
        sections = [
            "# AI_SYSTEM Tool Ideas Context",
            "",
            f"- Captured: {datetime.now(timezone.utc).isoformat()}",
            f"- Project root: `{PROJECT_ROOT}`",
            f"- User focus: {user_prompt or 'useful future system-maintenance tools'}",
            "",
            "## Existing Capabilities",
            "",
            "- CLI task routing in `main.py` and `core/router/router.py`.",
            "- Local Ollama roles for orchestrator, coding, and fast tasks.",
            "- Optional OpenRouter free-only requests with usage tracking.",
            "- Safe file, shell, and markdown-memory tools.",
            "- Environment snapshots and markdown context loading.",
            "",
            "## Safe File Inventory",
            "",
            "\n".join(f"- `{file}`" for file in files),
            "",
            "## Ranking Instructions",
            "",
            "- Suggest practical system tools that fit this repo.",
            "- Score each idea by value, difficulty, local/API model fit, and safety risk.",
            "- Prefer local-first tools with optional API second opinions.",
            "- Include the smallest useful version for the top ideas.",
        ]
        return "\n".join(sections)

    def _build_selected_project_context(
        self,
        title: str,
        user_prompt: str,
        instructions: list[str],
    ) -> str:
        sections = [
            f"# {title}",
            "",
            f"- Captured: {datetime.now(timezone.utc).isoformat()}",
            f"- Project root: `{PROJECT_ROOT}`",
            f"- User focus: {user_prompt}",
            "",
            "## Key File Excerpts",
        ]

        for relative_path in SYSTEM_REVIEW_FILES:
            path = PROJECT_ROOT / relative_path
            if not path.exists():
                continue
            content = read_project_file(relative_path, max_bytes=70_000)
            sections.extend(
                [
                    "",
                    f"### `{relative_path}`",
                    "",
                    "```text",
                    self._trim(content, 2_800),
                    "```",
                ]
            )

        sections.extend(["", "## Review Instructions", ""])
        sections.extend(f"- {instruction}" for instruction in instructions)
        return "\n".join(sections)

    def _trim(self, content: str, max_chars: int) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rstrip() + "\n\n[excerpt trimmed]"


planner_agent = PlannerAgent()
