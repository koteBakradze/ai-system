from __future__ import annotations

from typing import Any, Callable

from agents.environment.environment_agent import EnvironmentAgent
from core.tools.file_tools import list_project_files, read_project_file
from core.tools.memory_writer import save_observation
from core.tools.safe_shell import available_commands, run_safe_command


class ToolRegistryError(ValueError):
    pass


ToolFunction = Callable[..., Any]


class ToolRegistry:
    def __init__(self, environment_agent: EnvironmentAgent | None = None):
        self.environment_agent = environment_agent or EnvironmentAgent()
        self._tools: dict[str, ToolFunction] = {
            "list_project_files": list_project_files,
            "read_project_file": read_project_file,
            "run_system_check": run_safe_command,
            "save_observation": save_observation,
            "create_environment_snapshot": self.environment_agent.create_environment_snapshot,
            "create_project_context_snapshot": self.environment_agent.create_project_context_snapshot,
        }

    def list_tools(self) -> dict[str, str]:
        return {
            "list_project_files": "List safe project files, excluding blocked folders and secrets.",
            "read_project_file": "Read a safe .md, .py, or .json file from this project.",
            "run_system_check": (
                "Run a named whitelisted read-only command. Allowed: "
                + ", ".join(sorted([*available_commands(), "platform_summary"]))
            ),
            "save_observation": "Write an observation markdown file under memory/observations.",
            "create_environment_snapshot": "Create markdown snapshots of safe local environment data.",
            "create_project_context_snapshot": "Create markdown snapshots of safe project file context.",
        }

    def call_tool(self, tool_name: str, **kwargs):
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolRegistryError(f"Unknown tool: {tool_name}")
        return tool(**kwargs)


tool_registry = ToolRegistry()
