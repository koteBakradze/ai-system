from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUAL_CONTEXT_PATH = PROJECT_ROOT / "docs" / "context" / "CHATGPT_PROJECT_CONTEXT.md"
GENERATED_CONTEXT_PATH = (
    PROJECT_ROOT / "docs" / "context" / "AI_SYSTEM_PROJECT_SUMMARY.generated.md"
)

MANUAL_CONTEXT_TEMPLATE = """# AI_SYSTEM ChatGPT Project Context

## 1. Project Goal

TODO: Summarize the main goal of AI_SYSTEM.

## 2. Current System Overview

TODO: Explain what the AI_SYSTEM currently does.

## 3. Current Folder Structure

TODO: Paste or generate the current folder tree here.

## 4. Already Accomplished

TODO: List what is already working.

Examples:
- Local model workflow
- OpenRouter/free API workflow
- Review workflows
- File/system review actions
- Orchestrators
- Any working scripts
- Any tests
- Any safety checks

## 5. Important Existing Files

TODO: List important files and explain what each one does.

## 6. Current Agents / Actions / Workflows

TODO: Describe all agents, actions, commands, scripts, and workflows that already exist.

## 7. API / Model Usage

TODO: Explain local model usage, API model usage, OpenRouter usage, and any safety limits.

## 8. Safety Rules

TODO: Explain what agents are allowed to do and what they must ask before doing.

## 9. Current Problems / Missing Parts

TODO: List what is still missing or unfinished.

## 10. Recommended Next Steps

TODO: List the next most useful implementation steps.

## 11. How ChatGPT Should Help in This Project

TODO: Explain how ChatGPT Desktop should behave when helping with this project.
"""

BLOCKED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "node_modules",
    "venv",
}
BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".envrc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
}
SOURCE_SUFFIXES = {".md", ".py", ".json", ".txt", ".sh"}
SECRET_KEY_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|"
    r"authorization|bearer|private[_-]?key)"
)
SECRET_VALUE_REPLACEMENTS = (
    (
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*"
            r"['\"]?[^'\"\s,}]+"
        ),
        r"\1=<redacted>",
    ),
    (re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"), "Bearer <redacted>"),
    (
        re.compile(r"(?i)(sk-[a-z0-9_-]{12,}|or-[a-z0-9_-]{12,}|[a-z0-9]{32,})"),
        "<redacted>",
    ),
)

