# AGENTS.md — AI_SYSTEM Repository Instructions

## Purpose

This repository is the user's long-term AI_SYSTEM project.

The goal is to build a local-first AI workflow system that helps the user create additional income without risking their current job.

The system should use:
- local AI models first;
- OpenRouter free API models only when useful;
- usage tracking and budgeting;
- real internet research with source URLs;
- persistent markdown memory;
- Codex in VS Code for implementation;
- ChatGPT Desktop for planning, review, and source-text updates;
- later optional browser automation and stronger AI tool integration.

## Required Startup Behavior

Before starting any task, read these files if they exist:

1. `.codex/state.md`
2. `.codex/plan.md`
3. `.codex/decisions.md`
4. `.codex/rules.md`
5. `.codex/safety.md`
6. `.codex/next-actions.md`
7. `docs/context/AI_SYSTEM_LONG_TERM_GOAL_AND_PROGRESS.md`
8. `docs/context/AI_SYSTEM_FILE_STRUCTURE.md`
9. `docs/context/AI_SYSTEM_CURRENT_WORKFLOW.md`

After reading them, summarize:
- current project state;
- current active phase;
- what task you are about to perform;
- which files you expect to modify;
- how you will verify the result.

Do not ask the user to repeat project context if it is already available in these files.

## Current Highest Priority

The current highest priority is to fix or build the real internet research gateway.

The research workflow must:
- return real source URLs;
- save title, URL, snippet, query, provider, and timestamp;
- clearly mark whether results are real or mock/fallback;
- never present mock data as real research;
- save markdown research reports;
- include tests.

## Working Rules

Prefer small, safe, reviewable changes.

Before coding:
- inspect existing files;
- understand current architecture;
- explain the plan;
- avoid large rewrites unless necessary.

When implementing:
- preserve existing working behavior;
- add tests when practical;
- keep interfaces simple;
- write clear errors and logs;
- update project memory files after meaningful progress.

After implementation:
- explain changed files;
- explain how to run/test;
- update `.codex/state.md`;
- update `.codex/next-actions.md`;
- add decisions to `.codex/decisions.md` if a new important decision was made.

## Safety Rules

Do not:
- expose API keys, tokens, cookies, passwords, or secrets;
- read browser cookies or authentication tokens;
- send messages, apply to jobs, push code, create public repos, or spend money without explicit user approval;
- silently use mock data when real research was requested;
- install unnecessary packages without explaining why.

Browser automation is a later phase and must be visible, approval-based, and isolated from secrets.

## Done Means

A task is done only when:
- code or docs are updated;
- the change is explained;
- tests or manual verification steps are provided;
- project state files are updated;
- next actions are clear.