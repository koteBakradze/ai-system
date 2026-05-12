# Local AI System

Terminal-first local AI orchestration with persistent markdown memory and Ollama
models as the default provider.

# Model Providers

## Local Ollama

Default provider. Used for most tasks.

Local roles are configured in `configs/models/local_models.json`:

- `general` uses the local orchestrator model
- `coding` uses the local coding model
- `fast` uses the local fast model

## OpenRouter Free Models

Optional fallback provider.
Only free models are allowed.
Usage is tracked locally.
Daily and per-minute limits are enforced locally before calls.
Remote key usage is checked through OpenRouter when an API key is available.

OpenRouter configuration lives in `configs/models/openrouter_models.json`.
Usage is stored in `configs/usage/openrouter_usage.json`.

The strict free-only guard allows only:

- `openrouter/free`
- model IDs ending in `:free`

Free model discovery uses OpenRouter's models endpoint and stores a local cache
of zero-price text chat models. Specific model routing can be configured per
purpose, while `openrouter/free` remains the fallback.

Set environment variables in `.env`:

```bash
OPENROUTER_API_KEY=
OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=local-ai-system
```

Do not commit `.env`.

## Usage

```bash
python main.py
```

AI task responses are saved as Markdown files under
`workspace/reports/responses/`. The terminal prints the saved file path instead
of the full response, which keeps large reports such as `system_review`
readable.

Then choose:

- `general` for local reasoning
- `coding` for local coding
- `fast` for a smaller local model
- `review` for an OpenRouter free review when available, otherwise local fallback
- `api` for a direct OpenRouter free-model request
- `doctor` for a local-first system health report
- `project_brief` to generate and save `memory/context/PROJECT_BRIEF.md`
- `memory_audit` to inspect markdown memory and propose fixes
- `model_status` to review local/API routing and OpenRouter budget status
- `system_review` for local self-review plus optional OpenRouter free multi-review
- `tool_ideas` to rank useful future AI_SYSTEM tools
- `research` to collect fresh source metadata into `workspace/research/`
- `research-context` to convert a saved research report into compact context
- `usage` to check OpenRouter usage
- `discover` to refresh the free-model discovery cache
- `project_context_export` to refresh generated ChatGPT project context
- `exit` to quit

Run a one-shot fresh research report:

```bash
python main.py research "best local LLM coding workflow 2026" --real
```

Real research uses the optional free DDGS provider:

```bash
pip install ddgs
python main.py research "best local LLM coding workflow 2026" --provider ddgs
```

Offline/mock research is available explicitly for deterministic tests:

```bash
python main.py research "test topic" --provider mock
```

The gateway saves titles, URLs, snippets, search queries, and provider metadata
without browser automation or autonomous actions. Explicit real research never
falls back to mock sources.

Convert a saved research report into compact reusable AI context:

```bash
python main.py research-context workspace/research/<generated-report>.md
```

Raw reports stay under `workspace/research/`. Compact context packs are saved
under `memory/context/research/` for later local-model prompts.

Test OpenRouter with one optional API call:

```bash
python scripts/test_openrouter.py
```

If the API key is missing, the script prints a safe disabled message.
If the API key exists and local free limits allow it, the script makes one tiny
OpenRouter request and updates local usage.

# Safe Local Tools

Agents can inspect the local project through a narrow tool registry in
`core/tools`. The tool layer blocks arbitrary shell execution, delete/move
operations, `.env` reads, secret-looking paths, and writes outside markdown
memory or environment reports.

Run a terminal-only environment scan:

```bash
python scripts/scan_environment.py
```

This refreshes `memory/context/SYSTEM_CONTEXT.md`,
`memory/context/INSTALLED_TOOLS.md`, `memory/context/PROJECT_CONTEXT.md`, and
writes timestamped reports under `workspace/reports/environment/`.

Create or refresh ChatGPT Desktop project-context material:

```bash
python main.py project_context_export
```

Equivalent direct script form:

```bash
python scripts/export_project_context.py
```

This creates `docs/context/CHATGPT_PROJECT_CONTEXT.md` only if it is missing,
then updates `docs/context/AI_SYSTEM_PROJECT_SUMMARY.generated.md` with a local
project summary. It does not call model APIs.
