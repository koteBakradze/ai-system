# Fresh Internet Research Gateway

## Goal

The Fresh Internet Research Gateway gives AI_SYSTEM a safe way to collect current
internet research for local models without giving those models uncontrolled
browser access, shell access, or autonomous action permissions.

The gateway is a source-collection layer, not an agent that acts on the web. It
collects search-result metadata, saves the raw source trail, and leaves final
judgment to a later review step.

## Safe Workflow

```text
user task
-> research questions
-> search provider
-> collected sources
-> summarized research note
-> optional model review
```

The first implementation keeps raw research separate from conclusions:

- Research questions are generated from the user's topic.
- A provider returns source titles, URLs, snippets, and provider metadata.
- The gateway deduplicates and stores source candidates.
- A markdown report is saved under `workspace/research/`.
- A compact context pack can be generated under `memory/context/research/`.
- Local models can later read the context pack instead of the full raw report.

## Commands

Install the optional real search provider:

```bash
pip install ddgs
```

Collect a real raw research report:

```bash
python main.py research "best local LLM coding workflow 2026" --provider ddgs
```

or:

```bash
python main.py research "best local LLM coding workflow 2026" --real
```

Run deterministic offline/mock research for tests:

```bash
python main.py research "test topic" --provider mock
```

Convert a saved report into compact reusable AI context:

```bash
python main.py research-context workspace/research/<report>.md
```

Raw reports stay in `workspace/research/`. Compact context packs are written to
`memory/context/research/` with a safe slug filename. The context builder reads
only the saved Markdown report, uses deterministic extraction from snippets and
metadata, and does not call the internet or paid APIs.

Quick verification:

```bash
python main.py research "OpenRouter free models 2026" --real
ls -la workspace/research
cat workspace/research/<generated-file>.md
```

## Version 1 Scope

Version 1 supports:

- A provider interface that can be swapped later.
- An offline mock provider for deterministic tests.
- Optional `ddgs` / DuckDuckGo-style search for real free web research.
- Structured research query, search result, and report models.
- Markdown report writing under `workspace/research/`.
- CLI commands: `python main.py research "topic here" --provider mock`,
  `python main.py research "topic here" --provider ddgs`, and
  `python main.py research "topic here" --real`.
- Compact context-pack writing under `memory/context/research/`.
- A CLI command: `python main.py research-context workspace/research/<report>.md`.

Real mode must include source URLs, titles, snippets, provider metadata,
timestamps, search queries, and source counts. If `ddgs` is not installed, the
gateway reports: `Real web search requires ddgs. Install with: pip install ddgs`.
If real search returns no results, it saves an empty report with metadata rather
than creating fake/mock sources.

Local models should read only saved reports or compact context packs. They
should not browse freely, automate a browser, or edit files based directly on
web content.

Version 1 does not support:

- Browser automation.
- Page crawling or downloading full articles.
- Autonomous form submission, account access, purchases, deletion, or code edits.
- Paid or API-key-only search providers by default.
- Treating internet snippets as verified facts.
- Vector indexing or long-term database storage.

## Safety Rules

- No destructive actions.
- No automatic code edits from internet content.
- No trusting one source.
- Always save source URLs, titles, snippets, search queries, and provider names.
- Separate raw research from final conclusions.
- Prefer primary sources and compare multiple independent sources before using a claim.
- Keep paid/key-based providers disabled by default.

## Future Provider Adapters

Potential future adapters include Tavily, SerpAPI, Brave Search, or other
key-based providers, but they should remain optional and disabled unless the user
explicitly configures them.
