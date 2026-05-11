import json
from pathlib import Path

from ollama import chat

from core.models.openrouter_client import OpenRouterClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODELS_PATH = PROJECT_ROOT / "configs" / "models" / "local_models.json"


class ModelManager:
    def __init__(self):
        with open(LOCAL_MODELS_PATH, "r", encoding="utf-8") as f:
            self.models = json.load(f)
        self.openrouter = OpenRouterClient()

    def run_local_model(self, role: str, prompt: str) -> str:
        model_name = self.models.get(role)
        if not model_name:
            return f"Unknown local model role: {role}"

        try:
            response = chat(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as exc:
            return f"Local Ollama model failed safely: {exc}"

        return response["message"]["content"]

    def run_openrouter_model(
        self,
        prompt: str,
        model_name: str | None = None,
        purpose: str = "api",
        system_prompt: str | None = None,
    ) -> str:
        return self.openrouter.run_model(
            prompt=prompt,
            model_name=model_name,
            purpose=purpose,
            system_prompt=system_prompt,
        )

    def run_openrouter_multi_review(self, prompt: str) -> str:
        result = self.openrouter.run_multi_model_review(prompt)
        if result["ok"]:
            return result["content"]
        return result["error"]

    def run_model(self, provider: str = "local", role: str = "orchestrator", prompt: str = "") -> str:
        if provider == "openrouter":
            return self.run_openrouter_model(prompt, purpose=role)

        if provider == "local":
            return self.run_local_model(role, prompt)

        return f"Unknown model provider: {provider}"

    def can_use_openrouter(self, planned_requests: int = 1) -> tuple[bool, str]:
        return self.openrouter.can_call_free_model(planned_requests=planned_requests)

    def discover_openrouter_free_models(self) -> dict:
        return self.openrouter.discover_free_models(persist=True)

    def get_openrouter_status(self, include_remote: bool = True) -> dict:
        remote_status = None
        if include_remote:
            remote_status = self.openrouter.get_remote_key_status()
        status = self.openrouter.usage_manager.get_openrouter_status()
        if include_remote:
            status["remote_key_status"] = remote_status
        return status


model_manager = ModelManager()
