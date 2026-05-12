# AI_SYSTEM Current Workflow

Last updated: 2026-05-12

## Normal CLI Workflow

Run the terminal app:

```bash
python main.py
```

Choose a task type, enter a prompt, and let the system save larger outputs as markdown reports instead of printing everything to the terminal.

Main task groups:
- local model tasks: `general`, `coding`, `fast`;
- OpenRouter guarded tasks: `api`, `review`;
- deterministic system tasks: `doctor`, `project_brief`, `memory_audit`, `model_status`, `system_review`, `tool_ideas`;
- utilities: `usage`, `discover`, `project_context_export`;
- research tasks: `research`, `research-context`.

## Research Workflow

Mock/offline deterministic research:

```bash
python main.py research "test topic" --provider mock
```

Real DDGS-backed research:

```bash
python main.py research "best local LLM coding workflow 2026" --real
```

Equivalent explicit provider form:

```bash
python main.py research "best local LLM coding workflow 2026" --provider ddgs
```

Research reports are saved to `workspace/research/`. They include provider, title, URL, snippet, query, timestamp, source count, limitations, and safety notes. Mock/offline reports are labeled as `mock-offline`; real reports are labeled as `ddgs`.

Convert a saved research report into compact reusable context:

```bash
python main.py research-context workspace/research/<generated-report>.md
```

Context packs are saved under `memory/context/research/`.

## Project Context Workflow

Refresh the generated ChatGPT Desktop project summary:

```bash
python main.py project_context_export
```

This calls the existing local exporter and does not call model APIs. It refreshes `docs/context/AI_SYSTEM_PROJECT_SUMMARY.generated.md` and does not overwrite the human-curated `docs/context/CHATGPT_PROJECT_CONTEXT.md`.

## Verification Workflow

Run the full unit test suite:

```bash
python -m unittest discover -s tests
```

Run research checks after changing research code or docs:

```bash
python main.py research "test topic" --provider mock
python main.py research "best local LLM coding workflow 2026" --real
```

If real search fails because network access is unavailable, keep the failure visible and do not substitute mock data as real research.
