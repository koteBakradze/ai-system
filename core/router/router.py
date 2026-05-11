from agents.environment.environment_agent import EnvironmentAgent
from agents.memory.memory_agent import MemoryAgent
from agents.planning.planner_agent import PlannerAgent
from agents.research.research_agent import ResearchAgent
from core.models.model_manager import model_manager
from core.tools.file_tools import PROJECT_ROOT
from core.tools.tool_registry import tool_registry
from memory.load_memory import memory_loader


SYSTEM_TOOL_TASKS = {
    "doctor",
    "project_brief",
    "memory_audit",
    "model_status",
    "system_review",
    "tool_ideas",
}


class LocalOrchestrator:
    def __init__(
        self,
        environment_agent: EnvironmentAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        planner_agent: PlannerAgent | None = None,
        research_agent: ResearchAgent | None = None,
    ):
        self.environment_agent = environment_agent or EnvironmentAgent()
        self.memory_agent = memory_agent or MemoryAgent()
        self.planner_agent = planner_agent or PlannerAgent()
        self.research_agent = research_agent or ResearchAgent()

    def handle_task(self, task_type: str, prompt: str) -> str:
        task_type = (task_type or "general").strip().lower()
        prompt = prompt or ""

        memory_context = memory_loader.load_markdown_memories()

        full_prompt = f"""
            SYSTEM CONTEXT:
            {memory_context}

            USER REQUEST:
            {prompt}
            """

        if task_type == "coding":
            return model_manager.run_local_model("coding", full_prompt)

        if task_type == "fast":
            return model_manager.run_local_model("fast", full_prompt)

        if task_type == "api":
            return model_manager.run_openrouter_model(full_prompt, purpose="api")

        if task_type == "review":
            can_call, reason = model_manager.can_use_openrouter(planned_requests=3)
            if can_call:
                response = model_manager.run_openrouter_multi_review(full_prompt)
                if not self._is_openrouter_error(response):
                    return response
                reason = response

            local_response = model_manager.run_local_model("orchestrator", full_prompt)
            return (
                "OpenRouter review unavailable; using local orchestrator instead.\n"
                f"Reason: {reason}\n\n"
                f"{local_response}"
            )

        if task_type == "doctor":
            return self._handle_doctor(prompt)

        if task_type == "project_brief":
            return self._handle_project_brief(prompt)

        if task_type == "memory_audit":
            return self._handle_memory_audit(prompt)

        if task_type == "model_status":
            return self._handle_model_status(prompt)

        if task_type == "system_review":
            return self._handle_system_review(prompt)

        if task_type == "tool_ideas":
            return self._handle_tool_ideas(prompt)

        return model_manager.run_local_model("orchestrator", full_prompt)

    def get_usage_status(self) -> dict:
        return model_manager.get_openrouter_status()

    def discover_openrouter_models(self) -> dict:
        return model_manager.discover_openrouter_free_models()

    def _handle_doctor(self, prompt: str) -> str:
        context = self.environment_agent.build_doctor_context(
            local_models=model_manager.models,
            openrouter_status=model_manager.get_openrouter_status(),
            openrouter_config=model_manager.openrouter.config,
            available_tools=tool_registry.list_tools(),
        )
        assessment = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Act as the AI_SYSTEM doctor. Summarize health, name broken or "
                "risky checks, and give the next concrete repair steps."
            ),
        )
        return self._join_sections(context, "Local Doctor Assessment", assessment)

    def _handle_project_brief(self, prompt: str) -> str:
        context = self.research_agent.build_project_brief_context(prompt)
        brief = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Write a concise project brief suitable for persistent markdown "
                "memory. Include current purpose, architecture, local/API model "
                "split, safety rules, and near-term extension points."
            ),
        )
        if self._is_local_model_error(brief):
            brief = self.research_agent.deterministic_project_brief() + "\n\n" + brief

        path = self.research_agent.save_project_brief(brief)
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        return f"Saved project brief to `{relative}`.\n\n{brief}"

    def _handle_memory_audit(self, prompt: str) -> str:
        context = self.memory_agent.build_memory_audit_context(prompt)
        assessment = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Audit the markdown memory. Identify stale, duplicate, missing, "
                "or conflicting context. Propose fixes only; do not rewrite files."
            ),
        )
        return self._join_sections(context, "Local Memory Audit", assessment)

    def _handle_model_status(self, prompt: str) -> str:
        context = self.environment_agent.build_model_status_context(
            local_models=model_manager.models,
            openrouter_status=model_manager.get_openrouter_status(),
            openrouter_config=model_manager.openrouter.config,
        )
        assessment = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Summarize model readiness, routing recommendations, OpenRouter "
                "free-budget status, and any configuration issues."
            ),
        )
        return self._join_sections(context, "Local Model Routing Assessment", assessment)

    def _handle_system_review(self, prompt: str) -> str:
        context = self.planner_agent.build_system_review_context(prompt)
        local_review = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Run a structured self-review of AI_SYSTEM. Lead with actionable "
                "bugs, risks, missing tests, and maintainability concerns."
            ),
        )

        sections = [self._join_sections(context, "Local System Review", local_review)]
        can_call, reason = model_manager.can_use_openrouter(planned_requests=3)
        if can_call:
            response = model_manager.run_openrouter_multi_review(context)
            if not self._is_openrouter_error(response):
                sections.append("## OpenRouter Free Multi-Review\n\n" + response)
            else:
                sections.append(
                    "## OpenRouter Free Multi-Review\n\n"
                    "OpenRouter review unavailable; local review above is authoritative.\n"
                    f"Reason: {response}"
                )
        else:
            sections.append(
                "## OpenRouter Free Multi-Review\n\n"
                "Skipped; local review above is authoritative.\n"
                f"Reason: {reason}"
            )
        return "\n\n".join(sections)

    def _handle_tool_ideas(self, prompt: str) -> str:
        context = self.planner_agent.build_tool_ideas_context(prompt)
        assessment = self._local_assessment(
            context=context,
            prompt=prompt,
            instructions=(
                "Generate and rank useful future AI_SYSTEM tools. For each idea, "
                "score value, difficulty, local/API model fit, and safety risk. "
                "Prefer small local-first versions."
            ),
        )
        return self._join_sections(context, "Local Tool Ideas", assessment)

    def _local_assessment(self, context: str, prompt: str, instructions: str) -> str:
        full_prompt = f"""
            SYSTEM TOOL CONTEXT:
            {context}

            USER FOCUS:
            {prompt or "No extra focus provided."}

            INSTRUCTIONS:
            {instructions}
            """
        return model_manager.run_local_model("orchestrator", full_prompt)

    def _join_sections(self, context: str, title: str, assessment: str) -> str:
        return f"{context}\n\n## {title}\n\n{assessment}"

    def _is_openrouter_error(self, response: str) -> bool:
        error_prefixes = (
            "OpenRouter is disabled",
            "OpenRouter call skipped",
            "OpenRouter multi-model review skipped",
            "OpenRouter multi-model review unavailable",
            "OpenRouter authentication failed",
            "OpenRouter rejected",
            "OpenRouter rate limit reached",
            "OpenRouter server error",
            "OpenRouter request failed",
            "OpenRouter request timed out",
            "OpenRouter returned",
            "OpenRouter model blocked",
        )
        return response.startswith(error_prefixes)

    def _is_local_model_error(self, response: str) -> bool:
        return response.startswith(
            ("Local Ollama model failed safely", "Unknown local model role")
        )

orchestrator = LocalOrchestrator()
