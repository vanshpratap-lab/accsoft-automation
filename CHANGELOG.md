# Changelog

## Unreleased

- Added `AGENTS.md` with development and safety instructions.
- Added `TASKS.md` for phase and handoff tracking.
- Added `DECISIONS.md` for architecture decisions.
- Established Ubuntu/Linux-first development with cross-platform design.
- Added `LINUX_MVP_DESIGN.md` defining the first local-agent vertical slice.
- Centralized runtime settings and timeouts in `main.py`; existing default behavior is
  preserved and credentials now accept environment overrides.
- Added startup configuration validation without changing the portal workflow.
- Added `run`, `test`, and `status` CLI modes; `test` does not download, generate, or
  upload assignment answers.
- Added `setup` mode and the `keyring` dependency for OS-level credential storage.
- Added daily schedule storage and Ubuntu user-level `systemd` timer enable/disable
  commands; the timer is not enabled automatically.
- Existing automation code was not changed in Phase 0.
