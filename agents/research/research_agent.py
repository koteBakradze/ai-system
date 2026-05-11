from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.tools.file_tools import PROJECT_ROOT, list_project_files, read_project_file
from core.tools.memory_writer import save_context_memory


PROJECT_BRIEF_FILES = [
    "README.md",
    "main.py",
    "core/router/router.py",
    "core/models/model_manager.py",
    "core/models/openrouter_client.py",
    "core/tools/tool_registry.py",
    "core/tools/safe_shell.py",
    "core/tools/file_tools.py",
    "configs/models/local_models.json",
    "configs/models/openrouter_models.json",
    "tests/test_safe_tools.py",
    "tests/test_openrouter_safety.py",
]


class ResearchAgent:
    def build_project_brief_context(self, user_prompt: str = "") -> str:
        files = list_project_files(max_depth=4, max_files=180)
        sections = [
            "# Project Brief Source Context",
            "",
            f"- Captured: {datetime.now(timezone.utc).isoformat()}",
            f"- Project root: `{PROJECT_ROOT}`",
            f"- User focus: {user_prompt or 'current architecture and capabilities'}",
            f"- Safe files found: {len(files)}",
            "",
            "## Safe File Inventory",
            "",
            "\n".join(f"- `{file}`" for file in files),
            "",
            "## Key File Excerpts",
        ]

        for relative_path in PROJECT_BRIEF_FILES:
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
                    self._trim(content, 3_000),
                    "```",
                ]
            )

        sections.extend(
            [
                "",
                "## Brief Instructions",
                "",
                "- Summarize what AI_SYSTEM does today.",
                "- Name the local/API model split and safety constraints.",
                "- List the highest-value current extension points.",
                "- Keep it concise enough to be loaded as memory.",
            ]
        )
        return "\n".join(sections)

    def save_project_brief(self, body: str) -> Path:
        return save_context_memory("PROJECT_BRIEF.md", "PROJECT BRIEF", body)

    def deterministic_project_brief(self) -> str:
        files = list_project_files(max_depth=4, max_files=180)
        return "\n".join(
            [
                "- AI_SYSTEM is a terminal-first local AI orchestration project.",
                "- Local Ollama roles are configured in `configs/models/local_models.json`.",
                "- OpenRouter is optional, free-only, usage-tracked, and guarded before API calls.",
                "- Safe project tooling lives under `core/tools` and blocks secrets, path escapes, and arbitrary shell commands.",
                "- Markdown memory in `memory/context` is loaded into normal prompts.",
                f"- Current safe file count sampled for this brief: {len(files)}.",
            ]
        )

    def _trim(self, content: str, max_chars: int) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rstrip() + "\n\n[excerpt trimmed]"


research_agent = ResearchAgent()
