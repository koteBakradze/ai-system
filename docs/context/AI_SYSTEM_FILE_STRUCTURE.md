# AI_SYSTEM File Structure

Last updated: 2026-05-12

## Top-Level Areas

- `main.py` - terminal entry point for model tasks, utility tasks, research, research-context creation, and project-context export.
- `agents/` - task-specific context builders for coding, environment, memory, planning, and research.
- `api/` - early API package skeleton.
- `configs/` - model routing and OpenRouter usage configuration.
- `core/` - model clients, routing, prompts, research gateway, and safe tools.
- `docs/` - architecture, roadmap, research gateway docs, examples, and ChatGPT context files.
- `memory/` - persistent markdown memory and future index/vector storage areas.
- `scripts/` - deterministic local scripts for context export, environment scans, and OpenRouter smoke testing.
- `tests/` - unit tests for safety, routing, reports, OpenRouter, and research workflows.
- `workspace/` - generated reports, research outputs, projects, and task artifacts.

## Important Files

- `AGENTS.md` - repo rules and required startup context.
- `.codex/state.md` - current project state.
- `.codex/plan.md` - phase plan and priorities.
- `.codex/next-actions.md` - immediate next steps.
- `.codex/decisions.md` - important project decisions.
- `.codex/safety.md` - explicit safety boundaries.
- `README.md` - user-facing usage guide.
- `docs/context/CHATGPT_PROJECT_CONTEXT.md` - human-curated ChatGPT Desktop project context.
- `docs/context/AI_SYSTEM_PROJECT_SUMMARY.generated.md` - generated local project summary.
- `docs/FRESH_RESEARCH_GATEWAY.md` - source-of-truth research gateway behavior.

## Research Gateway Files

- `core/research/models.py` - structured research query, result, and report models.
- `core/research/providers.py` - mock/offline and DDGS search providers.
- `core/research/gateway.py` - result collection, validation, dedupe, summaries, and limitations.
- `core/research/writer.py` - markdown research report rendering and saving.
- `core/research/context_builder.py` - compact reusable context-pack extraction.
- `tests/test_fresh_research_gateway.py` - gateway/provider/report tests.
- `tests/test_research_context_builder.py` - context-pack tests.

## Generated Output Locations

- `workspace/reports/responses/` - saved AI task responses.
- `workspace/reports/environment/` - environment and project snapshots.
- `workspace/research/` - raw research reports with source metadata.
- `memory/context/research/` - compact research context packs for later prompts.
