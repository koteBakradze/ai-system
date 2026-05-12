# AI_SYSTEM Safety Rules

## Allowed Without Extra Approval

Codex may:
- read repository files;
- create or edit markdown files;
- create proposed code changes;
- run safe tests;
- inspect project structure;
- update `.codex/` project memory files;
- create reports.

## Requires Explicit User Approval

Codex must ask before:
- pushing to GitHub;
- creating public repositories;
- sending messages;
- applying to jobs;
- spending money;
- installing large or risky dependencies;
- changing secrets/authentication;
- using browser automation;
- accessing private accounts.

## Secrets

Never print, copy, store, summarize, or expose:
- API keys;
- passwords;
- browser cookies;
- auth tokens;
- session storage;
- private credentials.

## Research Integrity

Never present mock/fallback data as real internet research.

If real search fails, clearly say:
“Real search failed. This output used fallback/mock data.”