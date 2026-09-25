# Architecture Decisions

## D-001 — Local-agent product model

Decision: Customers will perform setup once, then a local background agent will run the
automation on a schedule without daily website interaction.

Reason: This matches the desired hands-off workflow and avoids requiring customers to
open a dashboard for every assignment.

Consequence: The customer device must be powered on and online at the scheduled time.
Phones are setup/status devices, not the primary automation runtime.

## D-002 — Linux-first development

Decision: Build and validate the first vertical slice on Ubuntu/Linux.

Reason: Ubuntu is the current development environment and gives us a real target for
fast feedback. The core design must remain cross-platform.

Consequence: Scheduling and packaging will use OS-specific adapters. Windows and macOS
will be added only after the Linux workflow is reliable.

## D-003 — Source code is not distributed

Decision: Customers receive a packaged agent, not the Git repository or readable source.

Reason: The product is a service and the implementation, AI credentials, and portal
integration must remain controlled.

Consequence: The future agent needs packaging, licensing, update, and revocation design.

## D-004 — Preserve the current prototype initially

Decision: Treat the existing `main.py` workflow as a baseline and refactor incrementally.

Reason: It is already working for the current account, so a large rewrite would make it
hard to identify regressions.

Consequence: Each production change must have a focused verification step.
