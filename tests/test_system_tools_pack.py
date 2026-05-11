import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.router import router


class FakeModelManager:
    def __init__(self, can_call: bool = False, api_response: str = "API_OK"):
        self.models = {"orchestrator": "local-orchestrator"}
        self.openrouter = SimpleNamespace(config={"enabled": True})
        self.can_call = can_call
        self.api_response = api_response
        self.local_calls = []
        self.api_calls = []

    def run_local_model(self, role: str, prompt: str) -> str:
        self.local_calls.append((role, prompt))
        return "LOCAL_OK"

    def run_openrouter_multi_review(self, prompt: str) -> str:
        self.api_calls.append(prompt)
        return self.api_response

    def run_openrouter_model(self, prompt: str, purpose: str = "api") -> str:
        return "API_DIRECT_OK"

    def can_use_openrouter(self, planned_requests: int = 1) -> tuple[bool, str]:
        return self.can_call, "budget test reason"

    def get_openrouter_status(self) -> dict:
        return {"enabled": True, "can_call": self.can_call}


class FakeEnvironmentAgent:
    def build_doctor_context(self, **kwargs) -> str:
        return "DOCTOR_CONTEXT"

    def build_model_status_context(self, **kwargs) -> str:
        return "MODEL_STATUS_CONTEXT"


class FakeMemoryAgent:
    def build_memory_audit_context(self, user_prompt: str = "") -> str:
        return f"MEMORY_AUDIT_CONTEXT {user_prompt}".strip()


class FakePlannerAgent:
    def build_system_review_context(self, user_prompt: str = "") -> str:
        return f"SYSTEM_REVIEW_CONTEXT {user_prompt}".strip()

    def build_tool_ideas_context(self, user_prompt: str = "") -> str:
        return f"TOOL_IDEAS_CONTEXT {user_prompt}".strip()


class FakeResearchAgent:
    def __init__(self):
        self.saved_body = None

    def build_project_brief_context(self, user_prompt: str = "") -> str:
        return f"PROJECT_BRIEF_CONTEXT {user_prompt}".strip()

    def save_project_brief(self, body: str) -> Path:
        self.saved_body = body
        return router.PROJECT_ROOT / "memory" / "context" / "PROJECT_BRIEF.md"

    def deterministic_project_brief(self) -> str:
        return "DETERMINISTIC_BRIEF"


def make_orchestrator() -> router.LocalOrchestrator:
    return router.LocalOrchestrator(
        environment_agent=FakeEnvironmentAgent(),
        memory_agent=FakeMemoryAgent(),
        planner_agent=FakePlannerAgent(),
        research_agent=FakeResearchAgent(),
    )


class SystemToolsPackTests(unittest.TestCase):
    def test_cli_system_tool_names_are_registered(self):
        self.assertEqual(
            router.SYSTEM_TOOL_TASKS,
            {
                "doctor",
                "project_brief",
                "memory_audit",
                "model_status",
                "system_review",
                "tool_ideas",
            },
        )

    def test_doctor_uses_local_model_and_includes_context(self):
        fake_model_manager = FakeModelManager()
        orchestrator = make_orchestrator()

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("doctor", "focus")

        self.assertIn("DOCTOR_CONTEXT", result)
        self.assertIn("LOCAL_OK", result)
        self.assertEqual(fake_model_manager.local_calls[0][0], "orchestrator")

    def test_project_brief_saves_local_model_output(self):
        fake_model_manager = FakeModelManager()
        research_agent = FakeResearchAgent()
        orchestrator = router.LocalOrchestrator(
            environment_agent=FakeEnvironmentAgent(),
            memory_agent=FakeMemoryAgent(),
            planner_agent=FakePlannerAgent(),
            research_agent=research_agent,
        )

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("project_brief", "")

        self.assertIn("Saved project brief", result)
        self.assertEqual(research_agent.saved_body, "LOCAL_OK")

    def test_project_brief_has_deterministic_fallback_on_local_failure(self):
        fake_model_manager = FakeModelManager()
        fake_model_manager.run_local_model = lambda role, prompt: (
            "Local Ollama model failed safely: unavailable"
        )
        research_agent = FakeResearchAgent()
        orchestrator = router.LocalOrchestrator(
            environment_agent=FakeEnvironmentAgent(),
            memory_agent=FakeMemoryAgent(),
            planner_agent=FakePlannerAgent(),
            research_agent=research_agent,
        )

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("project_brief", "")

        self.assertIn("DETERMINISTIC_BRIEF", result)
        self.assertIn("Local Ollama model failed safely", research_agent.saved_body)

    def test_system_review_skips_openrouter_when_budget_unavailable(self):
        fake_model_manager = FakeModelManager(can_call=False)
        orchestrator = make_orchestrator()

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("system_review", "safety")

        self.assertIn("SYSTEM_REVIEW_CONTEXT safety", result)
        self.assertIn("Skipped", result)
        self.assertEqual(fake_model_manager.api_calls, [])

    def test_system_review_appends_openrouter_when_budget_allows(self):
        fake_model_manager = FakeModelManager(can_call=True, api_response="API_REVIEW")
        orchestrator = make_orchestrator()

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("system_review", "")

        self.assertIn("LOCAL_OK", result)
        self.assertIn("API_REVIEW", result)
        self.assertEqual(len(fake_model_manager.api_calls), 1)

    def test_system_review_handles_openrouter_error(self):
        fake_model_manager = FakeModelManager(
            can_call=True,
            api_response="OpenRouter request failed safely: test",
        )
        orchestrator = make_orchestrator()

        with patch.object(router, "model_manager", fake_model_manager):
            result = orchestrator.handle_task("system_review", "")

        self.assertIn("OpenRouter review unavailable", result)
        self.assertIn("Local System Review", result)

    def test_memory_audit_and_tool_ideas_are_local_first(self):
        fake_model_manager = FakeModelManager()
        orchestrator = make_orchestrator()

        with patch.object(router, "model_manager", fake_model_manager):
            memory_result = orchestrator.handle_task("memory_audit", "stale")
            ideas_result = orchestrator.handle_task("tool_ideas", "small")

        self.assertIn("MEMORY_AUDIT_CONTEXT stale", memory_result)
        self.assertIn("TOOL_IDEAS_CONTEXT small", ideas_result)
        self.assertEqual(len(fake_model_manager.local_calls), 2)


if __name__ == "__main__":
    unittest.main()
