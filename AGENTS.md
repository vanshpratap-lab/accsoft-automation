# Accsoft Automation — Agent Instructions

## Project purpose

This repository contains the Accsoft student-portal automation prototype. The long-term
product is a cross-platform local desktop agent with one-time setup and scheduled,
automatic execution.

## Current development stage

We are beginning production development. The existing `main.py` workflow is the known
working baseline. Preserve its behavior until a replacement is tested.

## Required workflow

1. Read `PROJECT_CONTEXT.md`, `TASKS.md`, `DECISIONS.md`, and `plan.md` before making
   architectural changes.
2. Work on one small phase or task at a time.
3. Do not rewrite unrelated working code.
4. Before editing, inspect the relevant files and current Git status.
5. After editing, run the narrowest useful checks and report their results.
6. Update `TASKS.md` after each meaningful task.
7. Update `PROJECT_CONTEXT.md` when architecture, behavior, or setup changes.
8. Record important alternatives and decisions in `DECISIONS.md`.
9. Never commit secrets, `.env`, customer credentials, downloaded assignments, or
   generated answers.

## Safety rules

- Do not expose or print credentials, API keys, cookies, or portal session data.
- Do not change portal selectors or the current end-to-end flow without a focused test.
- Do not delete working code or use destructive Git commands without explicit approval.
- Keep customer-facing automation opt-in and clearly observable during development.
- Prefer reversible changes and Git checkpoints.

## Product direction

- Develop and test the Linux/Ubuntu MVP first.
- Keep business logic platform-independent.
- Isolate operating-system scheduling and packaging behind small adapters.
- Add Windows and macOS support after the Linux vertical slice works.
- Customers should receive a packaged application, not the source repository.

## Handoff format

At the end of a task, report:

- What changed
- What was verified
- Current limitations
- The exact next task
