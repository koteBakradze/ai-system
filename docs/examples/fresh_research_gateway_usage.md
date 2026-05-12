# Fresh Research Gateway Usage

Generate a research report from the terminal:

```bash
python main.py research "best local LLM coding workflow 2026"
```

Another example:

```bash
python main.py research "OpenRouter free model limits and best practices"
```

Reports are saved as markdown files under:

```text
workspace/research/
```

When the optional `ddgs` package is available, the gateway uses it for free
DuckDuckGo-style search. Without that package, the command still creates a safe
offline report with no source candidates, which keeps tests and local workflows
API-key-free.

The report keeps raw source titles, URLs, snippets, provider names, and search
queries separate from final conclusions so local models can use the material as
fresh context later.