IMPORTANT_FILES = {
    "README.md": "Project overview, setup notes, CLI usage, model providers, and safe-tool summary.",
    "main.py": "Terminal entry point. Routes user-selected task types and saves responses to markdown reports.",
    "core/router/router.py": "LocalOrchestrator task router for local models, OpenRouter reviews, and system-tool workflows.",
    "core/models/model_manager.py": "Model facade for local Ollama roles and OpenRouter calls.",
    "core/models/openrouter_client.py": "Free-only OpenRouter client with model validation, request guards, discovery, and multi-review support.",
    "core/models/usage_manager.py": "Tracks OpenRouter local request usage, daily/minute limits, token counts, and remote key status cache.",
    "core/tools/file_tools.py": "Safe project file listing/reading with path blocking and secret redaction.",
    "core/tools/safe_shell.py": "Whitelisted read-only local command runner for environment checks.",
    "core/tools/tool_registry.py": "Narrow tool registry exposed to agents.",
    "core/tools/memory_writer.py": "Restricted markdown memory/report writer.",
    "core/research/gateway.py": "Collects, validates, deduplicates, and summarizes research source metadata.",
    "core/research/providers.py": "Provides explicit mock/offline and DDGS-backed real search providers.",
    "core/research/writer.py": "Renders and saves markdown research reports.",
    "core/research/context_builder.py": "Builds compact reusable research context packs from saved reports.",
    "agents/environment/environment_agent.py": "Builds local environment, project, doctor, and model-status contexts.",
    "agents/research/research_agent.py": "Builds and saves project brief context.",
    "agents/planning/planner_agent.py": "Builds system-review and tool-ideas contexts.",
    "agents/memory/memory_agent.py": "Audits markdown memory for stale, duplicate, missing, or conflicting context.",
    "memory/load_memory.py": "Loads markdown memory files into normal model prompts.",
    "scripts/scan_environment.py": "Runs safe environment/project snapshots.",
    "scripts/test_openrouter.py": "Optional tiny OpenRouter test guarded by key and usage limits.",
    "scripts/export_project_context.py": "Generates this project-context export without calling model APIs.",
    "configs/models/local_models.json": "Local Ollama role-to-model mapping.",
    "configs/models/openrouter_models.json": "OpenRouter free-only model, review, discovery, and limit configuration.",
    "configs/usage/openrouter_usage.json": "Local OpenRouter usage ledger.",
    "tests/test_safe_tools.py": "Covers safe file/tool restrictions and redaction.",
    "tests/test_openrouter_safety.py": "Covers free-only OpenRouter validation and budget guards.",
    "tests/test_system_tools_pack.py": "Covers system-tool orchestration paths.",
    "tests/test_main_response_reports.py": "Covers markdown response report saving.",
    "tests/test_fresh_research_gateway.py": "Covers research providers, source validation, fallback behavior, and report writing.",
    "tests/test_research_context_builder.py": "Covers compact research context extraction and saving.",
    "tests/test_project_context_export.py": "Covers generated project-context export behavior.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create/update a generated AI_SYSTEM project-context summary for "
            "ChatGPT Desktop project instructions."
        )
    )
    parser.add_argument(
        "--output",
        default=str(GENERATED_CONTEXT_PATH.relative_to(PROJECT_ROOT)),
        help="Generated markdown path, relative to the project root by default.",
    )
    parser.add_argument(
        "--manual",
        default=str(MANUAL_CONTEXT_PATH.relative_to(PROJECT_ROOT)),
        help="Manual template path. Created only if missing.",
    )
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-files", type=int, default=350)
    parser.add_argument(
        "--skip-manual-template",
        action="store_true",
        help="Do not create the manual ChatGPT context template if it is missing.",
    )
    args = parser.parse_args(argv)

    manual_path = resolve_project_path(args.manual)
    output_path = resolve_project_path(args.output)

    created_manual = False
    if not args.skip_manual_template:
        created_manual = ensure_manual_context(manual_path)

    summary = build_project_summary(
        PROJECT_ROOT,
        manual_path=manual_path,
        output_path=output_path,
        max_depth=args.max_depth,
        max_files=args.max_files,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")

    manual_state = "created" if created_manual else "already existed"
    print(f"Manual context template {manual_state}: {relative(PROJECT_ROOT, manual_path)}")
    print(f"Generated project summary: {relative(PROJECT_ROOT, output_path)}")
    return 0


def ensure_manual_context(path: Path) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MANUAL_CONTEXT_TEMPLATE, encoding="utf-8")
    return True


