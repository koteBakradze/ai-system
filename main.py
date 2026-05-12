import json
import re
from datetime import datetime
from pathlib import Path

from core.router.router import SYSTEM_TOOL_TASKS, orchestrator


MODEL_TASKS = {"coding", "fast", "general", "review", "api"}
UTILITY_TASKS = {"usage", "discover"}
ALL_TASKS = MODEL_TASKS | SYSTEM_TOOL_TASKS | UTILITY_TASKS | {"exit"}
PROJECT_ROOT = Path(__file__).resolve().parent
RESPONSE_REPORT_DIR = PROJECT_ROOT / "workspace" / "reports" / "responses"


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


def main():

    print("\n=== LOCAL AI SYSTEM ===\n")

    while True:

        task_type = input(
            "\nTask Type "
            "(coding/fast/general/review/api/doctor/project_brief/"
            "memory_audit/model_status/system_review/tool_ideas/"
            "usage/discover/exit): "
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

        if task_type not in ALL_TASKS:
            print(
                "Unknown task type. Choose coding, fast, general, review, "
                "api, doctor, project_brief, memory_audit, model_status, "
                "system_review, tool_ideas, usage, discover, or exit."
            )
            continue

        prompt_label = "Prompt"
        if task_type in SYSTEM_TOOL_TASKS:
            prompt_label = "Prompt (optional focus)"

        prompt = input(f"\n{prompt_label}: ")

        print("\nRunning...\n")

        response = orchestrator.handle_task(
            task_type=task_type,
            prompt=prompt
        )

        report_path = save_response_report(task_type, prompt, response)
        relative_path = report_path.relative_to(PROJECT_ROOT).as_posix()
        print("\n=== RESPONSE SAVED ===\n")
        print(f"Saved full Markdown response to `{relative_path}`.")


if __name__ == "__main__":
    main()
