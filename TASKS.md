# Development Tasks

## Current phase

Phase 1 — Linux MVP design

## Status

Completed:

- Reviewed the existing prototype and production plan.
- Chosen direction: cross-platform local agent with one-time setup and daily scheduling.
- Chosen development order: Ubuntu/Linux MVP, then Windows, then macOS.
- Added persistent agent instructions and project handoff documents.
- Defined the Linux MVP boundary, commands, safety modes, storage, scheduling, and
  verification plan in `LINUX_MVP_DESIGN.md`.

Completed:

- Extracted configuration/constants from `main.py` without changing default behavior.
- Added startup configuration validation and a clear missing-AI-key warning.
- Added `run`, `test`, and `status` command modes.
- Added a `setup` mode that stores Accsoft credentials in the operating-system keyring.
- Added daily schedule storage and Ubuntu user-level `systemd` enable/disable commands.
- Added private local run logs and `enable-test` for safe scheduled validation.

In progress:

- Investigate one subject's alternate `AssignmentView.aspx` page, which did not expose
  the normal assignment table during safe testing.

Next task:

- Investigate and handle the alternate assignment page without changing the normal
  subject workflow.

## Phase roadmap

### Phase 0 — Foundation

- [x] Add persistent agent instructions.
- [x] Add task tracking and decision logging.
- [x] Confirm the Linux-first development order.

### Phase 1 — Linux MVP design

- [x] Define the local-agent process and boundaries.
- [x] Define configuration and credential-storage requirements.
- [x] Define the daily scheduling approach for Ubuntu.
- [x] Define a safe test mode that cannot upload accidentally.

### Phase 2 — Linux local-agent MVP

- [x] Separate configuration/constants from the current portal workflow.
- [x] Add initial CLI modes for full run, safe test, and status.
- [x] Add keyring-backed credential setup.
- [x] Add explicit command modes: setup, test, run, and status.
- [x] Add Ubuntu scheduling and local logs.
- [x] Verify login, assignment detection, subject navigation, and safe inspection on the
  Ubuntu desktop.
- [ ] Preserve and verify the current login/download/read/solve/upload behavior.

### Phase 3 — Packaging and reliability

- [ ] Package the Linux agent.
- [ ] Add retries, idempotency, failure recovery, and safe cleanup.
- [ ] Add automated tests for non-portal components.

### Phase 4 — Cross-platform support

- [ ] Add Windows scheduling and packaging.
- [ ] Add macOS scheduling and packaging.
- [ ] Test equivalent behavior on all three operating systems.

### Phase 5 — Commercial controls

- [ ] Add device registration and license validation.
- [ ] Add update mechanism and revocation.
- [ ] Add privacy, support, billing, and operational monitoring.
