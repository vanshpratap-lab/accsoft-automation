# Accsoft Automation — Production and Selling Plan

## 1. Recommended business model

Your preferred experience is a one-time setup followed by automatic daily execution.
Use a private desktop agent rather than requiring the customer to return to your website
for every assignment. Do not distribute the Python source code or ask customers to
clone the Git repository.

The recommended model is a hybrid:

```text
Customer laptop
        |
        | One-time setup and schedule
        v
Installed background agent
        |
        | Daily scheduled run
        v
Local browser automation worker
        |
        v
Accsoft portal + AI provider
```

The customer installs a packaged application once, enters their name, student ID,
password, and preferred time, and then the agent runs automatically every day.

The agent can contact your backend for license validation, updates, and error reporting,
but the customer does not need to open your website or press a button for each run.

The laptop must be powered on and connected to the internet at the scheduled time. The
agent can retry later if the laptop was asleep or offline. For phones, use the phone for
one-time setup and status viewing only; Android and iOS do not reliably allow this type
of long-running background browser automation.

## 2. How customers would use it

1. Customer opens your website or installer once.
2. Customer creates an account and chooses a plan.
3. Customer enters their name, Accsoft student ID, and password.
4. Customer chooses a daily time, such as 5 PM, 6 PM, or 7 PM.
5. The installer registers a background task/service on the laptop.
6. At the scheduled time, the agent logs in, downloads, solves, uploads, and exits.
7. The agent reports success or failure to your backend and can show a notification.

The customer receives the service, not the implementation.

## 3. Supported devices and operating systems

### Laptops and desktops

Build installers for:

- Windows
- macOS
- Linux

The installer should include or install the required browser/runtime dependencies so
customers do not manually install Python, Playwright, Tesseract, Poppler, or Node.js.

### Phones and tablets

Use a responsive setup/status website or Progressive Web App later. Customers can set up
the agent and view results from Android or iOS, but the actual scheduled automation runs
on their laptop or desktop.

## 4. Local background agent

The packaged agent should:

- Ask for setup details only once.
- Store credentials in Windows Credential Manager, macOS Keychain, or Linux Secret
  Service, never in plain text.
- Register the daily schedule with the operating system.
- Start the browser, run the workflow, and close it after completion.
- Retry temporary network or portal failures.
- Prevent duplicate processing if a run is repeated.
- Send minimal status and error information to your backend.
- Support changing the schedule, pausing, and updating credentials.

Use Windows Task Scheduler, macOS `launchd`, or Linux `systemd`/cron for automatic
execution. The customer should not need to interact with the application daily.

## 5. Suggested production architecture

### Frontend

Build a small web dashboard using a framework such as Next.js, React, or another stack
you are comfortable maintaining. It should provide:

- Registration and login
- Subscription and payment status
- Accsoft credential setup
- One-time agent download and device registration
- Job status and error messages
- Downloadable answer files
- Usage and billing history
- Support/contact functionality

### Backend API

Create an API service responsible for:

- User authentication and sessions
- Subscription and plan checks
- Encrypted credential storage or local OS credential storage
- Device registration and license authorization
- Usage limits
- Results and audit records
- Payment webhook handling

FastAPI, Django, Node.js, or another maintained backend framework would work. The
current automation functions can eventually be moved behind this API, but they should
not remain directly exposed to customers.

### Job queue

For the local-agent plan, the scheduled agent starts the job itself, so a server-side
queue is optional at first. The backend should still record runs. If you later offer a
server-run plan, use Redis with Celery/RQ or a managed cloud queue. A job can have states
such as:

```text
queued → running → downloading → solving → uploading → completed
                                  ↘ failed
```

The dashboard can poll for status initially. WebSockets or server-sent events can be
added later for live updates.

### Automation workers

For the local plan, the packaged agent runs Playwright on the customer's laptop. For a
server-run plan, use isolated worker containers or virtual machines with browser and OCR
dependencies installed in a repeatable Docker image.

Workers should receive only the job data they need, process one customer job at a time
where practical, clean temporary files afterward, and report structured errors to the
backend.

### Storage

Use a database such as PostgreSQL for users, plans, jobs, statuses, and audit records.
Use private object storage such as S3-compatible storage for assignment files and answer
PDFs. Do not store customer files in a publicly accessible bucket.

## 5. Credential and privacy design

This is the most important production concern because the service handles student portal
credentials and academic files.

- Remove hardcoded credentials from the application before launch.
- Never log passwords, access tokens, or complete portal responses.
- Encrypt credentials at rest using a managed key or a dedicated secrets system.
- Restrict who can access production credentials and database records.
- Use HTTPS everywhere.
- Use strong customer authentication, rate limits, and optional two-factor login.
- Give customers a way to delete their account and stored credentials.
- Automatically delete temporary downloads and generated files after a defined period.
- Keep audit records without storing unnecessary sensitive content.
- Separate development, staging, and production environments.
- Rotate encryption keys and service credentials periodically.

Before selling, confirm that automating the portal, storing credentials, uploading AI-
generated work, and processing student data are allowed by the college and portal terms.
Obtain explicit customer consent and publish a privacy policy and terms of service.

## 6. AI and cost control

Do not expose your OpenRouter key to the frontend or customer devices. Keep it only on
the backend or in a secrets manager. The local agent should send required job data to
your authenticated backend for AI processing.

