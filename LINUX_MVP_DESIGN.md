# Linux Local-Agent MVP Design

## Goal

Turn the current working portal automation into a Linux/Ubuntu local agent that can be
configured once and run automatically every day, while preserving the existing portal
workflow.

The MVP is intentionally local and single-user. It does not include payments, a public
web dashboard, multi-user accounts, or cross-platform installers yet.

## MVP user experience

The customer runs a setup command once:

```text
accsoft-agent setup
```

The setup flow collects:

- Customer display name
- Accsoft username/student ID
- Accsoft password
- Daily run time
- Whether automatic upload is enabled

The customer can then use:

```text
accsoft-agent test       # safe validation; upload disabled
accsoft-agent run        # one immediate full run
accsoft-agent status     # configuration and last-run summary
accsoft-agent enable     # install/enable the daily schedule
accsoft-agent disable    # pause the daily schedule
```

The scheduled task runs without the customer opening a terminal. It starts the browser,
performs the existing workflow, records the result, and exits.

## Explicit safety behavior

The first implementation must default to safe mode. Setup and test must not upload an
answer unless the customer explicitly enables automatic upload.

Use two independent controls:

1. A configuration flag such as `AUTO_UPLOAD=false`.
2. A runtime `--allow-upload` confirmation required for the first manual production run.

The agent must print or record which mode is active before processing. Test mode may log
in and inspect assignments, but must not call the upload function.

## Process boundaries

### Agent core

Platform-independent Python code responsible for:

- Loading validated configuration
- Running the existing login/navigation workflow
- Downloading and reading assignment files
- Generating answers through the backend/AI integration
- Creating answer PDFs
- Uploading only when explicitly enabled
- Returning structured success/failure results

### Linux adapter

Ubuntu-specific code responsible for:

- Reading/writing the user's configuration location
- Accessing the Linux secret store
- Installing and removing the systemd user timer
- Reading recent local logs

The core must not directly contain systemd commands. Put Linux-specific behavior behind
an adapter so Windows Task Scheduler and macOS launchd can be added later.

## Ubuntu scheduling design

Use a systemd user service and timer rather than an always-running Python process or
cron. The timer should:

- Run under the customer's user account.
- Use the configured local time.
- Start the agent with an explicit `run --scheduled` mode.
- Restart or retry only according to a bounded policy.
- Write logs to the user's journal or an application log directory.

The agent must document that the computer needs to be powered on and online. Add a
later option for `Persistent=true` so a missed run can start after the machine returns,
subject to a duplicate-run guard.

## Configuration and secrets

Store non-secret settings under the XDG configuration directory, for example:

```text
~/.config/accsoft-agent/config.toml
```

Store the Accsoft password in the desktop secret store using the `keyring` library or
an equivalent Linux Secret Service integration. Do not write the password to TOML, JSON,
logs, command-line arguments, or Git.

Store runtime data separately:

```text
~/.local/state/accsoft-agent/
```

Possible state files include the last-run result, run lock, and a small sanitized error
summary. Assignment downloads and generated answers should remain in project-managed
directories initially, then move to per-user application storage during packaging.

## Duplicate-run protection

Before a scheduled run starts, acquire a local lock. If another agent process already
holds the lock, exit cleanly. Record a run ID and start time.

Before generating or uploading an answer, check whether the assignment is already
submitted. Never upload the same generated file twice because a timer or retry was
restarted.

## Logging and result states

Use structured, sanitized events with states such as:

```text
started → logged_in → assignments_found → processing_assignment
        → answer_created → upload_confirmed → completed
        ↘ failed
```

Logs may include assignment numbers and error categories, but must not include passwords,
API keys, cookies, or full portal HTML. `status` should show the last run, duration,
result, and a safe error message.

## Refactoring sequence

Do not rewrite the entire script. Refactor in this order:

1. Extract configuration/constants without changing selectors or portal behavior.
2. Extract the current `main()` workflow into a callable `run_once()` result.
3. Add a mode flag so test mode skips upload.
4. Add setup validation and local configuration storage.
5. Add Linux secret-store access.
6. Add the systemd timer adapter.
7. Add lock/state/log handling.
8. Verify the original manual full run against the known account.

Each step must remain runnable independently.

## Verification plan

Before real upload testing:

- Run static syntax/import checks.
- Run unit tests for configuration, question parsing, and mode selection.
- Run setup with a test account or placeholder credentials.
- Run `test` and confirm no upload locator is clicked.
- Verify `status` does not expose the password.
- Verify enable/disable creates and removes only the intended user timer.
- Run one controlled full workflow manually.
- Confirm the portal shows `Re-Upload` only after a real successful upload.

## Out of scope for this MVP

- Windows and macOS installers
- Mobile background execution
- Payments and subscriptions
- Public web dashboard
- Automatic self-updates
- Multi-device synchronization
- Server-side browser workers
- Handwritten PDF generation
