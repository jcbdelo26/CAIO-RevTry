# CLAUDE.md - RevTry

This file guides development inside `E:\Greenfield Coding Workflow\Project-RevTry\`.

---

## 1. Project State

RevTry is a warm-first Revenue Operations system for ChiefAIOfficer.com.

Current build sequence:
- Phase 0A-0B: runtime foundation + live GHL triage
- Phase 1: cold campaign draft pipeline + approval dashboard
- Phase 2: shared dispatch safety
- Phase 3A-3E: warm follow-up system + pre-Vercel hardening
- Phase 3F: Vercel deployment of the warm dashboard
- Phase 4: cold-outbound expansion
- Phase 5: revenue intelligence + autonomy graduation

Current code status:
- Warm generation, review, approval, dispatch, scheduler, auth, storage abstraction, and deploy-readiness hardening are implemented
- Full local suite is green: `318 passed`
- Task 3B evidence is reconciled in the project-local runtime copy
- **Vercel deployment live** at `caio-rev-try.vercel.app` (2026-03-10)
  - Auth working, pages rendering, warm-only mode active
  - Dashboard shows zeros — pipeline not yet run against real GHL data
  - Remaining: DB timeout hardening, healthz DB probe, 4 route error handlers, pipeline data population

---

## 2. Workspace Boundaries

All development is consolidated in:
- `E:\Greenfield Coding Workflow\Project-RevTry\`

Key subdirectories:
- `src/` — application codebase
- `revtry/vault/` — business rules, integration configs, compliance
- `revtry/registry/` — task tracking, phase gates, operational state
- `revtry/guardrails/` — validation gates, hard blocks, policies
- `revtry/agents/` — agent configs and output schemas
- `mcp-servers/ghl-mcp/` — GHL MCP server (local copy)

MCP config:
- `E:\Greenfield Coding Workflow\Project-RevTry\.mcp.json` — project-root MCP server config

---

## 3. Core Architecture

Warm-first operator path:
- `/briefing` -> `/followups` -> approve/reject -> `/dispatch`

Compatibility rules:
- `GET /` stays backward-compatible in local mixed mode
- `WARM_ONLY_MODE=true` redirects `GET /` to `/briefing`
- Cold routes are hidden or blocked in deployed warm-only mode

Shared send safety:
- circuit breaker -> rate limiter -> dedup before any send
- warm GHL sends have priority over cold GHL sends

Warm context isolation:
- allowed: compacted primary-thread conversation context, signatures/compliance, minimal CTA/proof context
- not allowed: cold angle playbooks, broad ICP/campaign context, revenue-intel context, autonomy context

Approval rule:
- no email is ever sent without explicit human approval
- warm approval changes draft state only; it does not create GHL tasks or upsert contacts

---

## 4. Persistence Model

Local development:
- `STORAGE_BACKEND=file`
- human-readable JSON/Markdown stays the default local state model

Deployed warm mode:
- `STORAGE_BACKEND=postgres`
- `DATABASE_URL` is canonical, `POSTGRES_URL` is fallback only
- deployed warm mode must not use file-backed persistence

Implemented abstraction:
- `src/persistence/base.py`
- `src/persistence/file_store.py`
- `src/persistence/postgres_store.py`
- `src/persistence/factory.py`
- `src/persistence/schema.sql`

Systems already using the backend abstraction:
- warm follow-up storage
- briefing loading
- conversation scan persistence
- conversation analysis persistence
- warm orchestrator
- warm dispatcher
- rate limiter
- circuit breaker
- dedup

Trace logging:
- file backend: writes trace files
- postgres backend: emits structured JSON logs instead of writing local trace files

---

## 5. Dashboard and Access Control

Implemented routes:
- `GET /healthz`
- `GET /briefing`
- `GET /followups`
- `GET /followups/{id}`
- `POST /followups/{id}/approve`
- `POST /followups/{id}/reject`
- `POST /followups/batch/approve`
- `POST /followups/batch/reject`
- `POST /followups/generate`
- `GET /dispatch`
- `POST /dispatch/run`
- `GET /dispatch/status`

Auth:
- `DASHBOARD_AUTH_ENABLED=false` is acceptable for local mixed mode
- deployed dashboard requires HTTP Basic Auth
- all dashboard HTML and mutating routes are protected when auth is enabled
- `/healthz` stays open for smoke checks

Warm-only deployed mode:
- `WARM_ONLY_MODE=true`
- cold dashboard routes should not be exposed remotely

---

## 6. Important Code Areas

Agents:
- `src/agents/conversation_analyst_agent.py`
- `src/agents/followup_draft_agent.py`
- `src/agents/campaign_craft_agent.py`

Dashboard:
- `src/dashboard/app.py`
- `src/dashboard/auth.py`
- `src/dashboard/followup_storage.py`
- `src/dashboard/briefing_loader.py`
- `src/dashboard/storage.py`

Pipeline:
- `src/pipeline/followup_orchestrator.py`
- `src/pipeline/followup_dispatcher.py`
- `src/pipeline/scheduler.py`
- `src/pipeline/dispatcher.py`
- `src/pipeline/rate_limiter.py`
- `src/pipeline/circuit_breaker.py`
- `src/pipeline/dedup.py`

Integrations:
- `src/integrations/ghl_client.py`
- `src/integrations/anthropic_client.py`

Models:
- `src/models/schemas.py`
- `src/models/__init__.py`

Utilities:
- `src/utils/business_time.py`
- `src/utils/trace_logger.py`

Validators:
- `src/validators/followup_gate2_validator.py`
- `src/validators/followup_gate3_validator.py`
- `src/validators/gate1_validator.py`

---

## 7. Environment Contract

Critical env vars:
- `GHL_API_KEY`
- `GHL_LOCATION_ID`
- `APOLLO_API_KEY`
- `ANTHROPIC_API_KEY`
- `VAULT_DIR`
- `REGISTRY_DIR`
- `DASHBOARD_AUTH_ENABLED`
- `DASHBOARD_BASIC_AUTH_USER`
- `DASHBOARD_BASIC_AUTH_PASS`
- `STORAGE_BACKEND`
- `DATABASE_URL`
- `WARM_ONLY_MODE`
- `DAILY_SCAN_BATCH_SIZE`
- `FOLLOWUP_SCAN_DAYS`
- `SCHEDULER_ENABLED`
- `SCHEDULER_TIMEZONE`

Defaults:
- `SCHEDULER_TIMEZONE=America/Chicago`
- `SCHEDULER_ENABLED=false`
- `MAX_SCAN_CONTACTS` is deprecated and exists only as a temporary alias

Fail-fast rule:
- `GHLClient` raises `MissingGhlCredentialsError` when GHL credentials are absent

---

## 8. Development Rules

- Keep warm prompts lean; do not load cold playbook context into warm agents
- Keep `GET /` backward-compatible in local mixed mode
- Do not mark failed sends as `DISPATCHED`; use `SEND_FAILED`
- Same-day warm reruns must be idempotent by `businessDate`
- Business-date logic must resolve in `America/Chicago`
- Do not add remote deployment assumptions that depend on local file paths
- Do not treat green tests as a substitute for runtime `Task 3B`
- DnD/unsubscribed contacts must never reach `/followups` — filtered at scan time and at display time
- The `/followups` queue must ONLY show contacts with drafts (`draftId is not None`). Analysis-only contacts are not actionable and must not appear in the queue
- Draft generation must aim for >90% success rate. If Gate 3 Check 2 (conversation reference) rejects >10% of drafts, the matching logic is too strict and must be relaxed

## 8a. Post-Implementation Verification Protocol

After every major UI/UX or backend change, spawn parallel verification agents BEFORE committing:

1. **Code Review Agent** — Review modified files for bugs, logic errors, security issues, and project convention adherence. Use `superpowers:code-reviewer` or `pr-review-toolkit:code-reviewer`.
2. **Visual Validation Agent** — Use Playwright browser tools to screenshot affected dashboard pages and verify: correct rendering, no visual regressions, expected data display, proper badge/label states.
3. **Code Simplifier Agent** — Review recently modified code for clarity, consistency, and maintainability using `pr-review-toolkit:code-simplifier`.

**Triggers** — template changes (`src/dashboard/templates/`), route handler changes (`src/dashboard/app.py`), model changes affecting display, CSS changes in `base.html`, pipeline changes affecting dashboard data.

All 3 agents run IN PARALLEL. Fix any issues they identify before committing.

---

## 9. Validation Commands

```powershell
# Syntax
Get-ChildItem -Path src -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }

# Full suite
Set-Location 'E:\Greenfield Coding Workflow\Project-RevTry\src'
python -m pytest tests -q
```

Current baseline:
- `365 passed`
- `29` test files

---

## 10. Deployment Files

Vercel-specific files (not part of src/):
- `api/index.py` — Vercel serverless entry point (adds `src/` to sys.path, imports FastAPI app)
- `vercel.json` — Vercel build/route config (all traffic → `api/index.py`)
- `requirements.txt` (root) — production dependencies for Vercel

---

## 11. Current Next Steps

**Phase 3F status:**
- Tasks 62A-62D: DONE — DB hardening, healthz, error handling, pipeline populated
- Task 63: IN_PROGRESS — route verification, approve/reject flow testing
- Task 64: PENDING — Dani remote access verification from phone
- DnD/unsubscribe filtering: DONE — contacts filtered at scan time + display time

**Parallel priority (Phase 0 audit chain):**
- Task 15: Execute GHL audit
- Tasks 16-22: Complete audit → triage → notification chain

Rules:
- Treat Phase 3F as deployment configuration and remote verification work, not a reason to reopen warm product scope
- NEVER send real emails — pipeline generates drafts for review only