Track per-job costs, token usage, model responses, and failures. Your pricing must cover:

- Hosting
- Browser workers
- OCR processing
- AI API calls
- File storage and bandwidth
- Payment fees
- Support and maintenance

Add limits such as assignments per month, maximum file size, maximum pages, and maximum
AI questions per job. Require confirmation before processing unusually large jobs.

## 7. Payments and plans

Start with simple plans rather than complex billing:

- Trial: limited number of jobs
- Student monthly plan: fixed monthly job allowance
- Pay-per-assignment plan: useful for occasional users
- College or department plan: negotiated limits and support

Use a payment provider that supports your operating country, such as Razorpay or Stripe
where available. The backend must verify payment-provider webhooks rather than trusting
frontend payment status.

Suggested enforcement rules:

- Block new jobs when the plan is inactive.
- Reserve usage when a job starts.
- Refund or restore usage when a failed job was caused by your infrastructure.
- Keep an idempotency key so a repeated payment webhook cannot create duplicate access.

## 8. Deployment options

### Early pilot

Use one VPS or cloud instance with Docker, a database, a queue, and one automation
worker. This is affordable and enough for a small number of trusted testers.

### Production launch

Separate the web/API service, worker service, database, and object storage. Add backups,
monitoring, error tracking, and automatic deployment from a private repository.

Possible infrastructure choices include a managed VPS, AWS, Google Cloud, Azure, or a
platform that supports Docker workers. Choose based on budget, regional availability,
and whether the browser automation is permitted by the target portal.

The deployment should be reproducible from a Dockerfile and documented environment
configuration. Never depend on a manually configured personal laptop for production.

## 9. Source-code protection

Keep the repository private and run the automation only on infrastructure you control.

- Do not send `main.py` or readable source code to customers. Send only a signed,
  packaged agent installer.
- Do not put secrets in frontend JavaScript.
- Do not rely on Python obfuscation as the main protection; server-side execution is
  stronger and easier to maintain.
- Restrict repository, cloud, database, and CI/CD access with separate accounts.
- Use private package registries or locked dependency versions where appropriate.
- Back up the private repository and production configuration securely.

If a customer later demands an on-premise installation, treat that as a separate
enterprise product. It will require licensing, a protected deployment package, update
management, and a different security model.

## 10. Changes required before launch

The current project is a working prototype, not yet a multi-user service. Before
commercial use, plan to:

1. Move credentials and all configuration into secure environment/secrets management.
2. Replace hardcoded single-user assumptions with tenant/customer records.
3. Create signed Windows, macOS, and Linux installers with one-time setup and scheduling.
4. Separate portal automation, the local agent, and the web API.
5. Replace console printing with structured logging and customer-safe error messages.
6. Add job IDs, retry rules, timeouts, cancellation, and recovery after worker failure.
7. Prevent duplicate answer generation and duplicate uploads.
8. Store files in isolated per-customer locations.
9. Add authentication, authorization, quotas, and payment checks.
10. Add tests for extraction, question parsing, PDF generation, scheduling, and portal failure cases.
11. Package Playwright, Chromium, OCR, Poppler, and other dependencies inside the agent.
12. Add monitoring for failed jobs, login failures, AI failures, upload failures, and
    worker health.
13. Test against multiple real customer accounts with permission before launch.

The existing code should be treated as the automation engine that will eventually be
wrapped by the service, not as the customer-facing product itself.

## 11. Practical implementation phases

### Phase A — Product and compliance validation

- Confirm portal and college rules.
- Speak with a few students and validate the exact workflow they will pay for.
- Decide whether the service generates drafts for review or submits automatically.
- Define data retention, refund, privacy, and support policies.

### Phase B — Reliable single-customer agent

- Package the current automation into a repeatable desktop agent.
- Build one-time setup and secure operating-system credential storage.
- Register and test daily schedules on Windows, macOS, and Linux.
- Add structured job results and optional backend reporting.

### Phase C — Multi-user service foundation

- Add accounts, device registration, license checks, database records, private file
  storage, and a basic responsive dashboard.
- Add backend AI processing so API keys are not shipped inside the agent.

### Phase D — Billing and controlled pilot

- Add subscriptions or credits.
- Invite a small group of students.
- Track costs, failures, support requests, and portal changes.
- Keep automatic upload disabled until reliability and consent are clear.

### Phase E — Public launch

- Add monitoring, backups, rate limits, terms, privacy policy, support, and incident
  procedures.
- Publish the web app URL and onboarding instructions.
- Continue improving the worker without requiring customers to reinstall anything.

## 12. What customers should download

For this automatic local-agent version, customers download only a signed installer for
their operating system. They do not receive the repository or readable source code.

Optional later additions:

- A PWA install shortcut for phone and desktop.
- A small desktop helper/agent for Windows, macOS, and Linux.
- Native Android/iOS apps only if the web dashboard cannot provide the needed experience.

The simplest sellable offering is therefore:

```text
Signed desktop agent + one-time setup + daily scheduler + private backend + billing
```

Customers complete setup once and then remain hands-off. Their laptop must be powered on
and online for the scheduled run; a phone can be used for setup and status, but should
not be expected to run the automation itself. Your source code and AI keys remain under
your control.
