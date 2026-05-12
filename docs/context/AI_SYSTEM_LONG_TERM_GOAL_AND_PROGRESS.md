# AI_SYSTEM Long-Term Goal and Progress

Last updated: 2026-05-12

## Long-Term Goal

AI_SYSTEM is a local-first AI workflow system for creating additional income without risking the user's current job.

The system should help with research, planning, coding, review, and project generation while keeping sensitive actions manual and approval-based.

## Principles

- Prefer local Ollama models for normal work.
- Use OpenRouter only through strict free-model routes and local budget checks.
- Save useful outputs as markdown memory and reports.
- Use real internet research only through explicit, source-preserving gateways.
- Never present mock or fallback data as real research.
- Do not automate browser/account/job/publishing actions until a later approved phase.

## Current Progress

- Local CLI orchestration exists in `main.py`.
- Local model roles are configured in `configs/models/local_models.json`.
- OpenRouter free-only support exists with usage tracking in `configs/usage/openrouter_usage.json`.
- Model responses are saved under `workspace/reports/responses/`.
- Safe project inspection and markdown writing tools exist under `core/tools/`.
- Environment and project context export scripts exist under `scripts/`.
- Phase 1 real research gateway is implemented under `core/research/`.
- Research reports are saved under `workspace/research/`.
- Compact research context packs are saved under `memory/context/research/`.
- Tests cover safety, OpenRouter guardrails, system tools, response reports, research gateway behavior, research context extraction, and project context export.

## Active Phase

Phase 1 is in closure:
- code exists;
- tests exist;
- docs and project memory are being reconciled;
- live real-search smoke checks should be run when network access is available.

## Next Major Phase

Phase 3 - Income Research Workflow.

The next product capability should use saved research reports/context packs to discover realistic additional-income ideas, score them by time/risk/difficulty/income potential, and produce manual weekly reports.
