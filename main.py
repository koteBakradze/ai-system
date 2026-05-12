import json
import re
import sys
from datetime import datetime
from pathlib import Path

from core.research.context_builder import build_context_pack, save_context_pack
from core.research.gateway import create_research_report
from core.research.writer import save_research_report
from core.router.router import SYSTEM_TOOL_TASKS, orchestrator
from scripts import export_project_context


MODEL_TASKS = {"coding", "fast", "general", "review", "api"}
UTILITY_TASKS = {"usage", "discover", "project_context_export"}
RESEARCH_TASKS = {"research", "research-context"}
ALL_TASKS = MODEL_TASKS | SYSTEM_TOOL_TASKS | UTILITY_TASKS | RESEARCH_TASKS | {"exit"}
PROJECT_ROOT = Path(__file__).resolve().parent
RESPONSE_REPORT_DIR = PROJECT_ROOT / "workspace" / "reports" / "responses"
RESEARCH_CONTEXT_DIR = PROJECT_ROOT / "memory" / "context" / "research"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "response"


def save_response_report(task_type: str, prompt: str, response: str) -> Path:
    RESPONSE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now()
    timestamp = generated_at.strftime("%Y%m%d-%H%M%S-%f")
    slug = _slugify(task_type)
    path = RESPONSE_REPORT_DIR / f"{timestamp}-{slug}.md"

    prompt_text = prompt.strip() or "No prompt provided."
    content = (
        f"# AI Response: {task_type}\n\n"
        f"- Generated: {generated_at.isoformat(timespec='seconds')}\n"
        f"- Task type: `{task_type}`\n\n"
        "## Prompt\n\n"
        f"{prompt_text}\n\n"
        "## Response\n\n"
        f"{response.rstrip()}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def run_research(topic: str, provider_name: str = "mock") -> Path:
    report = create_research_report(topic, provider_name=provider_name)
    report_path = save_research_report(report)
    relative_path = report_path.relative_to(PROJECT_ROOT).as_posix()

    print("\n=== RESEARCH REPORT SAVED ===\n")
    print(report.summary)
    if report.limitations:
        print("\nLimitations:")
        for limitation in report.limitations:
            print(f"- {limitation}")
    print(f"\nSaved Markdown research report to `{relative_path}`.")
    return report_path


def _parse_research_args(args: list[str]) -> tuple[str, str]:
    provider_name = "mock"
    explicit_provider = False
    real_requested = False
    topic_parts: list[str] = []
    index = 0

    while index < len(args):
        arg = args[index]
        if arg == "--real":
            real_requested = True
            index += 1
            continue
        if arg == "--provider":
            if index + 1 >= len(args):
                raise ValueError("--provider requires a value: mock or ddgs")
            provider_name = args[index + 1].strip().lower()
            explicit_provider = True
            index += 2
            continue
        if arg.startswith("--provider="):
            provider_name = arg.split("=", 1)[1].strip().lower()
            explicit_provider = True
            index += 1
            continue
        if arg.startswith("-"):
            raise ValueError(f"Unknown research option: {arg}")
        topic_parts.append(arg)
        index += 1

    if real_requested:
        if explicit_provider and provider_name not in {"ddgs", "duckduckgo", "real"}:
            raise ValueError("--real requires the ddgs provider; do not combine it with mock.")
        provider_name = "ddgs"

    topic = " ".join(topic_parts).strip()
    if not topic:
        raise ValueError('Usage: python main.py research "topic here" [--provider mock|ddgs] [--real]')
    return topic, provider_name


def run_research_context(report_path_text: str) -> Path:
    report_path = Path(report_path_text).expanduser()
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path

    if report_path.suffix.lower() != ".md":
        raise ValueError("Research context input must be a Markdown `.md` report.")
    if not report_path.exists() or not report_path.is_file():
        raise FileNotFoundError(f"Research report not found: {report_path_text}")

    pack = build_context_pack(report_path)
    context_path = save_context_pack(pack, RESEARCH_CONTEXT_DIR)
    relative_path = context_path.relative_to(PROJECT_ROOT).as_posix()

    print("\n=== RESEARCH CONTEXT SAVED ===\n")
    print(pack.summary)
    print(f"\nSaved compact research context to `{relative_path}`.")
    return context_path


def run_project_context_export() -> int:
    return export_project_context.main(["--skip-manual-template"])


def run_one_shot(argv: list[str]) -> int:
    command = argv[0].strip().lower() if argv else ""
    if command == "project_context_export":
        if len(argv) > 1:
            print("Usage: python main.py project_context_export")
            return 2
        return run_project_context_export()

    if command == "research":
        try:
            topic, provider_name = _parse_research_args(argv[1:])
        except ValueError as exc:
            print(exc)
            return 2
        try:
            run_research(topic, provider_name=provider_name)
        except (RuntimeError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        return 0

    if command == "research-context":
        report_path = " ".join(argv[1:]).strip()
        if not report_path:
            print("Usage: python main.py research-context workspace/research/<report>.md")
            return 2
        try:
            run_research_context(report_path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            return 2
        return 0

    print(
        'Usage: python main.py research "topic here" [--provider mock|ddgs] [--real]\n'
        "   or: python main.py research-context workspace/research/<report>.md\n"
        "   or: python main.py project_context_export"
    )
    return 2


def main(argv: list[str] | None = None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        return run_one_shot(argv)

    print("\n=== LOCAL AI SYSTEM ===\n")

    while True:

        task_type = input(
            "\nTask Type "
            "(coding/fast/general/review/api/doctor/project_brief/"
            "memory_audit/model_status/system_review/tool_ideas/"
            "research/research-context/project_context_export/usage/discover/exit): "
        ).strip().lower()

        if task_type == "exit":
            break

        if task_type == "usage":
            print("\n=== OPENROUTER USAGE ===\n")
            print(json.dumps(orchestrator.get_usage_status(), indent=2))
            continue

        if task_type == "discover":
            print("\n=== OPENROUTER FREE MODEL DISCOVERY ===\n")
            print(json.dumps(orchestrator.discover_openrouter_models(), indent=2))
            continue

        if task_type == "project_context_export":
            print("\n=== PROJECT CONTEXT EXPORT ===\n")
            run_project_context_export()
            continue

        if task_type not in ALL_TASKS:
            print(
                "Unknown task type. Choose coding, fast, general, review, "
                "api, doctor, project_brief, memory_audit, model_status, "
                "system_review, tool_ideas, research, research-context, "
                "project_context_export, usage, discover, or exit."
            )
            continue

        prompt_label = "Prompt"
        if task_type in SYSTEM_TOOL_TASKS:
            prompt_label = "Prompt (optional focus)"
        if task_type == "research":
            prompt_label = "Research topic"
        if task_type == "research-context":
            prompt_label = "Research report path"

        prompt = input(f"\n{prompt_label}: ")

        print("\nRunning...\n")

        if task_type == "research":
            run_research(prompt)
            continue

        if task_type == "research-context":
            try:
                run_research_context(prompt)
            except (FileNotFoundError, ValueError) as exc:
                print(f"Error: {exc}")
            continue

        response = orchestrator.handle_task(
            task_type=task_type,
            prompt=prompt
        )

        report_path = save_response_report(task_type, prompt, response)
        relative_path = report_path.relative_to(PROJECT_ROOT).as_posix()
        print("\n=== RESPONSE SAVED ===\n")
        print(f"Saved full Markdown response to `{relative_path}`.")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
