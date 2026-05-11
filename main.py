import json

from core.router.router import SYSTEM_TOOL_TASKS, orchestrator


MODEL_TASKS = {"coding", "fast", "general", "review", "api"}
UTILITY_TASKS = {"usage", "discover"}
ALL_TASKS = MODEL_TASKS | SYSTEM_TOOL_TASKS | UTILITY_TASKS | {"exit"}


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

        print("\n=== RESPONSE ===\n")
        print(response)


if __name__ == "__main__":
    main()