def build_project_summary(
    root: Path,
    *,
    manual_path: Path,
    output_path: Path,
    max_depth: int = 4,
    max_files: int = 350,
) -> str:
    root = root.resolve()
    files = list_project_files(root, max_depth=max_depth, max_files=max_files)
    tree = build_tree(files)
    local_models = read_json_file(root, root / "configs" / "models" / "local_models.json")
    openrouter_config = read_json_file(
        root,
        root / "configs" / "models" / "openrouter_models.json",
    )
    openrouter_usage = read_json_file(
        root,
        root / "configs" / "usage" / "openrouter_usage.json",
    )
    cli_tasks = extract_cli_tasks(root / "main.py")
    system_tasks = extract_system_tasks(root / "core" / "router" / "router.py")
    agents = describe_python_modules(root, "agents")
    scripts = describe_python_modules(root, "scripts")
    tests = sorted(path for path in files if path.startswith("tests/test_"))
    memory_files = sorted(path for path in files if path.startswith("memory/context/"))
    response_reports = sorted(path for path in files if path.startswith("workspace/reports/responses/"))
    environment_reports = sorted(path for path in files if path.startswith("workspace/reports/environment/"))
    existing_important = [
        (path, description)
        for path, description in IMPORTANT_FILES.items()
        if (root / path).exists()
    ]

    sections = [
        "# AI_SYSTEM Generated Project Context",
        "",
        "_Generated by `python scripts/export_project_context.py`._",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Project root: `{root}`",
        f"- Manual template: `{relative(root, manual_path)}`",
        f"- Generated output: `{relative(root, output_path)}`",
        "- API usage: none; this script only scans local files and writes markdown.",
        "",
        "## 1. Project Goal",
        "",
        (
            "AI_SYSTEM is a terminal-first local AI orchestration project. Its default "
            "provider is local Ollama, with optional OpenRouter free-model support for "
            "guarded API tasks and second-opinion reviews."
        ),
        "",
        "## 2. Current System Overview",
        "",
        "- The CLI in `main.py` asks for a task type and prompt, routes through `core/router/router.py`, and saves full responses under `workspace/reports/responses/`.",
        "- Markdown memory in `memory/context` is loaded into model prompts for normal local/API tasks.",
        "- System-tool tasks build deterministic local context for doctor, project brief, memory audit, model status, system review, and tool ideas.",
        "- Research tasks collect explicit mock or real source metadata and save markdown reports under `workspace/research/`.",
        "- Local model roles come from `configs/models/local_models.json`; OpenRouter behavior comes from `configs/models/openrouter_models.json`.",
        "- Safe local tools can list/read selected project files, run whitelisted environment checks, and write only approved markdown memory/report files.",
        "",
        "## 3. Current Folder Structure",
        "",
        f"- Files scanned: {len(files)}",
        f"- Max depth: {max_depth}",
        "",
        "```text",
        tree,
        "```",
        "",
        "## 4. Already Accomplished",
        "",
        "- Local Ollama workflow with configured roles for orchestrator/general, coding, and fast tasks.",
        "- Optional OpenRouter workflow restricted to `openrouter/free` or `:free` models.",
        "- OpenRouter request tracking with daily and per-minute guardrails, safety buffers, and remote key status checks.",
        "- Multi-perspective review flow for correctness, security, and maintainability when free API budget allows.",
        "- Local fallback for review workflows when OpenRouter is unavailable or unsafe to call.",
        "- Doctor, project brief, memory audit, model status, system review, and tool-ideas workflows.",
        "- Safe file, shell, memory writer, and tool registry layers.",
        "- Real research gateway with explicit mock/offline mode, DDGS-backed real mode, saved source metadata, and compact context packs.",
        "- Environment and project context snapshot script.",
        "- CLI project-context export task.",
        "- Markdown response report saving to avoid dumping long model responses into the terminal.",
        f"- Unit tests present: {len(tests)} test files.",
        "",
        "## 5. Important Existing Files",
        "",
        *format_described_paths(existing_important),
        "",
        "## 6. Current Agents / Actions / Workflows",
        "",
        "### CLI Task Types",
        "",
        *format_inline_list("CLI tasks", cli_tasks),
        *format_inline_list("System-tool tasks", system_tasks),
        "",
        "### Agents",
        "",
        *format_described_paths(agents),
        "",
        "### Scripts",
        "",
        *format_described_paths(scripts),
        "",
        "### Tests",
        "",
        *format_paths(tests),
        "",
        "## 7. API / Model Usage",
        "",
        "### Local Ollama Roles",
        "",
        format_json_or_placeholder(local_models, "- No local model config found."),
        "",
        "### OpenRouter Config Summary",
        "",
        format_openrouter_config(openrouter_config),
        "",
        "### OpenRouter Usage Snapshot",
        "",
        format_openrouter_usage(openrouter_usage),
        "",
        "## 8. Safety Rules",
        "",
        "- Do not delete files, reset git state, commit, push, or install packages unless explicitly asked.",
        "- Do not read `.env`, SSH keys, private keys, virtual environments, caches, or secret-looking paths.",
        "- Do not use paid APIs. OpenRouter calls must remain free-only and guarded before requests.",
        "- Prefer local Ollama for normal reasoning, coding, and project-maintenance workflows.",
        "- Safe shell commands are whitelisted; arbitrary shell execution is not exposed through the agent tool registry.",
        "- File reads are limited to safe project paths and selected text-like suffixes, with JSON/key redaction.",
        "- Memory/report writes should stay inside approved markdown paths.",
        "- Large generated outputs should be saved as markdown reports instead of printed directly.",
        "- Mock/offline research must remain clearly labeled and must never be presented as real internet research.",
        "",
        "## 9. Current Problems / Missing Parts",
        "",
        *current_problem_lines(root, memory_files, response_reports, environment_reports),
        "",
        "## 10. Recommended Next Steps",
        "",
        "- Run unit tests after changing code or workflow docs.",
        "- Run mock and real research smoke checks when network access is available.",
        "- Keep `docs/context/CHATGPT_PROJECT_CONTEXT.md` human-curated and refresh this generated summary with `python main.py project_context_export`.",
        "- Start Phase 3 income research workflow design using saved research reports/context packs as inputs.",
        "- Add a context freshness check that compares generated summary timestamps against major source file modification times.",
        "",
        "## 11. How ChatGPT Should Help in This Project",
        "",
        "- Work local-first and prefer deterministic scanners, markdown docs, and tests before model/API calls.",
        "- Preserve existing files and user changes; ask before destructive actions, installs, commits, pushes, or paid/network work.",
        "- Treat `docs/context/CHATGPT_PROJECT_CONTEXT.md` as the manual project instruction source and this generated file as refreshable evidence.",
        "- When changing code, follow existing small-module patterns and keep safety boundaries clear.",
        "- When reviewing, lead with bugs, safety risks, missing tests, and concrete next steps.",
        "- Keep summaries copyable for ChatGPT Desktop project instructions.",
    ]
    return "\n".join(sections).rstrip() + "\n"


