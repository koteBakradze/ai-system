# Fresh Research Gateway Usage

The research gateway has two explicit modes:

- mock/offline mode for deterministic local checks;
- real DDGS-backed mode for current internet source metadata.

## Mock/Offline Research

Use mock/offline mode when testing or when no network should be used:

```bash
python main.py research "test topic" --provider mock
```

Mock reports are labeled with provider `mock-offline`. They must never be presented as real internet research.

## Real Research

Use `--real` for DDGS-backed source collection:

```bash
python main.py research "best local LLM coding workflow 2026" --real
```

Equivalent explicit provider form:

```bash
python main.py research "best local LLM coding workflow 2026" --provider ddgs
```

If the optional provider is missing, install it:

```bash
pip install ddgs
```

Explicit real research does not silently fall back to mock sources. If real search fails or returns no results, the saved report should show the actual provider and limitations.

## Outputs

Reports are saved under:

```text
workspace/research/
```

Each report keeps raw source titles, URLs, snippets, provider names, search queries, timestamps, source counts, limitations, and safety notes separate from final conclusions.

Convert a saved report into compact reusable context:

```bash
python main.py research-context workspace/research/<generated-report>.md
```

Context packs are saved under:

```text
memory/context/research/
```
