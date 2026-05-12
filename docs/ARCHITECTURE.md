# AI_SYSTEM Architecture

Last updated: 2026-05-12

## Overview

AI_SYSTEM is a terminal-first, local-first AI workflow system. The CLI routes user tasks to local Ollama models, optional guarded OpenRouter free models, deterministic local system tools, or the research gateway.

## Main Flow

```text
user command
-> main.py
-> task parser
-> local router / research gateway / utility script
-> markdown output
-> memory or workspace report
```

## Core Subsystems

- CLI: `main.py` handles interactive and one-shot commands.
- Router: `core/router/router.py` dispatches model and system-tool tasks.
- Models: `core/models/` wraps Ollama and OpenRouter behavior.
- Tools: `core/tools/` exposes narrow, safe project-inspection and markdown-writing capabilities.
- Research: `core/research/` collects source metadata, writes reports, and builds compact context packs.
- Memory: `memory/context/` stores persistent markdown context loaded into later prompts.
- Scripts: `scripts/` provides deterministic local maintenance workflows.

## Research Gateway

The research gateway is a source-collection layer, not a browsing agent. It supports:
- mock/offline provider for deterministic tests;
- DDGS provider for explicit real web research;
- validation and dedupe of title/URL/snippet metadata;
- markdown report output under `workspace/research/`;
- compact context-pack output under `memory/context/research/`.

The gateway does not automate browsers, sign in to accounts, submit forms, spend money, or treat snippets as verified conclusions.

## Safety Boundaries

- Local models are preferred by default.
- OpenRouter usage must remain free-only and guarded.
- Secrets such as `.env`, API keys, cookies, and tokens must not be read or exposed.
- Browser automation, job outreach, public repo creation, pushes, purchases, and account actions require explicit user approval.
- Mock/fallback research must remain clearly labeled.