def list_project_files(root: Path, *, max_depth: int, max_files: int) -> list[str]:
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if not path.is_file():
            continue
        if not is_safe_path(root, path):
            continue
        if path.suffix and path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        relative_path = path.relative_to(root)
        if len(relative_path.parts) > max_depth:
            continue
        files.append(relative_path.as_posix())
    return files


def build_tree(files: list[str]) -> str:
    if not files:
        return "."

    tree: dict[str, Any] = {}
    for file_path in files:
        cursor = tree
        parts = file_path.split("/")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor.setdefault("__files__", []).append(parts[-1])

    lines = ["."]
    append_tree_lines(lines, tree, prefix="")
    return "\n".join(lines)


def append_tree_lines(lines: list[str], node: dict[str, Any], *, prefix: str) -> None:
    names = sorted(name for name in node if name != "__files__")
    files = sorted(node.get("__files__", []))
    entries = [(name, node[name]) for name in names] + [(name, None) for name in files]

    for index, (name, child) in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "`-- " if is_last else "|-- "
        lines.append(f"{prefix}{branch}{name}")
        if isinstance(child, dict):
            extension = "    " if is_last else "|   "
            append_tree_lines(lines, child, prefix=prefix + extension)


def describe_python_modules(root: Path, folder: str) -> list[tuple[str, str]]:
    base = root / folder
    if not base.exists():
        return []

    descriptions = []
    for path in sorted(base.rglob("*.py")):
        if path.name == "__init__.py" or not is_safe_path(root, path):
            continue
        relative_path = path.relative_to(root).as_posix()
        descriptions.append((relative_path, summarize_python_file(path)))
    return descriptions


def summarize_python_file(path: Path) -> str:
    try:
        module = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return "Python module."

    classes = [node.name for node in module.body if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in module.body if isinstance(node, ast.FunctionDef)]
    parts = []
    if classes:
        parts.append("classes: " + ", ".join(classes[:5]))
    if functions:
        parts.append("functions: " + ", ".join(functions[:6]))
    return "; ".join(parts) + "." if parts else "Python module."


def extract_cli_tasks(path: Path) -> list[str]:
    text = safe_read_text(path)
    task_names = set(re.findall(r'"([a-z_-]+)"', text))
    known = {
        "api",
        "coding",
        "discover",
        "doctor",
        "exit",
        "fast",
        "general",
        "memory_audit",
        "model_status",
        "project_context_export",
        "project_brief",
        "research",
        "research-context",
        "review",
        "system_review",
        "tool_ideas",
        "usage",
    }
    return sorted(task_names & known)


def extract_system_tasks(path: Path) -> list[str]:
    text = safe_read_text(path)
    match = re.search(r"SYSTEM_TOOL_TASKS\s*=\s*\{(?P<body>.*?)\}", text, re.S)
    if not match:
        return []
    return sorted(set(re.findall(r'"([a-z_]+)"', match.group("body"))))


