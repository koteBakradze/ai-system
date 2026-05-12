# AI_SYSTEM ChatGPT Project Context

Last updated: 2026-05-12

## 1. Project Goal

AI_SYSTEM is a local-first AI workflow system for creating additional income without risking the user's current job.

The system should support research, planning, coding, review, and project-building workflows while keeping paid usage, browser automation, publishing, job outreach, account access, and other sensitive actions approval-based.

## 2. Current System Overview

- The CLI entry point is `main.py`.
- Local Ollama is the default model provider.
- OpenRouter is optional and restricted to free models with local usage tracking.
- Markdown memory lives under `memory/context/`.
- Reports are saved under `workspace/reports/` and `workspace/research/`.
- Safe local tools live under `core/tools/`.
- Real internet research is handled through `core/research/` with explicit mock and DDGS providers.
- ChatGPT Desktop should use this file plus `docs/context/AI_SYSTEM_PROJECT_SUMMARY.generated.md` as project context.

## 3. Current Folder Structure

- `.codex/` - Codex memory, plans, safety notes, prompts, and checklists.
- `agents/` - focused context builders for environment, planning, memory, research, and coding workflows.
- `api/` - early API skeleton.
- `configs/` - local model, OpenRouter, and usage configuration.
- `core/` - routing, model clients, prompts, research gateway, and safe tools.
- `docs/` - architecture, roadmap, research docs, examples, and ChatGPT context.
- `memory/` - persistent markdown memory and future index storage.
- `scripts/` - deterministic local scripts.
- `tests/` - unit tests.
- `workspace/` - generated reports, research outputs, projects, and tasks.

## 4. Already Accomplished

- Local Ollama task routing for `general`, `coding`, and `fast`.
- Optional OpenRouter free-only usage with budget checks.
- Multi-perspective review with local fallback.
- Markdown response reports.
- Safe file, shell, and memory writer tools.
- Environment scan and project context export scripts.
- Real research gateway with mock/offline and DDGS-backed real modes.
- Research report and research context-pack generation.
- Unit tests for safety, OpenRouter, system tools, response reports, research gateway behavior, context builder behavior, and project context export.

## 5. Important Existing Files

- `AGENTS.md` - repository operating rules.
- `README.md` - user-facing usage and setup.
- `main.py` - CLI entry point.
- `core/router/router.py` - task routing.
- `core/research/` - research gateway implementation.
- `core/tools/` - safe local tool layer.
- `configs/models/local_models.json` - Ollama role configuration.
- `configs/models/openrouter_models.json` - OpenRouter free-model configuration.
- `.codex/state.md` - current project state.
- `.codex/plan.md` - phase plan.
- `.codex/next-actions.md` - immediate next actions.
- `docs/FRESH_RESEARCH_GATEWAY.md` - research gateway source of truth.

## 6. Current Agents / Actions / Workflows

CLI task types:
- `general`, `coding`, `fast`
- `review`, `api`
- `doctor`, `project_brief`, `memory_audit`, `model_status`, `system_review`, `tool_ideas`
- `research`, `research-context`
- `usage`, `discover`, `project_context_export`

Key commands:

```bash
python main.py
python main.py research "topic" --provider mock
python main.py research "topic" --real
python main.py research-context workspace/research/<report>.md
python main.py project_context_export
python -m unittest discover -s tests
```

## 7. API / Model Usage

- Local models are preferred for routine reasoning, coding, and planning.
- OpenRouter is optional and must stay free-only.
- OpenRouter usage is tracked locally before calls.
- Remote OpenRouter key status checks are guarded and optional.
- `.env` must not be committed or exposed.

## 8. Safety Rules

Allowed without extra approval:
- reading repo files;
- editing code/docs/memory in the repo;
- running safe tests;
- creating markdown reports;
- using mock/offline research;
- using explicit real research gateway commands.

Requires explicit approval:
- pushing to GitHub;
- creating public repositories;
- spending money;
- sending messages or applying to jobs;
- installing unnecessary or risky packages;
- changing secrets or authentication;
- browser automation;
- private account access.

## 9. Current Problems / Missing Parts

- Phase 1 needs final closure verification and periodic live-search smoke checks.
- Income research workflow is not yet implemented.
- Browser automation is intentionally postponed.
- GitHub project builder is not yet implemented.
- OpenRouter quality depends on currently available free models.

## 10. Recommended Next Steps

1. Keep `.codex/` and `docs/context/` synced with the actual implementation.
2. Run unit tests after each code change.
3. Run mock and real research smoke checks.
4. Use saved research reports/context packs as the input to Phase 3 income research workflow.
5. Design the Phase 3 workflow before adding browser automation or publishing actions.

## 11. How ChatGPT Should Help in This Project

ChatGPT Desktop should help with planning, review, source-text updates, and high-level synthesis. It should not ask the user to repeat context already present in this repo. It should preserve local-first, free-first, safety-first constraints and should treat generated summaries as evidence while keeping this file human-curated.
