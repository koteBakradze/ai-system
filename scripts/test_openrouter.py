import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs) -> None:
        return None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.models.openrouter_client import OpenRouterClient


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    client = OpenRouterClient()

    print("\n=== OPENROUTER USAGE BEFORE ===\n")
    print(json.dumps(client.usage_manager.get_openrouter_status(), indent=2))

    if not os.getenv("OPENROUTER_API_KEY"):
        print("\nOpenRouter is disabled: OPENROUTER_API_KEY is not set.")
        return

    can_call, reason = client.can_call_free_model()
    if not can_call:
        print(
            "\nOpenRouter test skipped: free usage budget is close or reached. "
            f"Reason: {reason}."
        )
        return

    print("\nSending one tiny OpenRouter free-model test prompt...\n")
    response = client.run_model(
        "Reply with one sentence: OpenRouter free model is connected.",
        purpose="api",
    )

    print("=== RESPONSE ===\n")
    print(response)

    print("\n=== OPENROUTER USAGE AFTER ===\n")
    status = client.usage_manager.get_openrouter_status()
    status["remote_key_status"] = client.get_remote_key_status()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
