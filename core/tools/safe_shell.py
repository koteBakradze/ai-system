from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from core.tools.file_tools import PROJECT_ROOT, redact_secrets


COMMAND_TIMEOUT_SECONDS = 12
MAX_OUTPUT_CHARS = 12_000


@dataclass(frozen=True)
class SafeCommand:
    label: str
    argv: tuple[str, ...]
    description: str


SAFE_COMMANDS: dict[str, SafeCommand] = {
    "python_version": SafeCommand(
        label="Python Version",
        argv=(sys.executable, "--version"),
        description="Show the active Python interpreter version.",
    ),
    "pip_list": SafeCommand(
        label="Pip Packages",
        argv=(sys.executable, "-m", "pip", "list"),
        description="List installed packages in the active Python environment.",
    ),
    "ollama_list": SafeCommand(
        label="Ollama Models",
        argv=("ollama", "list"),
        description="List local Ollama models.",
    ),
    "git_status": SafeCommand(
        label="Git Status",
        argv=("git", "status", "--short"),
        description="Show short git status for the project.",
    ),
    "git_branch": SafeCommand(
        label="Git Branch",
        argv=("git", "branch", "--show-current"),
        description="Show the current git branch.",
    ),
    "sw_vers": SafeCommand(
        label="macOS Version",
        argv=("sw_vers",),
        description="Show macOS product/version information.",
    ),
    "uname": SafeCommand(
        label="Kernel",
        argv=("uname", "-mrs"),
        description="Show kernel name, release, and machine architecture.",
    ),
}


class SafeShellError(ValueError):
    pass


def available_commands() -> dict[str, str]:
    return {name: command.description for name, command in SAFE_COMMANDS.items()}


def run_safe_command(name: str) -> dict[str, object]:
    if name == "platform_summary":
        return _platform_summary()

    command = SAFE_COMMANDS.get(name)
    if command is None:
        allowed = ", ".join(sorted([*SAFE_COMMANDS, "platform_summary"]))
        raise SafeShellError(f"Command is not whitelisted. Allowed commands: {allowed}.")

    executable = command.argv[0]
    if shutil.which(executable) is None and not executable.startswith("/"):
        return {
            "command": name,
            "label": command.label,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{executable} is not installed or not on PATH.",
        }

    try:
        completed = subprocess.run(
            command.argv,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "command": name,
            "label": command.label,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds.",
        }

    return {
        "command": name,
        "label": command.label,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": _trim(redact_secrets(completed.stdout)),
        "stderr": _trim(redact_secrets(completed.stderr)),
    }


def run_many(command_names: list[str]) -> list[dict[str, object]]:
    return [run_safe_command(name) for name in command_names]


def _platform_summary() -> dict[str, object]:
    lines = [
        f"System: {platform.system()}",
        f"Release: {platform.release()}",
        f"Version: {platform.version()}",
        f"Machine: {platform.machine()}",
        f"Python: {platform.python_version()}",
        f"Project root: {PROJECT_ROOT}",
    ]
    return {
        "command": "platform_summary",
        "label": "Platform Summary",
        "ok": True,
        "returncode": 0,
        "stdout": "\n".join(lines),
        "stderr": "",
    }


def _trim(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"{text[:MAX_OUTPUT_CHARS]}\n\n[output trimmed]"
