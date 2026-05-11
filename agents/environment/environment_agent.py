from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.tools.file_tools import PROJECT_ROOT, list_project_files
from core.tools.memory_writer import (
    save_context_memory,
    save_environment_report,
)
from core.tools.safe_shell import run_many


ENVIRONMENT_COMMANDS = [
    "platform_summary",
    "sw_vers",
    "uname",
    "python_version",
    "pip_list",
    "ollama_list",
    "git_branch",
    "git_status",
]


class EnvironmentAgent:
    def create_environment_snapshot(self) -> dict[str, str]:
        captured_at = datetime.now(timezone.utc).isoformat()
        results = run_many(ENVIRONMENT_COMMANDS)

        system_sections = [f"- Captured: {captured_at}", f"- Project root: `{PROJECT_ROOT}`"]
        installed_sections = [f"- Captured: {captured_at}"]

        for result in results:
            section = self._format_command_result(result)
            if result["command"] in {"platform_summary", "sw_vers", "uname"}:
                system_sections.append(section)
            else:
                installed_sections.append(section)

        system_body = "\n\n".join(system_sections)
        installed_body = "\n\n".join(installed_sections)
        report_body = (
            f"- Captured: {captured_at}\n\n"
            "## System\n\n"
            f"{system_body}\n\n"
            "## Installed Tools\n\n"
            f"{installed_body}\n"
        )

        system_path = save_context_memory(
            "SYSTEM_CONTEXT.md",
            "SYSTEM CONTEXT",
            system_body,
        )
        tools_path = save_context_memory(
            "INSTALLED_TOOLS.md",
            "INSTALLED TOOLS",
            installed_body,
        )
        report_path = save_environment_report("Environment Snapshot", report_body)

        return {
            "system_context": _relative(system_path),
            "installed_tools": _relative(tools_path),
            "report": _relative(report_path),
        }

    def create_project_context_snapshot(
        self,
        max_depth: int = 4,
        max_files: int = 300,
    ) -> dict[str, str]:
        captured_at = datetime.now(timezone.utc).isoformat()
        files = list_project_files(max_depth=max_depth, max_files=max_files)
        file_lines = "\n".join(f"- `{file}`" for file in files)
        body = (
            f"- Captured: {captured_at}\n"
            f"- Project root: `{PROJECT_ROOT}`\n"
            f"- Max depth: {max_depth}\n"
            f"- Files listed: {len(files)}\n\n"
            "## Safe Project Files\n\n"
            f"{file_lines}\n"
        )

        context_path = save_context_memory(
            "PROJECT_CONTEXT.md",
            "PROJECT CONTEXT",
            body,
        )
        report_path = save_environment_report("Project Context Snapshot", body)

        return {
            "project_context": _relative(context_path),
            "report": _relative(report_path),
        }

    def create_all_snapshots(self) -> dict[str, dict[str, str]]:
        return {
            "environment": self.create_environment_snapshot(),
            "project": self.create_project_context_snapshot(),
        }

    def build_doctor_context(
        self,
        local_models: dict[str, str],
        openrouter_status: dict,
        openrouter_config: dict,
        available_tools: dict[str, str],
    ) -> str:
        captured_at = datetime.now(timezone.utc).isoformat()
        results = run_many(ENVIRONMENT_COMMANDS)
        files = list_project_files(max_depth=4, max_files=120)
        memory_status = self._memory_file_status()
        required_paths = self._required_path_status(
            [
                "main.py",
                "core/router/router.py",
                "core/models/model_manager.py",
                "core/models/openrouter_client.py",
                "core/tools/tool_registry.py",
                "configs/models/local_models.json",
                "configs/models/openrouter_models.json",
                "memory/context",
                "tests",
            ]
        )

        sections = [
            "# AI_SYSTEM Doctor Context",
            "",
            f"- Captured: {captured_at}",
            f"- Project root: `{PROJECT_ROOT}`",
            f"- Safe files sampled: {len(files)}",
            "",
            "## System Checks",
            "",
            self._format_command_table(results),
            "",
            "## Local Model Roles",
            "",
            self._format_json(local_models),
            "",
            "## OpenRouter Status",
            "",
            self._format_json(openrouter_status),
            "",
            "## OpenRouter Safety Config",
            "",
            self._format_json(
                {
                    "enabled": openrouter_config.get("enabled"),
                    "strict_free_only": openrouter_config.get("strict_free_only"),
                    "require_discovered_free_models": openrouter_config.get(
                        "require_discovered_free_models"
                    ),
                    "check_remote_key_usage": openrouter_config.get(
                        "check_remote_key_usage"
                    ),
                    "default": openrouter_config.get("default"),
                    "fallback_models": openrouter_config.get("fallback_models"),
                    "limits": openrouter_config.get("limits"),
                    "discovered_at": openrouter_config.get("discovered_at"),
                    "discovered_free_models_count": len(
                        openrouter_config.get("discovered_free_models") or []
                    ),
                }
            ),
            "",
            "## Memory Files",
            "",
            self._format_json(memory_status),
            "",
            "## Required Paths",
            "",
            self._format_json(required_paths),
            "",
            "## Safe Tool Registry",
            "",
            self._format_json(available_tools),
        ]
        return "\n".join(sections)

    def build_model_status_context(
        self,
        local_models: dict[str, str],
        openrouter_status: dict,
        openrouter_config: dict,
    ) -> str:
        local_lines = [
            f"- `{role}` -> `{model}`" for role, model in sorted(local_models.items())
        ]
        discovered = openrouter_config.get("discovered_free_models") or []
        discovered_lines = [
            f"- `{model.get('id')}` context={model.get('context_length')}"
            for model in discovered[:20]
        ]
        if not discovered_lines:
            discovered_lines = ["- No discovered free models cached."]

        sections = [
            "# AI_SYSTEM Model Status Context",
            "",
            f"- Captured: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Local Role Routing",
            "",
            *local_lines,
            "",
            "## OpenRouter Usage And Budget",
            "",
            self._format_json(openrouter_status),
            "",
            "## Free Model Discovery Cache",
            "",
            f"- Discovered at: {openrouter_config.get('discovered_at')}",
            f"- Cached model count: {len(discovered)}",
            *discovered_lines,
            "",
            "## Recommended Default Routing",
            "",
            "- `general`, `doctor`, `project_brief`, `memory_audit`, `model_status`, and `tool_ideas`: local orchestrator.",
            "- `coding`: local coding model.",
            "- `fast`: local fast model.",
            "- `review` and `system_review`: local first, OpenRouter free multi-review only when budget allows.",
            "- `api`: OpenRouter free model only, guarded by free-only validation and usage limits.",
        ]
        return "\n".join(sections)

    def _format_command_result(self, result: dict[str, object]) -> str:
        label = result.get("label") or result.get("command")
        stdout = str(result.get("stdout") or "").strip()
        stderr = str(result.get("stderr") or "").strip()
        status = "ok" if result.get("ok") else "unavailable"

        lines = [f"## {label}", "", f"- Status: {status}"]
        if stdout:
            lines.extend(["", "```text", stdout, "```"])
        if stderr:
            lines.extend(["", "```text", stderr, "```"])
        return "\n".join(lines)

    def _format_command_table(self, results: list[dict[str, object]]) -> str:
        lines = ["| Check | Status | Details |", "| --- | --- | --- |"]
        for result in results:
            status = "ok" if result.get("ok") else "unavailable"
            detail = str(result.get("stderr") or result.get("stdout") or "").strip()
            detail = detail.splitlines()[0] if detail else ""
            lines.append(
                f"| {result.get('label') or result.get('command')} | {status} | {detail} |"
            )
        return "\n".join(lines)

    def _memory_file_status(self) -> list[dict[str, object]]:
        context_dir = PROJECT_ROOT / "memory" / "context"
        if not context_dir.exists():
            return [{"path": "memory/context", "exists": False}]

        statuses = []
        for path in sorted(context_dir.glob("*.md")):
            statuses.append(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "modified_utc": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                }
            )
        return statuses

    def _required_path_status(self, relative_paths: list[str]) -> list[dict[str, object]]:
        statuses = []
        for relative_path in relative_paths:
            path = PROJECT_ROOT / relative_path
            statuses.append(
                {
                    "path": relative_path,
                    "exists": path.exists(),
                    "type": "directory" if path.is_dir() else "file",
                }
            )
        return statuses

    def _format_json(self, data: object) -> str:
        return "```json\n" + json.dumps(data, indent=2, sort_keys=True) + "\n```"


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()