def read_json_file(root: Path, path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists() or not is_safe_path(root, path):
        return None

    try:
        return redact_json(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return {"error": "invalid JSON"}


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            if SECRET_KEY_RE.search(str(key)):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_json(child)
        return redacted
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_VALUE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return redact_text(path.read_text(encoding="utf-8", errors="replace"))


def format_json_or_placeholder(value: Any, placeholder: str) -> str:
    if value is None:
        return placeholder
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"


def format_openrouter_config(config: Any) -> str:
    if not isinstance(config, dict):
        return "- No OpenRouter config found."

    discovered = config.get("discovered_free_models") or []
    limits = config.get("limits") or {}
    summary = {
        "enabled": config.get("enabled"),
        "strict_free_only": config.get("strict_free_only"),
        "require_discovered_free_models": config.get("require_discovered_free_models"),
        "check_remote_key_usage": config.get("check_remote_key_usage"),
        "default": config.get("default"),
        "fallback_models": config.get("fallback_models"),
        "max_review_models": config.get("max_review_models"),
        "discovered_at": config.get("discovered_at"),
        "discovered_free_models_count": len(discovered),
        "limits": limits,
    }
    return "```json\n" + json.dumps(summary, indent=2, sort_keys=True) + "\n```"


def format_openrouter_usage(usage: Any) -> str:
    if not isinstance(usage, dict):
        return "- No OpenRouter usage file found."

    summary = {
        "date": usage.get("date"),
        "requests_today": usage.get("requests_today"),
        "successful_requests_today": usage.get("successful_requests_today"),
        "failed_requests_today": usage.get("failed_requests_today"),
        "estimated_cost": usage.get("estimated_cost"),
        "last_request": usage.get("last_request"),
        "model_counts": usage.get("model_counts"),
        "purpose_counts": usage.get("purpose_counts"),
    }
    return "```json\n" + json.dumps(summary, indent=2, sort_keys=True) + "\n```"


def format_described_paths(items: list[tuple[str, str]]) -> list[str]:
    if not items:
        return ["- None found."]
    return [f"- `{path}`: {description}" for path, description in items]


def format_paths(paths: list[str]) -> list[str]:
    if not paths:
        return ["- None found."]
    return [f"- `{path}`" for path in paths]


def format_inline_list(label: str, values: list[str]) -> list[str]:
    if not values:
        return [f"- {label}: none found."]
    joined = ", ".join(f"`{value}`" for value in values)
    return [f"- {label}: {joined}."]


def current_problem_lines(
    root: Path,
    memory_files: list[str],
    response_reports: list[str],
    environment_reports: list[str],
) -> list[str]:
    problems = []
    if file_is_empty(root / "docs" / "ARCHITECTURE.md"):
        problems.append("- `docs/ARCHITECTURE.md` is empty.")
    if file_is_empty(root / "docs" / "ROADMAP.md"):
        problems.append("- `docs/ROADMAP.md` is empty.")
    if not memory_files:
        problems.append("- No markdown context memory files were found.")
    if not response_reports:
        problems.append("- No saved response reports were found.")
    if not environment_reports:
        problems.append("- No saved environment reports were found.")

    problems.extend(
        [
            "- Phase 1 needs periodic live DDGS smoke checks when network access is available.",
            "- The income research workflow is not yet implemented.",
            "- Browser automation and GitHub publishing remain postponed and approval-based.",
            "- Local model quality depends on installed Ollama models matching the local model config.",
            "- OpenRouter is optional and should remain disabled or skipped when keys, budget, or free-model validation are not safe.",
        ]
    )
    return problems


def file_is_empty(path: Path) -> bool:
    return (not path.exists()) or path.read_text(encoding="utf-8", errors="replace").strip() == ""


def is_safe_path(root: Path, path: Path) -> bool:
    try:
        relative_path = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False

    parts = set(relative_path.parts)
    filename = path.name.lower()
    if parts & BLOCKED_DIRS:
        return False
    if filename in BLOCKED_FILENAMES:
        return False
    if filename.endswith(".pem") or filename.endswith(".key"):
        return False
    return True


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Path must stay inside project root: {value}") from exc
    return resolved


def relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
