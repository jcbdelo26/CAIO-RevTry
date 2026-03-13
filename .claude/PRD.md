# PRD — RevTry: Revenue Operations Sentry
## ChiefAIOfficer.com
**Version**: 2.15 | **Date**: 2026-03-13 | **Status**: Phase 3G Complete (Tasks 75-80, 82 done; Task 81 data-blocked); Phase 4 unblocked
**Refined by**: Greenfield Coding Workflow bulletproofing process
**Source**: `E:\CAIO RevOps Claw\RevTry_PRD.md` v1.0

---

## 0. CRITICAL READ-FIRST

This build now uses one authoritative project/runtime root.

**Authoritative Project Root**
- Project + runtime root: `E:\Greenfield Coding Workflow\Project-RevTry\`
- Runtime registry/vault root: `E:\Greenfield Coding Workflow\Project-RevTry\revtry\`
- Runtime slash commands and `.mcp.json` live inside the Project RevTry root and are the files to use moving forward.

**Legacy reference workspace**
- `e:/CAIO RevOps Claw/` is now reference-only unless explicitly reactivated.
- Do not write new operational state there for this project.
- Historical source docs from the CAIO workspace may still be consulted, but the active runtime source of truth is Project RevTry.

**Alpha-swarm reuse policy:**
- Allowed: business knowledge extracted into vault files
- Allowed: the existing GHL MCP server entrypoint, if it exists and passes dependency preflight
- NOT allowed: alpha-swarm runtime architecture, deployment assumptions, agent class structure, or pipeline code

**Shell standard:**
- Canonical execution shell: `PowerShell 7 / Windows PowerShell`
- Git Bash is optional only when invoked by explicit path and verified on the machine
- Do NOT assume `bash.exe` on PATH is usable

**Environment readiness gate (must pass before Phase 0A or Phase 0B starts):**
1. Confirm the external GHL MCP server entrypoint exists at `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`
2. Run `python -m py_compile` against `server.py`, then start `python server.py` and capture output
3. If import/dependency errors occur, install the explicit packages required by the file imports (`mcp`, `aiohttp`, `python-dotenv`) and retry. Do NOT assume `requirements.txt` or `pyproject.toml` exists.
4. If the entrypoint file is missing entirely: log a Phase 0 blocker to `revtry/registry/escalations.md` and stop. Do not stub. Escalate to Chris.
5. Confirm required environment variables are present: `GHL_API_KEY`, `GHL_LOCATION_ID`
6. Confirm the GHL Private Integration token has the read/write scopes required for safe smoke validation. A token that can read but cannot write keeps Task 3B and the tag-safety smoke blocked.
7. Launch the fresh Claude Code runtime session for Task 3B from an env-ready PowerShell shell. The current shell is NOT reliable proof that the Claude runtime session inherited the same environment.
8. Run live GHL tool discovery and write the verified tool list + input/output schema notes into `revtry/vault/integrations/ghl.md`
9. For Task 3B PASS, write-capable MCP tools must be verified only against designated safe smoke assets (test contact emails, safe pipeline/stage, safe workflow, safe calendar). If safe assets are missing, unsafe, or blocked by missing write scopes, PAUSE the task and keep the Phase 0A live gate closed.
10. If any required dependency, read capability, or safe-write scope is missing, log a Phase 0 blocker to `revtry/registry/escalations.md` and stop implementation
11. If `SLACK_WEBHOOK_URL` is absent, record notification behavior as `SKIPPED_OPTIONAL`; this is warning-only for Phase 0 infrastructure checks

**Phase 0A hard gate:** Hero Outcome 1 is blocked until the external GHL MCP exposes the read capabilities required for audit and triage. No PRD section may assume audit or triage is runnable before Phase 0A passes.

**Immediate operational priority now:** Phase 3F COMPLETE (`PHASE_3F_VERCEL_LIVE` PASSED 2026-03-11). Phase 3G COMPLETE except Task 81 (data-blocked ~2 weeks). Live dispatch active (`DISPATCH_DRY_RUN=false`). Queue visibility fix deployed (Task 87, 2026-03-13). Hero Outcome 2 at 5/10 approved drafts — Dani needs 5 more. **Current focus: Phase 4 (cold outbound expansion) is now fully unblocked.** Task 81 resumes when production baseline data is available.

**Known inconsistency:** The external `manifest.json` may advertise fewer tools than `server.py` documents. Treat live discovery as the ONLY source of truth for tool availability and behavior. Treat `server.py` as the authoritative entrypoint path. Do not treat the manifest tool list as complete.

**Warm-first pre-production execution rule:**
- Warm follow-up (Phase 3A-3F) is the first post-foundation acceptance gate.
- Vercel deployment starts immediately after the warm dashboard passes local/private validation.
- Cold outbound expansion and autonomy graduation stay on the active roadmap, but they must not expand the warm MVP context surface.
- Warm phases may load only compacted primary-thread conversation context, signatures/compliance rules, and minimal CTA/proof context when needed.
- Warm phases may NOT load cold-outbound angle playbooks, broad ICP/campaign context, or autonomy policy context unless a later phase explicitly requires it.

**Tag-safety hotfix gate:**
- Freeze non-essential GHL writes until the add-only tag hotfix is coded and validated.
- Task 3B smoke writes remain allowed because they are restricted to designated safe smoke assets.
- All contact tag writes are add-only. Generic contact upsert/update payloads may not include `tags`, `tagIds`, or equivalent clear/remove semantics.
- Any audit-confirmed tag-loss recovery must use an exact incident manifest, dry-run diff, additive-only restore, and post-restore verification before broader writes resume.
- Phase 3F deployment and further feature development remain blocked until both `PHASE_3E_TAG_SAFETY_HOTFIX = PASSED` and `PHASE_3E_TAG_RECOVERY_COMPLETE = PASSED`.

**Authoritative Project Root**: `E:\Greenfield Coding Workflow\Project-RevTry\`
**Runtime Root**: `E:\Greenfield Coding Workflow\Project-RevTry\`
**Registry/Vault Root**: `E:\Greenfield Coding Workflow\Project-RevTry\revtry\`

---

## 1. PROJECT OVERVIEW

RevTry is a Revenue Operations Sentry for ChiefAIOfficer.com — an agentic system that monitors the GHL CRM, surfaces prioritized follow-up contacts for Dani Apgar, generates warm follow-up drafts grounded in real conversation history, and expands into cold-outbound campaign drafting only after the warm system is validated. Built for a two-person GTM team (Chris Daigle, GTM/PTO Engineer + Dani Apgar, Head of Sales), it replaces manual pipeline review with an orchestrator-and-specialists architecture that applies strict, versioned business rules from a knowledge vault, validates every output through a 3-gate maker-checker loop, and compounds its own performance through structured feedback. No code ships between phases — each phase produces a shippable, independently operable capability with zero dependencies on future phases.

---

## 1A. MISSION

Enable a two-person GTM team to operate a staged, approval-gated Revenue Operations pipeline — identifying, prioritizing, and contacting the right leads — with zero manual CRM work from Dani and zero guesswork from Chris.

---

## 1B. TARGET USERS

- **Primary — Dani Apgar (AE, Head of Sales)**: Needs a daily prioritized warm follow-up briefing and approval-ready drafts in a dashboard — without ever opening the CRM
- **Secondary — Chris Daigle (GTM/PTO Engineer)**: Needs to orchestrate the system via natural language goals, review validated outputs, manage vault evolution, and handle escalations from the agent system
- **System Actors (non-human)**: Pipeline Ops Agent, Campaign Craft Agent, Quality Guard — operate autonomously within guardrails defined by Chris and Dani; output never reaches humans without passing all 3 validation gates

---

## 2. TECH STACK

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| Claude Code (claude-sonnet-4-6) | Orchestrator runtime + all agent sessions | Native tool use, slash commands, and fresh-session maker-checker workflow; no additional orchestration layer needed |
| Python MCP Server (`ghl-mcp/server.py`) | GHL API bridge | Existing external entrypoint; Phase 0A must extend it with read capabilities required for audit and triage before Hero Outcome 1 is attempted |
| PowerShell 7 / Windows PowerShell | Canonical execution shell | Reliable on the current machine; used for validation commands, environment checks, and Slack webhook examples |
| GoHighLevel (GHL) API | CRM — contacts, pipelines, appointments, tags | Primary system of record for all pipeline data and warm outreach |
| Instantly V2 | Cold email dispatch (warmed domains only) | 6 warmed domains; CAN-SPAM compliant; isolated from GHL to protect domain reputation |
| HeyReach | LinkedIn outreach | Campaign-tiered LinkedIn sequencing (T1/T2/T3); 4-week warmup required before Phase 2 |
| Apollo | Lead discovery + enrichment (waterfall step 1) | Primary enrichment source; 200 req/hr API cap |
| BetterContact | Enrichment waterfall step 2 | Fallback when Apollo returns null email |
| Clay | Enrichment waterfall step 3 | Final fallback before marking field null |
| FastAPI + Jinja2 | Local/deployed dashboard + warm review surface | Lightweight Python server for cold draft review, warm briefing review, manual dispatch approval, and the first deployed warm dashboard |
| Anthropic SDK (`anthropic>=0.40`) | Warm conversation analysis + personalized follow-up drafting | Shared client wrapper required for retries, timeouts, JSON repair, and trace logging |
| APScheduler (`>=3.10`) | Warm follow-up scheduling | Daily warm run scheduler; disabled by default until manual flow is validated |
| America/Chicago scheduler timezone | Canonical warm follow-up schedule clock | Keeps daily briefing behavior aligned with team operating time and DST |
| HTTP Basic Auth | Pre-production dashboard access control | Lean remote protection for approve/reject/generate/dispatch routes before a larger auth system exists |
| Postgres (`DATABASE_URL`) | Deployed warm persistence backend | Required for deployed warm mode; local file storage remains the dev default |
| Vercel | Phase 3F deployed warm dashboard | Deployment hardening begins immediately after local/private warm dashboard validation passes |
| Slack webhook | Async notifications to #revtry | Optional and non-blocking; PASS records explicit `notificationStatus` evidence when `SLACK_WEBHOOK_URL` is missing or unusable |
| File-backed JSON/Markdown | Local development state + business rules | Human-readable local state for drafts, briefings, vault rules, and registry artifacts during local development |

**Required environment variables:**
- `GHL_API_KEY` — GHL Private Integration token
- `GHL_LOCATION_ID` — GHL Location/Sub-account ID
- `GHL_CALENDAR_ID` — (optional) default calendar ID
- `SLACK_WEBHOOK_URL` — (optional) enables Slack notifications; system degrades gracefully if absent
- `FEEDBACK_LOOP_POLICY_ENABLED` — (optional) enables dynamic GUARD-004 banned opener updates
- `ANTHROPIC_API_KEY` — required for Phase 3B/3C conversation analysis + follow-up drafting
- `DAILY_SCAN_BATCH_SIZE` — canonical max contacts scanned per warm run
- `FOLLOWUP_SCAN_DAYS` — lookback window for conversation scanning (default: 90 days)
- `SALES_TEAM_USER_IDS` — (optional) comma-separated GHL user IDs; contacts with recent manual outbound from these users are tagged with an "Active Deal" badge in the dashboard (not excluded)
- `SCHEDULER_ENABLED` — enables Phase 3E scheduler when set to `true`
- `SCHEDULER_TIMEZONE` — default `America/Chicago`
- `MAX_SCAN_CONTACTS` — deprecated alias for `DAILY_SCAN_BATCH_SIZE` during Phase 3A transition only
- `DASHBOARD_AUTH_ENABLED` — enables HTTP Basic Auth for all dashboard routes; deployed default is `true`
- `DASHBOARD_BASIC_AUTH_USER` — required when dashboard auth is enabled
- `DASHBOARD_BASIC_AUTH_PASS` — required when dashboard auth is enabled
- `STORAGE_BACKEND` — `file` for local dev, `postgres` for deployed warm mode
- `DATABASE_URL` — canonical Postgres connection string for deployed warm mode
- `POSTGRES_URL` — fallback only if `DATABASE_URL` is absent
- `WARM_ONLY_MODE` — hides cold operator surfaces and redirects `/` to `/briefing` in deployed warm-first mode
- `DISPATCH_DRY_RUN` — when `true`, dispatch logs email payloads without sending via GHL; safety mechanism for E2E testing and pre-launch verification

---

## 3. CORE FUNCTIONALITY — USER STORIES

### Phase 0 — Foundation + GHL Triage

- **US-1**: As Chris, I want to run `/prime` at session start so that I always see the current state of active tasks, recent failures, and any vault files that are stale — in under 30 seconds.
- **US-2**: As Chris, I want to run `/plan-task` with a natural language goal so that the orchestrator produces a zero-ambiguity task spec (with context package, output schema, and binary validation criteria) without me writing it manually.
- **US-3**: As Dani, I want a prioritized list of GHL contacts to follow up with today delivered with a recorded notification outcome so that I spend zero time deciding who to contact from the CRM.

### Phase 1 — Campaign Drafts

- **US-4**: As Chris, I want to trigger a full Recon → Enrichment → Segmentation → Campaign Craft pipeline so that 10+ ICP-qualified campaign drafts are ready for Dani to review without me assembling context manually.
- **US-5**: As Dani, I want a local dashboard showing formatted campaign drafts (subject, body, ICP tier, score) so that I can approve or reject each one with a note — without opening GHL.
- **US-6**: As Chris, I want Dani's rejection notes to automatically update the banned opener list and vault feedback so that the next draft batch improves without manual rule edits.

### Phase 2 — Outreach Dispatch

- **US-7**: As Dani, I want approved drafts dispatched via the correct channel (Instantly for cold, GHL for warm) at enforced daily rate limits so that I never accidentally burn domain reputation.
- **US-8**: As Chris, I want a circuit breaker to halt all sends to an integration when 3 consecutive failures occur so that I'm notified before damage compounds.

### Phase 3 — Warm Follow-Up System (Current Implementation Priority)

- **US-9**: As Dani, I want a daily warm follow-up briefing grouped by urgency and trigger so that I can work the right active conversations first.
- **US-10**: As Dani, I want AI-drafted follow-ups that reference the actual prior conversation so that I never send a disconnected warm email.
- **US-11**: As Chris, I want daily warm-run metrics showing scanned contacts, skipped contacts, analysis failures, draft failures, and estimated Anthropic cost so that I can validate the system without digging through logs.
- **US-12**: As Chris, I want warm follow-up drafts to use the same shared GHL safety rails and mandatory approval gate as every other outbound path so that speed never bypasses control.

### Phase 3F — Warm Dashboard Deployment to Vercel

- **US-13**: As Dani, I want the validated warm follow-up dashboard available remotely after local/private staging passes so that I can review and approve follow-ups without staying on the dev machine.

### Subsequent Active Track (After Warm Validation + Deployment)

- **US-14**: As Dani, I want cold outbound to return as a separate tested operator flow so that warm follow-up stays lean while cold expansion continues intentionally.
- **US-15**: As Chris, I want a deployed KPI dashboard showing campaign and follow-up metrics so that I can monitor pipeline health without querying raw data.
- **US-16**: As Chris, I want the system to graduate autonomy only after validated outbound performance proves it is safe so that send limits increase from evidence, not assumption.

---

## 4. DATA MODELS

Entity-level schemas spanning the system. Agent-specific JSON output schemas are in Section 13.

### Contact
*(Source: GHL; enriched by agents)*

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| id | string | GHL | GHL contact ID |
| email | string | GHL | Required; validated RFC 5322 |
| firstName | string | GHL | |
| lastName | string | GHL | |
| title | string | GHL/Apollo | Normalized to tier bucket before scoring |
| companyName | string | GHL/Apollo | |
| companySize | integer\|null | Apollo | Null if unavailable |
| industry | string\|null | Apollo | Normalized to tier bucket; null if unavailable |
| revenue | string\|null | Apollo | "$10M-$50M" format; null if unavailable |
| tags | string[] | GHL | Used for Customer/Competitor detection |
| dateLastActivity | ISO8601 | GHL | Key triage field for Phase 0 prioritization |
| dateUpdated | ISO8601 | GHL | CRM update timestamp |
| source | string | GHL | Lead origin |
| customFields | object | GHL | Structure discovered during Phase 0 audit |
| linkedinUrl | string\|null | Recon/Enrichment | LinkedIn profile URL; null if unavailable |
| icpTier | "1"\|"2"\|"3"\|"DISQUALIFIED"\|null | Segmentation Agent | Null until segmentation runs |
| icpScore | float 0-150\|null | Segmentation Agent | Weighted score (base 0-100 × multiplier up to 1.5x = max 150); math must be shown |
| enrichmentScore | integer 0-100\|null | Enrichment Agent | <70 = not ready for Campaign Craft |

### Lead
*(A scored Contact that has passed segmentation)*

| Field | Type | Notes |
|-------|------|-------|
| contactId | string | FK to Contact.id |
| baseScore | integer 0-100 | Before multiplier |
| industryMultiplier | float | From tier_definitions.md (1.5x / 1.2x / 1.0x / 0.8x) |
| icpScore | float 0-150 | baseScore × multiplier (standardized name — never use `weightedScore`) |
| scoreBreakdown | string | Human-readable math (required in every output) |
| whyThisScore | string | Plain-language explanation |
| tier | "1"\|"2"\|"3"\|"DISQUALIFIED" | |
| disqualificationReason | string\|null | Non-null only if DISQUALIFIED |

### Task
*(Registry entry for every agent operation)*

| Field | Type | Notes |
|-------|------|-------|
| taskId | string | Format: `TASK-YYYYMMDD-HHmmssfff-RAND4` |
| sessionId | string | Format: `{agent}-{yyyyMMdd-HHmmssfff}-{random4}` e.g. `pipeline-ops-20260306-093015127-xKmR`. Generated in PowerShell at lock claim time in `/execute`. The 4-char random suffix eliminates millisecond-resolution collisions. |
| agent | string | Agent name from permission matrix |
| goal | string | Binary goal statement (testable yes/no) |
| status | enum | `ACTIVE` \| `BLOCKED_HARD_RULE` \| `AWAITING_VALIDATION` \| `FAILED_VALIDATION` \| `COMPLETED` |
| attemptNumber | integer | Computed as `count(registry/failures.md rows for taskId) + 1` before execution starts |
| operationIntents | string[] | Normalized action tokens from the task spec, used by `/plan-task` lint and `/execute` hard-block preflight |
| notificationPolicy | enum | `required` \| `best_effort` \| `not_applicable` |
| notificationStatus | enum\|null | `SENT` \| `SKIPPED_OPTIONAL` \| `FAILED` \| `NOT_APPLICABLE`; populated by `/validate` |
| makerSessionId | string\|null | Recorded by `/execute` when candidate output is created |
| validatorSessionId | string\|null | Recorded by `/validate`; must differ from makerSessionId before PASS is allowed |
| dispatchedAt | ISO8601 | When orchestrator wrote the task spec |
| leaseExpiresAt | ISO8601 | 2 hours from sessionId claim; expired locks may be reclaimed |
| lockOwner | string | sessionId of claiming session |
| vaultFilesUsed | string[] | Populated by /execute at runtime |

**Shared DraftApprovalStatus enum**: `PENDING | APPROVED | REJECTED | DISPATCHED | SEND_FAILED`

### Campaign Draft
*(Output of Campaign Craft agent)*

| Field | Type | Notes |
|-------|------|-------|
| draftId | string | Format: `DRAFT-YYYYMMDD-HHMM-N` |
| contactId | string | FK to Lead.contactId |
| icpTier | "1"\|"2"\|"3" | Determines which angle was used |
| subject | string | ≤60 chars; no ALL CAPS; ≤1 exclamation mark |
| body | string | Personalized; no banned openers; references specific lead/company/industry |
| channel | "instantly"\|"ghl"\|"heyreach" | From domain_rules.md |
| bookingLink | string | Always `https://caio.cx/ai-exec-briefing-call` |
| status | "PENDING"\|"APPROVED"\|"REJECTED"\|"DISPATCHED"\|"SEND_FAILED" | Shared approval/send enum; `SEND_FAILED` is required for Phase 2+ and Phase 3 warm dispatch correctness |
| rejectionNote | string\|null | Dani's reason; fed to /metabolize |
| approvalTimestamp | ISO8601\|null | |

### Conversation Analysis
*(Output of the warm Conversation Analyst agent)*

| Field | Type | Notes |
|-------|------|-------|
| contactId | string | FK to Contact.id |
| sourceConversationId | string | Deterministically selected primary thread |
| trigger | "no_reply"\|"awaiting_our_response"\|"gone_cold" | Deterministic trigger class before LLM call |
| triggerReason | string | Plain-language explanation of why the trigger was selected |
| sentiment | "positive"\|"neutral"\|"negative"\|"cold" | Warm conversation sentiment classification |
| stage | "new"\|"engaged"\|"stalled"\|"won"\|"lost" | Conversation stage |
| urgency | "hot"\|"warm"\|"cooling" | Warm-priority bucket |
| summary | string | Compact summary of the primary thread only |
| keyTopics | string[] | Extracted topics used downstream for drafting |
| recommendedAction | string | Recommended next step if a draft should be created |
| confidence | float 0.0-1.0\|null | Shadow telemetry; not used for routing until calibrated. Added Phase 3G. |

### Follow-Up Draft
*(Warm follow-up draft stored separately from cold campaign drafts)*

| Field | Type | Notes |
|-------|------|-------|
| draftId | string | Deterministic per `(contactId, sourceConversationId, businessDate)`; same-day reruns overwrite, next-day reruns create a new draft |
| contactId | string | FK to Contact.id |
| sourceConversationId | string | Primary thread used for drafting |
| businessDate | YYYY-MM-DD | Warm business date in `America/Chicago`; used for idempotent draft identity |
| generationRunId | string | Traceable run identifier for the orchestration pass that wrote the draft |
| trigger | "no_reply"\|"awaiting_our_response"\|"gone_cold" | Carries forward from Conversation Analysis |
| urgency | "hot"\|"warm"\|"cooling" | Used for briefing and queue sort |
| sentiment | "positive"\|"neutral"\|"negative"\|"cold" | |
| stage | "new"\|"engaged"\|"stalled"\|"won"\|"lost" | |
| subject | string | ≤60 chars |
| body | string | <150 words; explicitly references real prior conversation |
| channel | "ghl" | Warm MVP is GHL email only |
| status | "PENDING"\|"APPROVED"\|"REJECTED"\|"DISPATCHED"\|"SEND_FAILED" | Approval is separate from dispatch |
| rejectionNote | string\|null | Dani feedback for warm drafts |
| approvalTimestamp | ISO8601\|null | |
| analysisSummary | string | Short analysis carry-forward for UI and debugging |
| editDiff | object\|null | `{"subject": {"before", "after"}, "body": {"before", "after"}}` — captured on edit. Added Phase 3G. |

### Daily Briefing
*(One per warm run date)*

| Field | Type | Notes |
|-------|------|-------|
| briefingDate | YYYY-MM-DD | One daily file per date unless forced |
| generatedAt | ISO8601 | |
| contactsScanned | integer | All contacts scanned that day |
| conversationsEligible | integer | Contacts that passed eligibility filters |
| contactsSkippedNoConversation | integer | Zero-message or no-primary-thread contacts |
| contactsSkippedNoEmail | integer | Contacts lacking valid email |
| analysisFailedCount | integer | Per-contact analysis failures after retry |
| draftFailedCount | integer | Per-contact draft failures after retry |
| urgencyBreakdown | object | `hot`, `warm`, `cooling` counts |
| triggerBreakdown | object | `awaiting_our_response`, `no_reply`, `gone_cold` counts |
| draftsGenerated | integer | Follow-up drafts produced |
| estimatedCostUsd | number | Estimated Anthropic cost for the run |

**Warm storage rule:**
- `outputs/conversations/{contactId}.json` + `index.json`
- `outputs/conversation_analysis/{contactId}.json` + `index.json`
- `outputs/followups/{draftId}.json` + `index.json`
- `outputs/briefings/{YYYY-MM-DD}.json`

**Storage backend rule:**
- Local development defaults to `STORAGE_BACKEND=file`
- Deployed warm mode requires `STORAGE_BACKEND=postgres`
- Public storage APIs stay stable; implementation may swap file vs Postgres backends behind those interfaces
- Warm deployed mode must refuse startup if `WARM_ONLY_MODE=true` and `STORAGE_BACKEND=file`

---

## 5. SYSTEM ARCHITECTURE

### Two-Tier Model
```
Tier 1: Revenue Orchestrator (BRAIN)
  - Holds all business context from vault
  - Translates human goals → zero-ambiguity task specs
  - Dispatches to specialist agents (risk-tiered)
  - Never executes directly

Tier 2: Specialist Agents (WORKERS)
  - Receive ONLY their task spec + max 5 vault files
  - One agent, one task, one prompt
  - Execute to completion with no mid-task clarification
  - Output validated before human sees it
```

### Risk-Tiered Dispatch
```
CURRENT IMPLEMENTATION-READY CONTRACT → Separate top-level Claude Code sessions
  Applies to: document research, local synthesis, GHL-backed work, and deliverable-producing tasks
  Mechanism: Orchestrator writes task spec → human opens new session → /execute
  Why: One execution model is easier to verify, lock, audit, and validate than a mixed dispatch model

GHL-BACKED tasks (read or write) → Separate top-level Claude Code sessions
  Examples: Phase 0A MCP verification, GHL audit, lead triage, Pipeline Ops writes
  Mechanism: Orchestrator writes task spec → human opens new session → /execute
  Why: Maximum isolation, explicit lock ownership, maker-checker evidence, and no reliance on unverified MCP inheritance

DELIVERABLE-EXECUTION tasks (validated outputs for human review) → Separate top-level Claude Code sessions
  Examples: Campaign Craft drafts, any output entering the approval dashboard
  Mechanism: Same as GHL-BACKED — task spec → new session → /execute → separate /validate session
  Why: Deliverables require full maker-checker evidence trail (distinct `makerSessionId` and `validatorSessionId`) before reaching human reviewers. Separate sessions guarantee audit isolation even when no live integration is involved.

Deferred optimization:
  Sub-agent dispatch is intentionally OUT OF SCOPE for this PRD version.
  Reintroduce it only in a future PRD revision after runtime inheritance, locking semantics, and
  maker-checker implications are empirically verified and documented.
```

### Warm-First Operating Mode
```
Primary operator flow (pre-production):
  /briefing → /followups → approve/reject → /dispatch

Compatibility rule:
  GET / remains supported while the warm system is being introduced
  GET /briefing becomes the primary operator entrypoint in docs and training
  GET /cold-drafts may exist as an explicit cold view alias

Deployment sequence:
  local/private warm validation first
  Vercel hardening immediately after that validation passes
  cold outbound expansion only after the warm deployed path is stable
```

### Context Isolation Rules
```
Warm follow-up tasks may load ONLY:
  - compacted primary-thread conversation context
  - compliance/signature rules
  - minimal CTA/proof context when required for a truthful follow-up

Warm follow-up tasks may NOT load:
  - vault/playbook/email_angles.md
  - broad ICP scoring/playbook context
  - broader revenue intelligence context
  - autonomy policy context

Cold outbound and autonomy remain active roadmap items,
but they stay context-isolated from the warm MVP until their own phases start.
```

### Storage Backend Abstraction
```
Local development:
  STORAGE_BACKEND=file
  Human-readable JSON/Markdown remains the default local state model

Deployed warm mode:
  STORAGE_BACKEND=postgres
  Warm drafts, briefings, analyses, dedup hashes, rate limits, circuit breaker state,
  and dispatch logs must use the storage backend abstraction rather than assuming local files

Backend rule:
  Keep public storage APIs stable
  Swap FileStorageBackend vs PostgresStorageBackend behind those interfaces
```

### Warm-Only Deployed Mode
```
Default deployed posture:
  WARM_ONLY_MODE=true

Behavior:
  GET / redirects to /briefing
  Cold approval routes and /cold-drafts are hidden or return 404
  /dispatch and /dispatch/run operate on warm items only
  Nav prioritizes /briefing, /followups, and /dispatch

Local mixed mode may keep cold surfaces visible for compatibility and later Phase 4 work.
```

### Dashboard Access Control
```
Local mixed mode:
  DASHBOARD_AUTH_ENABLED=false is allowed

Deployed mode:
  HTTP Basic Auth is required
  All HTML and mutating dashboard routes require auth when enabled
  GET /healthz remains unauthenticated for deploy smoke checks
```

### Shared Send Safety
```
All GHL send paths share:
  - one GHL circuit breaker
  - one GHL daily send budget

Priority rule:
  Warm follow-up dispatch consumes shared GHL budget first.
  Cold GHL sends may use remaining budget only after warm work is satisfied.
```

### PIV Loop (Every Operation)
```
PLAN
  Human types goal OR scheduler fires
  Orchestrator: decomposes → task spec → context package → dispatch
       ↓
  [CONTEXT RESET — fresh session]
       ↓
IMPLEMENT
  Agent reads ONLY its task spec + listed vault files
  Executes to completion
  Produces output matching exact schema
       ↓
VALIDATE (fresh checker session)
  Gate 1: Structural Integrity
  Gate 2: Compliance
  Gate 3: Business Alignment
       ↓
METABOLIZE
  PASS → vault/feedback updated + recorded notification outcome
  FAIL → diagnose root cause → fix system → rerun (max 3x)
```

### Ralph Loop V2 (Failure Recovery)
```
Agent fails
  ↓ DO NOT rerun with same spec
Diagnose: which vault file wrong? which rule ambiguous?
  ↓
Adjust task spec OR vault file
  ↓
Rerun with fixed spec
  ↓ (max 3 attempts — tracked by `taskId` in `registry/failures.md`)
3rd failure → escalate to human → write to registry/escalations.md
Log pattern in vault/feedback/agent_learnings.md
```

**Retry counter rule**: The 3-attempt limit is global per `taskId`, tracked in `registry/failures.md`. `/execute` computes `attemptNumber = count(failures.md rows for taskId) + 1` before claiming a lock. If the next attempt would be `4`, it does not run — it escalates immediately. Every failure log row MUST include `Attempt #`. The orchestrator does NOT reset this counter; only Chris can reset it by creating a new `taskId`.

### Execution Preconditions
```
1. Maker-checker separation is mandatory
   - Execution session may create candidate output
   - A DIFFERENT fresh session must run final validation before completion
   - This is policy-enforced with recorded evidence: `/execute` writes `makerSessionId`, `/validate` writes `validatorSessionId`, and PASS requires them to differ

2. Session lock is mandatory for every active task
   - registry/active.md must record: `taskId`, `agent`, `goal`, `status`, `attemptNumber`, `lockOwner` (`makerSessionId`), and `leaseExpiresAt`
   - No second executor may start while a valid (non-expired) lock is active

3. Environment readiness is a hard gate
   - `GHL_API_KEY` and `GHL_LOCATION_ID` must exist before `.mcp.json` is considered usable
   - Missing optional Slack webhook may downgrade notifications to `SKIPPED_OPTIONAL`, but may not hide a failed run

4. Capability-first integrations
   - Task specs may reference ONLY verified tool names and fields recorded in vault/integrations/ghl.md
   - Never rely on assumed MCP methods

5. Edge-case policy must be explicit in every task spec
   - Zero-result behavior
   - Partial-data behavior
   - Fallback behavior
   - Null handling for allowed optional fields
   - Required gate dependencies

6. External writes and sends require preview-first execution
   - /execute may build a candidate payload or dry-run plan
   - Real external mutation happens only after validation PASS and any required human approval
   - No irreversible write may occur before guardrails are satisfied
```

---

## 6. IMPLEMENTATION PHASES

### Phase 0A — GHL MCP Read Capability Extension

**Goal:** Extend and verify the external `ghl-mcp/server.py` so the runtime can read the data required for a real GHL audit and lead triage.

**Deliverables:**
- External MCP entrypoint verified at `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`
- Live tool discovery captured in `revtry/vault/integrations/ghl.md`
- Required Phase 0A read tools verified live:
  - `ghl_list_contacts`
  - `ghl_list_opportunities`
  - `ghl_list_pipelines`
  - `ghl_list_custom_fields`
- Pagination, filter support, and output schema notes recorded for each required read tool
- Environment readiness gate passed for `GHL_API_KEY` and `GHL_LOCATION_ID`

**Acceptance Criteria:**
- [ ] Current tool baseline recorded: 14 existing tools from `server.py`
- [ ] Phase 0A read tools exist or equivalent live capabilities are verified and documented
- [ ] Contact reads are paginated and repeatable
- [ ] Pipeline and stage data are retrievable without manual export
- [ ] Custom field metadata is retrievable without guessing field names
- [ ] If any Phase 0A capability is missing, implementation stops with a logged blocker

### Phase 0B — Foundation + GHL Triage

**Goal:** Stand up the complete infrastructure (vault, guardrails, agents, slash commands, registry) and deliver the first hero outcome: a prioritized GHL follow-up list for Dani with a recorded notification outcome, validated through the 3-gate PIV loop. Phase 0B starts only after Phase 0A passes.

**Deliverables:**
- `CLAUDE.md` (project root `E:\Greenfield Coding Workflow\Project-RevTry\`, <250 lines, all 9 required sections)
- `.mcp.json` with verified GHL MCP connection
- 6 runtime slash commands created in `Project-RevTry/.claude/commands/`: `/prime`, `/plan-task`, `/execute`, `/validate`, `/metabolize`, `/status`
- Complete `revtry/` folder structure with every current-phase file populated
- Production-required vault files populated with real migrated content and freshness-dated
- Future-phase files, if created early, marked as formal phase-gated stubs only
- All guardrail files with binary-only rules (no judgment calls)
- 6 specialist agent configs (Recon, Enrichment, Segmentation, Campaign Craft, Pipeline Ops, Revenue Intel) × (config.md + output_schema.md) + Orchestrator (config.md + context_assembly.md + task_spec_template.md) + Quality Guard (config.md)
- Registry initialized: `active.md`, `completed.md`, `failures.md`, `escalations.md`, `phase_gates.md`, `locks/`, `memory/`
- GHL audit output: contact count, field inventory, pipeline stages, stale count, tag taxonomy, custom fields
- Triage criteria written into the named `Phase 0 Triage Criteria` section of `vault/integrations/ghl.md`
- Prioritized follow-up list delivered with explicit `notificationStatus` evidence (`SENT`, `SKIPPED_OPTIONAL`, `FAILED`, or `NOT_APPLICABLE`)

**Acceptance Criteria:**
- [ ] All items in Section 18 verification table pass
- [ ] `sessionId` format `{agent}-{yyyyMMdd-HHmmssfff}-{random4}` used in every active.md lock entry
- [ ] `completed.md` records both `makerSessionId` and `validatorSessionId`
- [ ] When `notificationStatus = SENT`, Slack notification format is `{"taskId": "...", "agent": "pipeline-ops", "summary": {"count": N, "top3": [...]}, "timestamp": "ISO8601", "outputPath": "revtry/outputs/TASK-ID_output.md"}`
- [ ] GHL MCP Python server starts without error
- [ ] Live tool discovery recorded in `vault/integrations/ghl.md` (not based on manifest)
- [ ] If ICP fields missing in GHL: GHL-native priority list returned (not invented scores)
- [ ] Hard block verified: `/execute` preflight rejects a synthetic task spec containing a prohibited operation intent before candidate output generation

### Phase 1 — Campaign Draft Pipeline + Approval Dashboard

**Goal:** Run the full Recon → Enrichment → Segmentation → Campaign Craft pipeline and deliver ICP-qualified campaign drafts to a local FastAPI approval dashboard for Dani's review.

**Deliverables:**
- Recon, Enrichment, Segmentation chain verified end-to-end through separate top-level execution sessions under the current runtime contract
- Campaign Craft producing Gate-validated drafts in a separate Claude Code session
- Local FastAPI dashboard at `http://localhost:8000`:
  - `GET /drafts` — list all PENDING campaign drafts (JSON array)
  - `GET /drafts/{draft_id}` — single draft with full HTML render
  - `POST /drafts/{draft_id}/approve` — mark APPROVED, record timestamp
  - `POST /drafts/{draft_id}/reject` — mark REJECTED with `{"note": "string"}` body
  - Local mixed mode may run without auth; deployed mode requires HTTP Basic Auth on all dashboard routes
- **Dashboard data flow:**
  - **Draft storage**: Validated drafts written to `revtry/outputs/drafts/DRAFT-YYYYMMDD-HHMM-N.json` (one JSON file per draft, matching Campaign Draft schema in Section 4)
  - **Draft index**: `revtry/outputs/drafts/index.json` — array of `{draft_id, contact_id, icp_tier, status, created_at, updated_at}`. Status: `PENDING | APPROVED | REJECTED`
  - **FastAPI reads**: Server reads `index.json` for list endpoints and individual draft files for detail endpoints. File system is the source of truth — no database.
  - **Approval/rejection writes**: `POST /approve` and `POST /reject` update `status` in `index.json` and append to a `decision_log` array in the draft file. Original draft content is never mutated.
  - **Concurrency safety**: To avoid lost-update conflicts between dashboard writes and agent writes, the FastAPI server SHOULD scan `revtry/outputs/drafts/*.json` for list endpoints and derive status from each file's internal `status` field, rather than relying on a shared `index.json`. If `index.json` is retained for performance, implement optimistic concurrency control (version number in the file; reject writes where version has changed since last read).
  - **Rejection → /metabolize**: On reject, server writes `{draft_id, note, timestamp}` to `revtry/registry/pending_feedback/`. Orchestrator must check `registry/pending_feedback/` and run `/metabolize` for all pending items before dispatching new Campaign Craft tasks.
- `/metabolize` processing rejection notes → `vault/feedback/campaign_performance.md`
- GUARD-004 auto-update of banned openers when `FEEDBACK_LOOP_POLICY_ENABLED=true`
- HeyReach account warmup initiated; start date recorded in `vault/integrations/heyreach.md`; Phase 2 LinkedIn dispatch gated on `warmup_start + 28 days`
- Full migration of legacy vault content to `revtry/vault/product/` and `revtry/vault/playbook/`

**Acceptance Criteria:**
- [ ] End-to-end pipeline produces ≥10 Tier 1 or Tier 2 qualified leads with complete score math
- [ ] Every draft in dashboard has passed all 3 Gates before appearing
- [ ] Dashboard renders subject, body, tier, and score for every draft
- [ ] Rejection notes appear in `vault/feedback/campaign_performance.md` before any new Campaign Craft task is dispatched (Orchestrator must check `registry/pending_feedback/` and run `/metabolize` for all pending items before creating new campaign tasks)
- [ ] No draft with enrichment_score <70 reaches Campaign Craft
- [ ] Legacy `vault/product/product_context.md` content split across all 5 product vault files

### Phase 2 — Outreach Dispatch Foundation

**Goal:** Establish the shared outbound safety infrastructure and manual dispatch behavior required by both warm and cold paths without widening the warm MVP unnecessarily.

**Deliverables:**
- Shared dispatch safety chain verified in this order: circuit breaker → rate limiter → dedup
- Manual dispatch path for approved sends with explicit `DISPATCHED` vs `SEND_FAILED` state handling
- GHL send budget + circuit breaker ready for warm priority routing
- Instantly/HeyReach integrations remain integration-ready but are not the current MVP acceptance gate
- Revenue Intel KPI snapshots available for red-flag monitoring, not yet the primary product surface

**Acceptance Criteria:**
- [ ] Any active send path runs circuit breaker → rate limiter → dedup before outbound API call
- [ ] Failed sends never become `DISPATCHED`; failure state is `SEND_FAILED`
- [ ] Circuit breaker trips on 3 consecutive failures and halts the affected integration
- [ ] Shared GHL send cap is enforced and logged
- [ ] Instantly and HeyReach remain disabled or manually gated until Phase 4

### Phase 3A — Conversation Reader + Data Models

**Goal:** Build the warm conversation ingestion layer and finalize the data contracts that every later warm component depends on.

**Deliverables:**
- `src/scripts/ghl_conversation_scanner.py` aligned to the final env contract
- `ConversationAnalysis`, `FollowUpDraft`, and `DailyBriefing` models finalized in `src/models/schemas.py`
- Separate warm storage domains defined for conversations, analysis, follow-ups, and briefings through the shared storage backend abstraction
- `src/models/__init__.py` exports updated to include all warm-phase models
- Canonical batch-size env set to `DAILY_SCAN_BATCH_SIZE`; `MAX_SCAN_CONTACTS` retained only as a deprecated transition alias

**Acceptance Criteria:**
- [ ] Only contacts with `totalMessages > 0`, valid email, and a deterministic primary thread are eligible downstream
- [ ] Contacts with manual outbound from configured sales team members (`SALES_TEAM_USER_IDS`) are tagged with an "Active Deal" badge in the dashboard and remain in the warm queue
- [ ] Zero-message and no-email contacts are skipped before any LLM call and counted in `DailyBriefing`; active-sales contacts are tagged, not excluded
- [ ] Primary-thread rule is deterministic: newest `lastMessageDate` wins
- [ ] Prompt compaction rule is fixed: latest 8 messages from the primary thread, reordered chronologically, trimmed before prompt assembly

### Phase 3B — Conversation Analyst

**Goal:** Classify warm conversation state cheaply and deterministically before any drafting work begins.

**Deliverables:**
- `src/integrations/anthropic_client.py` shared wrapper for retries, timeouts, JSON repair, and trace logging
- `src/agents/conversation_analyst_agent.py`
- `src/tests/test_anthropic_client.py`
- `src/tests/test_conversation_analyst.py`
- Deterministic trigger classification before LLM invocation (`awaiting_our_response`, `no_reply`, `gone_cold`)

**Acceptance Criteria:**
- [ ] Haiku is used only after deterministic trigger classification
- [ ] Invalid JSON gets one repair retry max; repeated failure records a per-contact analysis failure and continues the batch
- [ ] Failed analysis never auto-produces a draft
- [ ] One bad contact never fails the whole daily run

### Phase 3C — Follow-Up Draft Generation

**Goal:** Generate personalized warm follow-up drafts with separate storage and a validation profile that does not inherit cold-outbound assumptions.

**Deliverables:**
- `src/agents/followup_draft_agent.py`
- `src/dashboard/followup_storage.py`
- `src/validators/followup_gate2_validator.py`
- `src/validators/followup_gate3_validator.py`
- `src/tests/test_followup_draft_agent.py`
- `src/tests/test_followup_storage.py`
- `src/tests/test_followup_validators.py`

**Acceptance Criteria:**
- [ ] Every warm draft references the real prior conversation and fabricates nothing
- [ ] Subject <60 chars and body <150 words
- [ ] CTA is stage-aware; reply CTA is allowed and booking-link CTA is optional
- [ ] Warm validation profile does not enforce cold angle-tier mapping

### Phase 3D — Warm Review Dashboard

**Goal:** Give Dani a warm-first operator surface without breaking the current cold-draft dashboard entrypoint during the transition.

**Deliverables:**
- `GET /briefing` (supports `?date=YYYY-MM-DD`)
- `GET /followups` (supports `?date=YYYY-MM-DD`)
- `GET /followups/{id}`
- `POST /followups/{id}/approve`
- `POST /followups/{id}/reject`
- `POST /followups/batch/approve`
- `POST /followups/batch/reject`
- `POST /followups/generate`
- `src/dashboard/briefing_loader.py`
- `briefing.html`, `followup_list.html`, `followup_detail.html`
- `src/tests/test_briefing_loader.py`
- `GET /` remains backward-compatible; `GET /cold-drafts` may be added as an explicit alias

**Acceptance Criteria:**
- [ ] `/briefing` is the documented primary operator entrypoint
- [ ] `GET /` still renders the existing cold-draft page during the transition
- [ ] Approve/reject flow works for warm drafts
- [ ] Warm approval updates file-backed state only and does NOT create GHL tasks or upsert contacts

### Phase 3E — Warm Deploy-Readiness Hardening

**Goal:** Finish the local manual warm system and make it safe to deploy later by adding unified dispatch, auth, durable deployed persistence, idempotent generation, and business-date consistency.

**Deliverables:**
- `src/pipeline/followup_orchestrator.py`
- `src/pipeline/followup_dispatcher.py`
- `src/pipeline/scheduler.py`
- `src/tests/test_followup_orchestrator.py`
- `src/tests/test_followup_dispatcher.py`
- Shared GHL circuit breaker / rate limiter / dedup integration
- Manual generate → review → approve → dispatch flow
- Scheduler present but disabled by default
- Unified `GET /dispatch` + `POST /dispatch/run` warm-first operator flow
- HTTP Basic Auth for deployed dashboard access
- `GET /healthz` for deployment smoke checks
- Storage backend abstraction: file for local dev, Postgres for deployed warm mode
- Idempotent warm draft generation per `businessDate`
- Shared business-date helper using `America/Chicago`
- `GHLClient` fail-fast configuration errors on missing credentials
- `PHASE_3E_GENERATION_COMPLETE` and `PHASE_3E_DEPLOY_READY` gates tracked separately

**Acceptance Criteria:**
- [ ] Manual warm generate/review/approve/dispatch flow works end-to-end
- [ ] Scheduler cannot overlap runs; one daily run per date unless explicitly forced
- [ ] Warm follow-up dispatch consumes shared GHL budget before cold GHL sends
- [ ] Any failed send becomes `SEND_FAILED`, not `DISPATCHED`
- [ ] `POST /dispatch/run` dispatches warm first and returns a unified `{warm, cold, totals}` payload
- [ ] Deployed mode never exposes approve/reject/generate/dispatch routes without auth
- [ ] Deployed warm mode refuses file-backed persistence
- [ ] Same-day warm reruns overwrite the same draft; next-day reruns create a new draft
- [ ] Business-date logic is consistent with `America/Chicago`
- [ ] `PHASE_3E_DEPLOY_READY` passes before any Phase 3F work starts

### Phase 3F — Warm Dashboard Deployment to Vercel

**Goal:** Deploy the lean warm dashboard immediately after local/private validation so Dani can review and approve warm follow-ups remotely.

**Status (2026-03-10):** Dashboard deployed and accessible at `caio-rev-try.vercel.app`. Auth works, pages render. Code hardening is validated locally (DB timeout, healthz probe, remaining route error handling, candidate-source fallback). The remaining work is operational: run the warm pipeline against real GHL data, verify deployed routes with real data, and complete Dani verification.

**Deployment Architecture:**
- Entry point: `api/index.py` (Vercel serverless function, adds `src/` to sys.path)
- Config: `vercel.json` (routes `/(.*)`  to `api/index.py` via `@vercel/python` builder)
- Dependencies: root `requirements.txt` (installed by Vercel at build time)
- Auto-deploy: pushes to `origin/master` trigger Vercel auto-deploy via GitHub integration

**Deliverables:**
- [x] Vercel deployment configuration for the warm dashboard surface
- [x] Deployment env inventory and runtime path strategy for outputs/registry
- [x] DB connection hardening (connect_timeout, healthz DB probe)
- [x] Error handling for all routes (4 routes hardened with graceful fallback)
- [x] Candidate-source fallback from validated triage output to `outputs/ghl_followup_candidates.json`
- [ ] Pipeline data population (run orchestrator against real GHL data)
- [ ] Remote review/approval route verification with real data
- [ ] Deployment smoke-test checklist

**Acceptance Criteria:**
- [x] `PHASE_3E_DEPLOY_READY` is PASSED before deployment starts
- [x] `/briefing` and `/followups` render correctly in deployed mode
- [ ] `/briefing` and `/followups` show real data from pipeline execution
- [ ] Remote approve/reject actions work with real drafts
- [x] Deployed mode runs with HTTP Basic Auth, `WARM_ONLY_MODE=true`, and Postgres persistence
- [ ] No cold-flow dependency is required for the first deployed warm MVP
- [x] `GET /healthz` performs a real DB probe in postgres mode and returns `db=connected` or `status=degraded`

### Phase 3G — Agentic Engineering Enhancements

**Goal:** Improve warm pipeline measurement, validation quality, and developer workflow based on agentic engineering patterns. Full spec: `docs/superpowers/specs/2026-03-11-phase-3g-agentic-enhancements-spec.md`

**Deliverables:**
- Human edit-diff capture on follow-up draft edits
- Storage-derived pipeline metrics (6 new draft-lifecycle counts)
- Shadow confidence scoring on ConversationAnalysis (telemetry only)
- Output-only validation with evidence packets in `/validate`
- Prompt contracts with complexity gate in `/plan-task`
- Self-modifying candidate rules in `/metabolize` (shadow mode)
- Enhanced retry with gate failure context in warm orchestrator
- CLAUDE.md token audit for compaction resilience

**Acceptance Criteria:**
- [ ] Edit-diff field populated when Dani edits a draft
- [ ] KPI tracker outputs 6 new draft-lifecycle metrics
- [ ] ConversationAnalysis includes shadow confidence float (no behavioral changes)
- [ ] `/validate` enforces output-only review with evidence packets
- [ ] `/plan-task` complexity gate skips contracts for routine tasks
- [ ] `/metabolize` produces candidate rules in shadow mode
- [ ] All existing tests pass with no regressions

### Phase 4 — Cold-Outbound Expansion

**Goal:** Reactivate cold outbound as a separate tested operator surface after the warm deployed path is stable.

**Deliverables:**
- Instantly cold-email flow reactivated intentionally
- HeyReach LinkedIn flow reactivated intentionally
- Cold dashboard routes/documentation made explicit rather than inherited from the warm path
- Separate cold context assembly retained; no warm-context leakage

**Acceptance Criteria:**
- [ ] Cold email dispatches ONLY via Instantly
- [ ] Warm email dispatches ONLY via GHL
- [ ] Shared GHL breaker/budget behavior remains intact when cold work is reintroduced
- [ ] Cold operator flow is tested independently of the warm flow

### Phase 5 — Revenue Intelligence + Autonomy Graduation

**Goal:** Layer analytics, KPI reporting, and autonomy graduation on top of validated warm and cold outbound paths.

**Deliverables:**
- Revenue Intel agent producing KPI reports and dashboards
- Autonomy graduation policy activation using validated outbound history
- `/metabolize` fully compounding across warm + cold execution history

**Acceptance Criteria:**
- [ ] Revenue Intel reports include warm + cold operational metrics over a defined date range
- [ ] Graduation to Supervised requires validated KPI history plus Chris approval
- [ ] Graduation to Full Autonomy requires sustained KPI history plus Chris + Dani approval
- [ ] `vault/feedback/agent_learnings.md` continues compounding across later phases

---

## 7. OUT OF SCOPE

### Never in scope (any phase)
- Self-learning or reinforcement learning (rule-based only; all rules live in versioned vault files)
- Monolithic pipeline (no tightly-coupled agent stages; context isolation always enforced)
- Any agent approving its own output (maker-checker is a hard architectural constraint)
- Any GHL write without a preceding read
- GHL DELETE, BULK_DELETE, export_all_contacts, mass_unsubscribe (blocked forever by Quality Guard)
- Multi-tenant support
- AI/ML model training
- General-purpose database redesign outside the warm deploy-readiness storage backend abstraction
- Mobile app or public-facing API

### Not in scope until Phase 1
- Campaign draft generation
- Apollo/BetterContact/Clay enrichment integration
- Instantly, HeyReach integration
- FastAPI approval dashboard

### Not in scope until Phase 2
- Any outbound sends (email or LinkedIn)
- Dispatch rate enforcement
- Circuit breaker activation

### Not in scope until Phase 3
- Warm conversation scanning, Anthropic-backed analysis, and follow-up drafting
- Warm briefing dashboard routes
- Warm follow-up orchestrator and scheduler

### Not in scope until Phase 3F
- Vercel deployment
- Remote approval workflow for the warm dashboard

### Not in scope until Phase 4
- Cold-outbound expansion to Instantly + HeyReach as an active operator surface
- Cold-context reactivation inside the dashboard

### Not in scope until Phase 5
- Revenue Intel KPI reporting as the primary product surface
- Autonomy graduation

---

## 8. SUCCESS CRITERIA

Overall project is complete when ALL of the following pass:

- [ ] Phase 0: All 33 verification checks pass (Section 18 table) with zero failures
- [x] Phase 0: GHL audit completed, triage criteria approved, notification outcome recorded
- [ ] Phase 1: ≥10 ICP-qualified campaign drafts produced, validated through 3 gates, and reviewed by Dani in the approval dashboard
- [ ] Phase 2: shared dispatch safety chain verified; failed sends recorded as `SEND_FAILED`; circuit breaker tested and verified
- [ ] Phase 3: daily warm briefing generated, reviewed, and manually dispatched through shared GHL safety rails
- [ ] Phase 3F: Vercel warm dashboard live and accessible without relying on the local server
- [ ] Phase 4: cold outbound reactivated as a separate tested surface without polluting the warm operator flow
- [ ] Phase 5: Revenue Intel reporting live and autonomy graduation criteria met
- [ ] Zero instances of mock data in any validated output (across all phases)
- [ ] Zero instances of an agent self-approving output (maker-checker always different sessions)
- [ ] `vault/feedback/agent_learnings.md` has entries from every completed phase
- [ ] `registry/escalations.md` has zero unresolved escalations at project close

---

## 9. RISKS & MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GHL MCP Python server fails to start (import errors, missing deps) | High | Blocks Phase 0A | Run `python -m py_compile` then `python server.py`. If imports fail: install explicit packages from `server.py` (`mcp`, `aiohttp`, `python-dotenv`). If entrypoint missing: log blocker, stop, escalate to Chris. |
| GHL live tool discovery returns fewer tools than documented (manifest inconsistency known) | High | Changes Phase 0 task specs | Treat live discovery as only source of truth. Write verified tool names to `vault/integrations/ghl.md` before any task spec references them. |
| GHL read capabilities needed for audit are missing from the external MCP | High | Blocks Hero Outcome 1 completely | Phase 0A extends the MCP first. No audit or triage run starts until paginated contact reads, pipeline/stage reads, and custom field metadata are verified. |
| GHL contacts lack ICP-scorable fields (company size, revenue, industry) | Medium | Phase 0 triage fallback required | Use Phase 0 fallback: GHL-native priority list using only verified fields (dateLastActivity, open opportunity, tags, valid email). Full ICP scoring deferred until enrichment live. |
| Enrichment waterfall returns null for majority of leads | Medium | Phase 1 pipeline stalls | Pipeline Ops reports enrichment_score distribution in audit. If >50% score <70 after full waterfall, escalate to Chris before Campaign Craft runs. |
| Anthropic API unavailable, rate-limited, or returns invalid JSON during warm runs | Medium | Phase 3 batch quality degraded | Shared `anthropic_client.py` wrapper handles timeout/retry/one repair retry. Record per-contact failure and continue the batch. |
| Warm path pulls cold-outbound context and bloats prompts | Medium | Degraded follow-up quality + higher cost | Warm context isolation is a hard rule: no `email_angles.md`, no broad ICP/campaign playbook context unless later phase explicitly requires it. |
| Vercel deployment cannot access runtime outputs/registry paths safely | Medium | Blocks Phase 3F remote dashboard | Define deployment env inventory and path strategy before deployment; Phase 3F starts only after local/private warm validation is complete. |
| Instantly warmup not complete when Phase 4 starts | Medium | Cannot dispatch cold email at full scale | Keep cold expansion in Phase 4. Use reduced-rate reactivation until warmup and domain readiness are verified. |
| Dani rejection rate >80% in Phase 1 | Medium | Delays Phase 2 | /metabolize diagnoses per rejection. If 3+ rejections share same root cause, update vault file + rerun. Escalate to Chris if no improvement after 2 batch cycles. |
| Legacy vault files missing key business content | High | Agents have no accurate context | Phase 0 migration mapping mandatory before any vault file is written. Source files preserved until migration verified. Chris reviews migration output before any agent task runs. |
| SLACK_WEBHOOK_URL not configured | Low | Notifications silently fail | System degrades gracefully — triage output still written to `revtry/outputs/`. `/status` command reports notification state. Warning only, not a blocker. |

---

## 10. COMPLETE FILE STRUCTURE

Build every folder and every file listed. Production-required files must contain real content. Future-phase files may exist as formal phase-gated stubs only. Do not leave stray `TODO`, `TBD`, or unlabeled placeholder text.

```
E:/Greenfield Coding Workflow/Project-RevTry/
├── CLAUDE.md                              ← Global config (<250 lines, always loaded)
├── .mcp.json                             ← GHL MCP server configuration
├── .claude/
│   └── commands/                         ← Real slash commands (invoke with /name)
│       ├── prime.md
│       ├── plan-task.md
│       ├── execute.md
│       ├── validate.md
│       ├── metabolize.md
│       └── status.md
│
└── revtry/
    ├── migration/
    │   └── legacy_inventory.md
    │
    ├── README.md
    │
    ├── vault/
    │   ├── README.md
    │   ├── icp/
    │   │   ├── tier_definitions.md
    │   │   ├── scoring_rules.md
    │   │   ├── disqualification.md
    │   │   └── target_companies.md
    │   ├── product/
    │   │   ├── offers.md
    │   │   ├── positioning.md
    │   │   ├── pricing.md
    │   │   ├── proof_points.md
    │   │   └── cta_library.md
    │   ├── playbook/
    │   │   ├── email_angles.md
    │   │   ├── sequences.md
    │   │   ├── objections.md
    │   │   └── signatures.md
    │   ├── compliance/
    │   │   ├── exclusions.md
    │   │   ├── domain_rules.md
    │   │   └── rate_limits.md
    │   ├── feedback/
    │   │   ├── campaign_performance.md
    │   │   ├── win_loss_patterns.md
    │   │   └── agent_learnings.md
    │   └── integrations/
    │       ├── ghl.md
    │       ├── instantly.md
    │       ├── heyreach.md
    │       ├── apollo.md
    │       ├── bettercontact.md          ← Phase-gated stub (Phase 1)
    │       └── clay.md                   ← Phase-gated stub (Phase 1)
    │
    ├── agents/
    │   ├── README.md
    │   ├── orchestrator/
    │   │   ├── config.md
    │   │   ├── context_assembly.md
    │   │   └── task_spec_template.md
    │   ├── recon/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   ├── enrichment/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   ├── segmentation/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   ├── campaign-craft/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   ├── conversation-analyst/
    │   │   ├── config.md                ← Phase-gated stub until Phase 3B
    │   │   └── output_schema.md         ← Phase-gated stub until Phase 3B
    │   ├── followup-draft/
    │   │   ├── config.md                ← Phase-gated stub until Phase 3C
    │   │   └── output_schema.md         ← Phase-gated stub until Phase 3C
    │   ├── pipeline-ops/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   ├── revenue-intel/
    │   │   ├── config.md
    │   │   └── output_schema.md
    │   └── quality-guard/
    │       └── config.md
    │
    ├── guardrails/
    │   ├── README.md
    │   ├── gate1_structural.md
    │   ├── gate2_compliance.md
    │   ├── gate3_alignment.md
    │   ├── hard_blocks.md
    │   ├── quality_guards.md
    │   ├── deliverability.md
    │   ├── rejection_memory.md
    │   ├── dedup_rules.md
    │   ├── circuit_breaker.md
    │   ├── autonomy_graduation.md
    │   └── escalation.md
    │
    ├── registry/
    │   ├── active.md
    │   ├── completed.md
    │   ├── failures.md
    │   ├── escalations.md
    │   ├── phase_gates.md               ← Phase completion status (checked by /execute)
    │   ├── locks/                       ← Atomic lock files for task execution
    │   ├── pending_feedback/            ← Dani's rejection notes (Phase 1+)
    │   └── tasks/
    │
    ├── outputs/
    │   ├── drafts/                      ← Campaign draft JSON files + index (Phase 1+)
    │   ├── conversations/               ← Warm conversation summaries + index (Phase 3A+)
    │   ├── conversation_analysis/       ← Warm analysis outputs + index (Phase 3B+)
    │   ├── followups/                   ← Warm follow-up draft JSON files + index (Phase 3C+)
    │   └── briefings/                   ← Daily warm briefing files (Phase 3D+)
    │
    └── memory/
        ├── operations_log.md
        └── learnings.md
```

---

## 11. FILE SPECIFICATIONS

### 11.1 `CLAUDE.md` (Workspace Root — ALWAYS LOADED)

Rules: Under 250 lines. No implementation details. Links to revtry/ for details.

**Runtime note:** This file specifies the active project-root `Project-RevTry/CLAUDE.md`.

**Required sections:**
1. Project Context (3 lines max)
2. Team (Chris Daigle + Dani Apgar roles)
3. Mandatory Session Start (`Run /prime`)
4. The 5 Laws (condensed — 1 line each)
5. Dispatch Rules (all implementation-ready runtime work executes in fresh top-level sessions; sub-agent optimization deferred)
6. Progressive Disclosure (conditions → vault files)
7. Hard Blocks Quick Reference (link to `revtry/guardrails/hard_blocks.md`)
8. Escalation Protocol
9. Anti-Patterns (never-do list)

**The 5 Laws (include verbatim):**
- Law 1: Same model + better context > better model + worse context. The vault IS the system.
- Law 2: 70% effort in planning. 30% in execution. If execution fails, fix the plan.
- Law 3: Bad output → diagnose root cause → fix the SYSTEM → rerun. Never patch output manually.
- Law 4: Each agent has only what it needs. One agent, one task, one prompt.
- Law 5: Wins reinforce vault. Failures update rules. Every cycle earns more autonomy.

**Anti-Patterns (include verbatim):**
- Never carry conversation history into an execution session
- Never give an agent vault files it doesn't need for THIS task
- Never fix bad agent output manually — scrap and rerun
- Never mock data in validation
- Never run `bulk_delete`, `export_all_contacts`, or `mass_unsubscribe`
- Never send cold email via GHL (warm only)
- Never send warm email via Instantly (cold only)
- Never approve your own output (maker-checker separation)

**Progressive Disclosure rules:**
```
When working on GHL operations → read revtry/vault/integrations/ghl.md
When working on outreach → read revtry/vault/playbook/email_angles.md + signatures.md + revtry/vault/product/positioning.md + proof_points.md + cta_library.md
When working on warm follow-up → read revtry/vault/playbook/signatures.md + revtry/vault/compliance/domain_rules.md + revtry/vault/compliance/exclusions.md + revtry/vault/product/proof_points.md + revtry/vault/product/cta_library.md
When working on lead scoring → read revtry/vault/icp/tier_definitions.md + scoring_rules.md
When validating any output → read revtry/guardrails/gate1_structural.md + gate2_compliance.md + gate3_alignment.md
When a task fails → read revtry/registry/failures.md before diagnosis
```

### 11.2 `.mcp.json` (Workspace Root)

```json
{
  "mcpServers": {
    "ghl": {
      "command": "python",
      "args": ["E:\\Greenfield Coding Workflow\\Project-RevTry\\mcp-servers\\ghl-mcp\\server.py"],
      "env": {
        "GHL_API_KEY": "${GHL_API_KEY}",
        "GHL_LOCATION_ID": "${GHL_LOCATION_ID}"
      }
    }
  }
}
```

**Runtime note:** Verify Python can start the server, required environment variables are present, and runtime dependencies are installed in Claude Code's environment before Phase 0A starts. PowerShell is the canonical shell for all examples in this PRD.

### 11.3 Slash Commands (`.claude/commands/`)

These six files are runtime slash commands in `Project-RevTry/.claude/commands/`.

#### `/prime` — `prime.md`

```markdown
# /prime — Session Startup

Read these files IN ORDER:
1. CLAUDE.md
2. revtry/README.md
3. revtry/registry/active.md
4. revtry/registry/failures.md (last 3 entries)
5. revtry/memory/operations_log.md (last 5 entries)
6. revtry/vault/README.md

Output a status report:
- Active tasks: `taskId`, `agent`, `goal`, time elapsed (if any)
- Last completed task + outcome
- Any failures requiring attention
- Any vault files with stale freshness dates
- Recommended next action

SELF-VALIDATE:
Confirm all 6 files were read. If any file missing, report it — do NOT fabricate content.
Do not proceed without completing this startup sequence.
```

#### `/plan-task` — `plan-task.md`

```markdown
# /plan-task — Task Decomposition

Given a goal (from argument or recent conversation):

STEP 1: If goal is ambiguous → ask 3-5 clarifying questions (multiple choice preferred).
STEP 2: Identify which specialist agent handles this.
STEP 3: Apply INCLUSION TEST to vault files:
  For each candidate vault file ask: "If the agent doesn't have this, will it make a wrong decision?"
  YES = include. NO = exclude. MAXIMUM 5 files in context package.
STEP 4: Write task spec using the zero-ambiguity template (all 9 sections — see revtry/agents/orchestrator/task_spec_template.md), including normalized `Operation Intents`, `Notification Policy`, and `Required Phase Gates`.
STEP 5: Review: does any field allow the agent to infer or assume? Fix before saving.
STEP 6: Read revtry/guardrails/hard_blocks.md and lint the task spec's `Operation Intents` against prohibited operations.
  If a prohibited intent is present → STOP. Do NOT save the spec. Escalate the blocked request to Chris.
STEP 7: Generate `taskId` in the format `TASK-YYYYMMDD-HHmmssfff-RAND4` and save to revtry/registry/tasks/TASK-[YYYYMMDD-HHmmssfff-RAND4].md
STEP 8: Do NOT claim an active lock here. `/execute` owns revtry/registry/active.md at run time.

SELF-VALIDATE before saving:
- [ ] All 9 task spec sections populated (no blanks, no "TBD")
- [ ] Goal statement is binary (testable yes/no)
- [ ] Context package ≤5 vault files with inclusion rationale for each
- [ ] `Operation Intents` are normalized and complete for the requested work
- [ ] All validation criteria are binary pass/fail (no "approximately" or "seems correct")
- [ ] MAY/MAY NOT scope boundaries explicitly defined
- [ ] `Notification Policy` is one of: `required`, `best_effort`, `not_applicable`
- [ ] `Required Phase Gates` explicitly lists every prerequisite gate needed at execution time
- [ ] Failure protocol includes max 3 retry rule
- [ ] Output schema is exact JSON with field types
- [ ] Hard-block lint passed before saving the task spec

FEEDBACK LOOP: After task completes, /metabolize updates this command if spec patterns cause recurring failures.
```

#### `/execute` — `execute.md`

```markdown
# /execute — Task Execution + Hard-Block Preflight

USAGE: /execute revtry/registry/tasks/TASK-XXX.md

This command runs in a FRESH Claude Code session.
Do NOT carry prior conversation history into execution.

STEP 0: Verify the provided task spec file path exists. If missing, report the exact missing path and STOP. Do not proceed.
STEP 1: Read task spec from the provided path.
STEP 1A: Read the task spec's `Required Phase Gates` list and check revtry/registry/phase_gates.md.
  If any required phase gate is missing or not `PASSED`, STOP and report the unmet prerequisite.
STEP 2: Read revtry/guardrails/hard_blocks.md and compare the task spec's normalized `Operation Intents` against prohibited operations.
  If any prohibited intent is present:
  - STOP before execution, lock claim, or candidate generation
  - Log the blocked attempt to revtry/memory/operations_log.md
  - Record a `BLOCKED_HARD_RULE` row in revtry/registry/active.md with blank lock/lease fields
  - Escalate to Chris with the exact prohibited intent(s)
STEP 3: Compute `attemptNumber = count(revtry/registry/failures.md rows for taskId) + 1`.
  If `attemptNumber = 4` → STOP and escalate immediately. Do NOT create a 4th run.
STEP 4: Check revtry/registry/active.md for an existing unexpired lock on this task.
  If lock exists and is owned by another session → STOP. Report duplicate execution attempt.
  If lock is expired → check whether revtry/outputs/[TASK-ID]_candidate.md was modified within the last 30 minutes. If yes, refuse reclaim (the original session may still be active). If no, delete the stale `revtry/registry/locks/[TASK-ID].lock` file, log a `LEASE_RECLAIM` event in memory/operations_log.md, and continue.
  If no valid lock exists → claim lock atomically:
  a. Create `revtry/registry/locks/[TASK-ID].lock` file. If file already exists, STOP (another session is racing).
  b. Generate `makerSessionId` in PowerShell:
  ```powershell
  $suffix = -join ((65..90) + (97..122) | Get-Random -Count 4 | % {[char]$_})
  $makerSessionId = "{0}-{1}-{2}" -f $agent, (Get-Date -Format 'yyyyMMdd-HHmmssfff'), $suffix
  ```
  c. Write JSON to `revtry/registry/locks/[TASK-ID].lock`:
  ```json
  {"taskId":"[TASK-ID]","sessionId":"[maker-session-id]","agent":"[agent]","acquiredAt":"ISO8601","leaseExpiresAt":"ISO8601","lastHeartbeatAt":"ISO8601"}
  ```
  d. Record `taskId`, `attemptNumber`, `makerSessionId`, `lockOwner`, `leaseExpiresAt`, and `notificationPolicy` in `active.md`.
  e. **Lease heartbeat**: During execution, update BOTH `leaseExpiresAt` in `active.md` and `leaseExpiresAt` / `lastHeartbeatAt` in the `.lock` file every 30 minutes to prevent expiry on long-running tasks.
STEP 5: Load ONLY the vault files listed in the task spec's Context Package section.
  DO NOT read additional vault files. DO NOT explore beyond what's listed.
STEP 6: Load agent rules: revtry/agents/[agent-name]/config.md
STEP 7: Execute the task, working to full completion.
STEP 8: Produce output matching the EXACT schema in task spec Section 4.
STEP 9: Save candidate output to: revtry/outputs/[TASK-ID]_candidate.md

IN-SESSION PRECHECK (maker-side only):
9a. Read revtry/guardrails/gate1_structural.md → run Gate 1 checks only
9b. If Gate 1 FAILS:
  - DO NOT run Gate 2 or Gate 3
  - Log to `revtry/registry/failures.md`: {taskId, attemptNumber, gateFailed, specificReason, timestamp}
  - Keep candidate output only if useful for diagnosis; never present as approved output
  - Report FAIL to human with `rootCauseHypothesis`
9c. If Gate 1 PASSES:
  - Update active.md status to AWAITING_VALIDATION
  - STOP and require a DIFFERENT fresh session to run:
    /validate revtry/outputs/[TASK-ID]_candidate.md revtry/registry/tasks/TASK-XXX.md

FINAL VALIDATION, completion, Slack, and /metabolize do NOT happen in the maker session.

SELF-VALIDATE (meta check — run before submitting):
- [ ] I ran `/execute` hard-block preflight before lock claim or candidate generation
- [ ] No prohibited `Operation Intents` were present in the task spec
- [ ] I read ONLY the files listed in the task spec context package
- [ ] I computed `attemptNumber` from `failures.md` and refused a 4th attempt
- [ ] I claimed or verified the task lock before executing
- [ ] I recorded `makerSessionId`, `notificationPolicy`, and lease expiry in `active.md`
- [ ] I created or refreshed the `.lock` file heartbeat alongside active.md
- [ ] Output schema matches task spec Section 4 exactly (field names, types, nesting)
- [ ] I ran Gate 1 only in-session as a structural precheck and did NOT self-approve the output
- [ ] No data was mocked or fabricated (all from real sources)
- [ ] Trace log is complete: `taskId` + `agent` + `timestamp` + `vaultFilesUsed`
```

#### `/validate` — `validate.md`

```markdown
# /validate — Manual Validation

USAGE: /validate [output-path] [task-spec-path]

This command MUST run in a DIFFERENT fresh session from the one that created the candidate output.

0. Verify both provided file paths exist. If either is missing, report the exact missing path and STOP.
1. Read task spec validation criteria from [task-spec-path]
2. Read candidate output from [output-path]
3. Read `active.md` or `completed.md` record for the task and generate `validatorSessionId` in PowerShell:

```powershell
$suffix = -join ((65..90) + (97..122) | Get-Random -Count 4 | % {[char]$_})
$validatorSessionId = "{0}-{1}-{2}" -f "quality-guard", (Get-Date -Format 'yyyyMMdd-HHmmssfff'), $suffix
```

4. Compare `validatorSessionId` to `makerSessionId`. If they match, FAIL immediately. Maker-checker is policy-enforced with recorded evidence.
5. For each gate, load the gate file PLUS any vault files explicitly referenced inside that gate
6. Run Gate 1 (revtry/guardrails/gate1_structural.md)
7. If Gate 1 PASS → run Gate 2 (revtry/guardrails/gate2_compliance.md)
8. If Gate 2 PASS → run Gate 3 (revtry/guardrails/gate3_alignment.md)
9. Output verdict:

{
  "verdict": "PASS|FAIL",
  "gateResults": {"gate1": "PASS|FAIL", "gate2": "PASS|FAIL", "gate3": "PASS|FAIL"},
  "failureReason": "string|null",
  "violations": ["specific violation 1"],
  "recommendation": "PROCEED|RERUN|ESCALATE",
  "notificationStatus": "SENT|SKIPPED_OPTIONAL|FAILED|NOT_APPLICABLE"
}

IF PASS:
- Resolve notification handling from the task spec's `Notification Policy`:
  - `not_applicable` → final `notificationStatus = NOT_APPLICABLE`
  - `best_effort` + missing `SLACK_WEBHOOK_URL` → final `notificationStatus = SKIPPED_OPTIONAL`
  - `required` + missing `SLACK_WEBHOOK_URL` → FAIL validation
- If policy requires or permits a webhook send and `SLACK_WEBHOOK_URL` is set, attempt Slack delivery with retry (3 attempts, exponential backoff: 1s, 3s, 9s) using PowerShell:
  ```powershell
  if ($env:SLACK_WEBHOOK_URL) {
    $body = @{
      taskId = "[TASK-ID]"
      agent = "[agent]"
      summary = @{ count = 0; top_3 = @() }
      timestamp = (Get-Date).ToString("o")
      outputPath = "revtry/outputs/[TASK-ID]_output.md"
    } | ConvertTo-Json -Depth 5
    Invoke-RestMethod -Method Post -Uri $env:SLACK_WEBHOOK_URL -ContentType 'application/json' -Body $body | Out-Null
  }
  ```
  For triage tasks, build the JSON body from the validated candidate payload already loaded in memory so it includes `count` and `top3` without depending on a not-yet-promoted file.
- Finalize `notificationStatus` after the send attempt (after all retries exhausted):
  - successful send → `SENT`
  - any send failure + `required` → FAIL validation
  - any send failure + `best_effort` → `FAILED` (task may still PASS)
- Promote candidate file: COPY `_candidate.md` to `revtry/outputs/[TASK-ID]_output.md` (do NOT rename). Delete `_candidate.md` only AFTER `completed.md` is updated successfully.
- Update `revtry/registry/active.md` → move task to `revtry/registry/completed.md`, recording `makerSessionId`, `validatorSessionId`, `notificationPolicy`, and final `notificationStatus`
- Delete `revtry/registry/locks/[TASK-ID].lock` after the completed row is written successfully.
- Do NOT update vault capability docs directly in `/validate`
- Run /metabolize (invoke as a slash command in this same session)

IF FAIL:
- Do NOT patch the candidate output manually
- Log to `revtry/registry/failures.md`: `attemptNumber` + `gateFailed` + `specificReason` + `rootCauseHypothesis`
- Update active.md status to FAILED_VALIDATION
- Delete `revtry/registry/locks/[TASK-ID].lock` so a later corrected attempt can claim a fresh lock

SELF-VALIDATE:
- All applicable gates ran in sequence
- All gate dependency files referenced by the guardrails were loaded
- `makerSessionId` and `validatorSessionId` are both recorded and are different
- `notificationStatus` is recorded and matches the task spec policy
- `notificationPolicy` is preserved in `completed.md`
- Violations are specific (not generic "failed")
```

#### `/metabolize` — `metabolize.md`

```markdown
# /metabolize — Outcome Processing

Auto-called by /validate on PASS. Call manually after failure diagnosis.

PERMISSION SCOPE: /metabolize writes to vault/feedback/ files on PASS. For `task_type = capability_audit`, PASS additionally allows writes to `revtry/vault/integrations/ghl.md` only. When invoked by /validate (Quality Guard session), it inherits Orchestrator-level write access for those paths only. On FAIL diagnosis, /metabolize may additionally update any vault file, agent config, or skill file as a system-evolution action — this elevated write scope is logged in memory/learnings.md with the specific file changed and rationale. Quality Guard cannot write to vault/ outside of /metabolize execution.

READ: revtry/registry/tasks/[task-id].md + validation verdict

IF PASS:
1. Identify what made this successful (which vault files most useful?)
2. Log to vault/feedback/agent_learnings.md:
   {taskId, agent, pattern, whatWorked, vaultFilesUsed, date}
3. If outreach task → update vault/feedback/campaign_performance.md
4. If `task_type = capability_audit` → update `revtry/vault/integrations/ghl.md` with:
   - verified existing tools
   - required Phase 0A tools and any remaining gaps
   - parameter support and pagination notes
   - the named `Phase 0 Triage Criteria` section as `Status: DRAFT` unless explicit human approval metadata is already present
5. Update revtry/memory/operations_log.md
6. Registry transitions happen in /validate, not here

IF FAIL:
Diagnose root cause using this hierarchy:
  a. Vault file wrong/outdated? → update vault file + log change
  b. Task spec ambiguous? → update task spec template
  c. Agent went out of scope? → update agent config.md
  d. Context package too broad? → narrow inclusion criteria
  e. Skill definition incomplete? → update the skill file
Log to revtry/registry/failures.md:
  {taskId, attemptNumber, failureReason, rootCauseCategory, fixApplied, date}
After 3rd attempt on same task → write to revtry/registry/escalations.md

SYSTEM EVOLUTION RULE: If the same root cause category appears in 3 different tasks →
  update the relevant system file (vault, agent config, or skill) + log in memory/learnings.md

GUARD-004 FEEDBACK (if FEEDBACK_LOOP_POLICY_ENABLED=true):
If rejection_note contains an opener pattern matching ≥2 rejections → add to banned openers in vault/playbook/signatures.md

SELF-VALIDATE: `rootCause` identified (not "unknown"). Fix logged with specific action taken.
```

#### `/status` — `status.md`

```markdown
# /status — System State Snapshot

Read:
1. revtry/registry/active.md
2. revtry/registry/completed.md (last 10 entries)
3. revtry/registry/failures.md (last 5 entries)
4. revtry/memory/operations_log.md (last 5 entries)

Output formatted report (readable in 30 seconds):
- Active tasks: count + [`taskId` | `agent` | `goal` | elapsed time]
- Last 24h completions: count + brief outcomes
- Last 24h failures: count + brief reasons + root cause categories
- System alerts: stale vault files | stuck tasks (>2h) | pending escalations
- Vault freshness: list any vault files past Valid Through date
- Notification status: SLACK_WEBHOOK_URL configured? Y/N

SELF-VALIDATE: All 4 files read. No fabricated data. All dates accurate.
```

---

## 12. VAULT FILE SPECIFICATIONS

### Vault File Template (Every File Must Follow This)

```markdown
# [Topic]
Last Updated: YYYY-MM-DD | Valid Through: YYYY-MM-DD | Source: [origin]
Applies To: [agent-name(s)]

## Purpose
[One sentence: what question does this file answer for the agent?]

## Rules
| Rule | Condition | Action | Example ✅ | Counter-example ❌ |
|------|-----------|--------|-----------|-------------------|

## Do NOT Apply This File To
[What this file is NOT for — explicit out-of-scope]

## Review Trigger
[What event would make this file need updating?]
```

### Migration Rule

1. Record every source file and its destination in `revtry/migration/legacy_inventory.md`
2. If one source file splits across multiple destinations, list every destination explicitly
3. No legacy source file may be deleted until destination files exist, contain migrated content, and pass freshness review

### Production-Required Files vs Phase-Gated Stubs

- Production-required files for the active phase must contain real content before execution.
- Future-phase files may exist early only as formal phase-gated stubs.
- Every phase-gated stub MUST include these fields:
  - `Status`
  - `Phase`
  - `Owner`
  - `Why deferred`
  - `Review trigger`
- Placeholder scans must fail on stray `TODO`, `TBD`, unlabeled placeholder text, or fake content in production-required files.
- Placeholder scans may ignore formal phase-gated stubs outside the active phase.

### 7 Laws for Writing Vault Files

1. **Zero Implied Knowledge**: Never assume the agent knows anything about the business. State everything explicitly.
2. **Binary Over Nuanced**: ALWAYS/NEVER over judgment calls. `Score ≥80 = qualified` not `"seems like a good fit"`
3. **Examples for Every Rule**: One correct + one incorrect example per rule
4. **Out-of-Scope Explicit**: Every vault file states what it does NOT cover
5. **Freshness Metadata**: Last Updated, Valid Through, Review Trigger — required on every file
6. **Machine-Parseable**: Tables, bullets, headers. Minimal prose paragraphs.
7. **Conflict Resolution**: If two rules could conflict, define priority: `compliance > scoring`

### 12.1 `vault/compliance/exclusions.md`

**Purpose**: Complete list of blocked domains and emails. Checked before ANY outreach.

**Blocked Domains (ALL contacts from these 7 domains are blocked forever):**
- jbcco.com, frazerbilt.com, immatics.com, debconstruction.com, credegroup.com, verifiedcredentials.com, exitmomentum.com

**Blocked Individual Emails (27 contacts):**
chudziak@jbcco.com, hkephart@frazerbilt.com, jmusil@jbcco.com, imorris@jbcco.com,
mdabler@jbcco.com, maria.martinezcisnado@immatics.com, mm@immatics.com,
slee@debconstruction.com, bzupan@jbcco.com, mfolsom@jbcco.com,
kelsey.irvin@credegroup.com, michael.loveridge@credegroup.com, amejia@debconstruction.com,
kjacinto@debconstruction.com, lagriffin@frazerbilt.com, aneblett@verifiedcredentials.com,
tek@debconstruction.com, wmitchell@frazerbilt.com, cole@exitmomentum.com,
alex.wagas@credegroup.com, avali@debconstruction.com, jnavarro@jbcco.com,
kvale@frazerbilt.com, phirve@frazerbilt.com, mkcole@frazerbilt.com,
tschaaf@jbcco.com, sharrell@frazerbilt.com

### 12.2 `vault/icp/tier_definitions.md`

**Purpose**: Defines title buckets, industry buckets, company-fit ranges, and multipliers. Does NOT define arithmetic scoring (that lives in `scoring_rules.md`).

**Title Buckets:**
- **Tier 1**: CEO, Founder, President, COO, Owner, Managing Partner
- **Tier 2**: CTO, CIO, Chief of Staff, VP Operations, VP Strategy, VP Innovation, Managing Director
- **Tier 3**: Director Ops, Director IT, Director Strategy, VP Engineering, Head of AI, Head of Data
- **Manager**: Operations Manager, IT Manager, Project Manager, General Manager (any title containing "Manager" that does not match a higher tier)
- **Unmatched**: Any title not matching Tier 1, 2, 3, or Manager buckets → scored as 0 points

**Industry Tiers:**
- **Tier 1**: Agencies, Staffing, Consulting, Law/CPA, Real Estate, E-commerce
- **Tier 2**: B2B SaaS, IT Services, Healthcare, Financial Services
- **Tier 3**: Manufacturing, Logistics, Construction, Home Services

**Company Fit:**
- Sweet spot: 101-250 employees
- Acceptable: 51-100 or 251-500 employees
- Review required: 10-50 or 501-1000 employees

**Multipliers:**
- Tier 1 industry/title fit → `1.5x`
- Tier 2 → `1.2x`
- Tier 3 → `1.0x`
- Unmatched industry → `0.8x` (penalizes unknown industries below Tier 3 baseline)

**Disqualification handoff:** If ANY disqualification rule matches, STOP scoring and mark `DISQUALIFIED`.

**Note on `vault/icp/target_companies.md`**: Phase-gated stub for Phase 0. Populated during Phase 1 Recon with discovered target account lists and ideal company profiles. Content specification deferred to Phase 1 plan.

### 12.3 `vault/icp/scoring_rules.md`

**Purpose**: Deterministic arithmetic for ICP scoring. Use with `tier_definitions.md` and `disqualification.md`.

**Calculation Order (mandatory):**
1. Check `disqualification.md`. If any rule matches → `DISQUALIFIED`
2. Calculate `base_score` (0-100)
3. Apply `industry_multiplier`
4. Calculate `icp_score = round(base_score * multiplier, 1)`
5. Assign tier from `icp_score`

**Base Score Components:**

| Component | Max Points | Logic |
|-----------|-----------|-------|
| Company Size | 20 | 101-250=20, 51-100=15, 251-500=15, 10-50=10, 501-1000=10 |
| Title Match | 25 | Tier 1=25, Tier 2=22, Tier 3=18, Manager=12, unmatched=0 |
| Industry Match | 20 | Tier 1=20, Tier 2=15, Tier 3=10, unmatched=0 |
| Revenue Fit | 15 | $10M-$50M=15, $5M-$10M=12, $50M-$100M=12, $1M-$5M=8, >$100M=8, <$1M=0, unknown=0 |
| Tech Signal | 10 | Active AI hiring=10, AI tools adopted=7, no signal=0 |
| Engagement Signal | 10 | Website visit=10, content download=7, social engagement=5, none=0 |

**Tier Thresholds (use comparison operators — no ambiguity):**
- Tier 1 QUALIFIED: `icp_score >= 80.0`
- Tier 2 QUALIFIED: `60.0 <= icp_score < 80.0`
- Tier 3 QUALIFIED: `40.0 <= icp_score < 60.0`
- Disqualified: `icp_score < 40.0` OR any disqualification rule match

**Worked Example (mandatory — include verbatim in vault file):**
CEO at consulting firm, 150 employees, $25M revenue
- Size: 20, Title: 25, Industry: 20, Revenue: 15, Tech: 0, Engagement: 0
- base_score = 80 | multiplier = 1.5 | icp_score = 120.0 → **Tier 1 QUALIFIED**

### 12.4 `vault/icp/disqualification.md`

| Disqualifier | Condition | Action |
|-------------|-----------|--------|
| Too small | <10 employees | BLOCK |
| Too large | >1,000 employees | BLOCK |
| Government | Industry = Government | BLOCK |
| Non-profit | Industry = Non-profit | BLOCK |
| Education | Industry = Education/Academia | BLOCK |
| Current customer | In GHL with "Customer" tag | BLOCK |
| Competitor | Known competitor domain | BLOCK |
| Blocked domain | In exclusions.md domain list | BLOCK |
| Blocked email | In exclusions.md email list | BLOCK |

### 12.5 `vault/compliance/domain_rules.md`

| Message Type | Platform | Rule |
|-------------|----------|------|
| Cold outreach email | **Instantly V2 ONLY** | 6 warmed domains |
| Warm/nurture email | **GHL ONLY** | chiefai.ai domain |
| LinkedIn outreach | **HeyReach ONLY** | T1/T2/T3 campaigns |
| Revival email | **Instantly ONLY** | Warm domains |
| NEVER cold via GHL | NEVER warm via Instantly | Violation = domain reputation destroyed |

### 12.6 `vault/compliance/rate_limits.md`

| Channel | Daily Cap | Monthly Cap | Hourly Cap | Notes |
|---------|-----------|-------------|------------|-------|
| Cold email (Instantly) | 25 (all domains) | — | — | Ramp: start at 5/day |
| GHL email | 150 | 3,000 | 20/domain | |
| LinkedIn (HeyReach) | 5→20 | — | — | 4-week warmup required |
| Revival email | 5 | — | — | |
| Apollo API | — | — | 200 req/hr | |
| GHL API | — | — | 60 req/min | |

### 12.7 `vault/integrations/ghl.md`

**Purpose**: Everything Pipeline Ops needs to interact with GHL via MCP.

**MCP Server**: Loaded via `.mcp.json`
**Entrypoint**: `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`

**Tool verification rule**: The file is authoritative ONLY AFTER live tool discovery records exact method names, pagination behavior, filter support, and response schemas. No task spec may reference an assumed tool name or field.

**Verified Existing Tools (current external server baseline = 14 tools):**
1. `ghl_create_contact`
2. `ghl_update_contact`
3. `ghl_get_contact`
4. `ghl_add_tag`
5. `ghl_create_opportunity`
6. `ghl_trigger_workflow`
7. `ghl_bulk_create_contacts`
8. `ghl_get_calendars`
9. `ghl_get_free_slots`
10. `ghl_create_appointment`
11. `ghl_update_appointment`
12. `ghl_get_appointment`
13. `ghl_delete_calendar_event`
14. `ghl_get_calendar_events`

**Required Phase 0A Tools (must be live before audit/triage):**
- `ghl_list_contacts`
  - Input: `page`, `page_limit`, optional `query`
  - Output: `contacts[]`, `page`, `page_limit`, `has_more`, `next_page`, `total_count|null`
- `ghl_list_opportunities`
  - Input: `page`, `page_limit`, optional `pipeline_id`
  - Output: `opportunities[]`, `page`, `page_limit`, `has_more`, `next_page`, `total_count|null`
- `ghl_list_pipelines`
  - Input: none
  - Output: `pipelines[]` with nested `stages[]`
- `ghl_list_custom_fields`
  - Input: `object_type = contact|opportunity`
  - Output: `fields[]`

**Derived capability rule:** Tag inventory may be derived from paginated contact reads. A dedicated `ghl_list_tags` tool is optional unless live testing proves it is required.

**Tool verification procedure:**
1. Start the external server from `server.py`
2. Run live tool discovery through Claude Code
3. Record for each tool: exact name, required params, optional params, pagination behavior, filters supported, and response shape
4. Record which capabilities are verified, missing, or partially supported
5. Treat the live discovery output as higher priority than both this PRD and `manifest.json`

**Task 3B live discovery protocol (mandatory):**
1. Chris launches a fresh Claude Code session from an env-ready PowerShell shell in `E:\Greenfield Coding Workflow\Project-RevTry\`
2. Run `/prime`
3. Confirm the live observed tool inventory matches the expected 18-tool set
4. Verify read tools first:
   - `ghl_list_pipelines`
   - `ghl_list_custom_fields` (`object_type=contact`)
   - `ghl_list_custom_fields` (`object_type=opportunity`)
   - `ghl_list_contacts`
   - `ghl_list_opportunities`
   - `ghl_get_contact`
   - `ghl_get_calendars`
   - `ghl_get_free_slots`
   - `ghl_get_calendar_events`
5. Verify write-capable tools second using only designated safe smoke assets:
   - `ghl_create_contact`
   - `ghl_update_contact`
   - `ghl_add_tag`
   - `ghl_bulk_create_contacts`
   - `ghl_create_opportunity`
   - `ghl_trigger_workflow`
   - `ghl_create_appointment`
   - `ghl_get_appointment`
   - `ghl_update_appointment`
   - `ghl_delete_calendar_event`
   - `ghl_update_contact` smoke verification may touch only `firstName`, `lastName`, or `companyName`
   - `ghl_create_contact` and `ghl_bulk_create_contacts` smoke verification may not include tag payloads; `ghl_add_tag` is the only permitted tag mutation test
6. Record exact schemas, pagination notes, filter behavior, and sample response keys in `ghl.md`
7. PASS only if all 18 tools are callable and all write-capable tools are verified against safe smoke assets
8. If safe smoke assets are missing or unsafe, PAUSE Task 3B and keep `PHASE_0A_MCP_VERIFIED_LIVE` closed

**Required `ghl.md` evidence subsection name:** `## Task 3B Live MCP Verification`

Required fields inside that subsection:
- `Run Date`
- `Operator`
- `Env Ready`
- `Expected Tool Count`
- `Observed Tool Count`

Required tool matrix columns:
- `Tool`
- `Category`
- `Sample Input Summary`
- `Result`
- `Response Keys Confirmed`
- `Pagination / Filter Notes`
- `Asset Used`
- `Notes`

**If any required read capability is missing:** Hero Outcome 1 is BLOCKED. Log blocker to `revtry/registry/escalations.md`. Do not fake the audit.

**Provisional-state rule:** Any preexisting audit-style inventory, capability notes, or triage criteria already present in `ghl.md` are provisional until the maker-checker Phase 0 audit flow completes. `ghl.md` content alone is not sufficient to treat `PHASE_0_AUDIT_PASSED` or `PHASE_0_TRIAGE_CRITERIA_APPROVED` as passed.

**Critical Contact Fields:**
- `id`, `email`, `firstName`, `lastName`, `phone`, `companyName`
- `tags` — array of strings (check for "Customer", "Competitor" tags)
- `dateLastActivity` — KEY FOR TRIAGE
- `source`, `dateUpdated`, `customFields`

**Safe Read Operations (Phase 0A/0B):** verified list/read tools, `ghl_get_contact`, `ghl_get_calendar_events`

**Safe Write Operations (Phase 1+):** `ghl_update_contact` (safe non-tag fields only), `ghl_add_tag`, `ghl_create_appointment`, `ghl_trigger_workflow`

**Tag-safety rule:** All tag writes are add-only. `ghl_add_tag` is the only permitted tag mutation tool. Generic contact upsert/update payloads may not include `tags`, `tagIds`, or clear/remove semantics.

**Generic contact write allowlist:** `firstName`, `lastName`, `companyName`

**HARD BLOCKED (NEVER):** `DELETE_CONTACT`, `BULK_DELETE`, mass field updates >10 contacts without human approval, any write without preceding read, `ghl_bulk_create_contacts` without Quality Guard pre-approval, tag removal, tag replacement, tag-clear operations, generic contact writes that include `tags` / `tagIds`, generic contact writes that touch blocked fields outside the allowlist

**One-time audited tag recovery procedure:** If an audit-confirmed incident proves tags were removed incorrectly, recovery must use a generated incident manifest sourced from the audit file, a read-only dry-run diff against current contact state, additive-only `ghl_add_tag` writes for missing tags only, and a post-restore verification pass proving every affected contact's current tags are a superset of the incident manifest tags. Recovery may not use generic contact update/upsert paths.

**Named section required in the runtime file:** `## Phase 0 Triage Criteria`
- Required schema:
  - `Status: DRAFT | APPROVED | DEFERRED`
  - `Approved By: Chris + Dani | null`
  - `Approved At: ISO8601 | null`
  - `Criteria Rules`
  - `Review Notes`
- `/metabolize` may populate audit facts and draft criteria only
- Pipeline Ops may read triage criteria ONLY from this named section and ONLY when `Status = APPROVED`
- `DRAFT`, `DEFERRED`, or a missing section all block triage; Pipeline Ops must STOP rather than invent criteria

### 12.8 `vault/playbook/signatures.md`

**Sender Identity:**
```
Dani Apgar
Head of Sales, Chief AI Officer
```

**CAN-SPAM Footer (include verbatim in every email):**
```
Reply STOP to unsubscribe.
Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705
```

**Booking Link:** `https://caio.cx/ai-exec-briefing-call`

**Banned Openers (GUARD-004 static list):**
- "Hope this finds you well"
- "I wanted to reach out"
- "Are you open to"
- "I came across your profile"
- "Just checking in"
- "I hope you're doing well"
- "I noticed"
- "Quick question"

**Subject Line Rules:** ≤60 characters | No ALL CAPS words | ≤1 exclamation mark | No spam triggers: free, guarantee, urgent, act now, limited time, winner, no obligation, buy now

### 12.9 `vault/playbook/email_angles.md`

**Purpose**: Defines the available outreach angles, their tier applicability, and selection rules. The Orchestrator MUST specify an angle from this list in every Campaign Craft task spec. Campaign Craft MUST STOP if the angle is not specified.

**Angle Definitions:**

| Angle ID | Name | Applicable Tiers | Description | When to Use |
|----------|------|-----------------|-------------|-------------|
| `ai_executive_briefing` | AI Executive Briefing | Tier 1 | CEO/Founder-level — strategic AI transformation, competitive advantage, board-level ROI | C-suite titles, high-revenue companies |
| `operational_efficiency` | Operational Efficiency | Tier 1, Tier 2 | Process automation, team productivity, cost reduction via AI workflows | Operations/Strategy VPs, Directors |
| `tech_modernization` | Tech Modernization | Tier 2, Tier 3 | AI stack adoption, integration with existing systems, technical ROI | CTO/CIO/VP Engineering, IT Directors |
| `competitive_edge` | Competitive Edge | Tier 1, Tier 2 | Industry-specific AI use cases, competitor analysis, market positioning | Any tier where industry context is strong |
| `quick_win` | Quick Win | Tier 2, Tier 3 | Low-lift AI pilots, 30-day results, minimal disruption | Mid-level decision makers, skeptical prospects |

**Tier-to-Angle Mapping Rule:**
- Tier 1 leads: Use `ai_executive_briefing` or `competitive_edge` (default: `ai_executive_briefing`)
- Tier 2 leads: Use `operational_efficiency`, `tech_modernization`, or `competitive_edge` (default: `operational_efficiency`)
- Tier 3 leads: Use `tech_modernization` or `quick_win` (default: `quick_win`)

**Gate 3 validation**: Email angle must match the lead's tier per this mapping. A Tier 1 lead receiving a `quick_win` angle → FAIL.

**Do NOT Apply This File To**: Warm follow-up drafts (Phase 3 uses conversation-grounded follow-up rules, not cold angle selection). LinkedIn outreach (HeyReach has its own message templates). Revival emails (use separate revival angle rules when defined in Phase 4).

**Note on `vault/playbook/objections.md` and `vault/playbook/sequences.md`**: Phase-gated stubs for Phase 0. Content to be migrated from legacy playbook files during Phase 1. Both are Campaign Craft task-specific add-ons (never in minimum context package). Add to migration mapping in `revtry/migration/legacy_inventory.md` when source material is identified.

---

## 13. AGENT SPECIFICATIONS

### Agent Permission Matrix

| Agent | Read Vault | Write Vault | GHL Read | GHL Write | Sends | Approves |
|-------|-----------|------------|----------|-----------|-------|---------|
| Orchestrator | Full | feedback/ only | No direct access | No | No | Delegates |
| Recon | icp/ + compliance/exclusions.md + integrations/apollo.md | No | No | No | No | No |
| Enrichment | integrations/ only | No | No | No | No | No |
| Segmentation | icp/ only | No | No | No | No | No |
| Campaign Craft | playbook/ + product/ + compliance/ | No | No | No | No | No |
| Conversation Analyst | compliance/ + product/ (minimal) | No | No | No | No | No |
| Follow-Up Draft | playbook/signatures.md + product/ (minimal) + compliance/ | No | No | No | No | No |
| Pipeline Ops | integrations/ghl.md | No | YES | YES (safe ops only) | No | No |
| Revenue Intel | All (read-only) | No | YES (read) | No | No | No |
| Quality Guard | guardrails/ + task spec + candidate output | feedback/ only (via /metabolize) | No | No | No | YES (validation only) |

### 13.1 Orchestrator — `agents/orchestrator/config.md`

**Session type**: Human opens Claude Code, runs `/prime`, types goal.

**Dispatch decision tree:**
```
Goal arrives
  ↓ Write task spec → human opens new session → /execute
  ↓ Does this task depend on another task's output?
  YES → Define dependency. Task B waits for Task A's completed output.
  NO  → Dispatch immediately
  ↓ Is there already an active unexpired task for this agent?
  YES → Wait (max 3-4 parallel sessions per RAM constraints)
  NO  → Dispatch
```

**Escalation triggers (always notify human):**
- 3rd consecutive failure on same task
- KPI red flag metrics triggered
- Vault conflict detected (two rules contradict)
- Task requires scope beyond current agent definitions
- Any GHL write above "safe" threshold

### 13.2 Recon Agent — `agents/recon/config.md`

**Purpose**: Lead discovery from external sources
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Context package**: vault/icp/tier_definitions.md + vault/icp/scoring_rules.md + vault/icp/disqualification.md + vault/compliance/exclusions.md + vault/integrations/apollo.md (5 vault files — agents/recon/config.md is the agent config, not counted toward the 5-file vault limit)

**Data source**: Apollo API (people search endpoint). Recon DISCOVERS new leads by querying Apollo with ICP-derived filters (title keywords, industry, company size range). This is distinct from the Enrichment agent, which FILLS GAPS on already-known leads. Apollo API rate limit (200 req/hr) applies to Recon queries.

**Recon → Enrichment handoff**: Recon outputs scored candidate records with fields populated from Apollo search results. Enrichment then receives these records and runs the full waterfall (Apollo detail lookup → BetterContact → Clay) to fill remaining null fields and compute enrichment_score. A contact appearing in both Recon's search results and Enrichment's detail lookup is expected — the two operations serve different purposes (discovery vs. gap-filling).

**Score authority rule**: Recon's ICP score is preliminary (based on Apollo search data only). Segmentation's ICP score is authoritative (based on enriched data). Recon's preliminary score is used for discovery filtering only and is NOT carried forward to downstream agents. Gate 3 validates only the Segmentation-produced score.

**Field naming convention**: All machine-readable JSON payloads in this PRD use camelCase matching the GHL-native Contact data model (e.g., `firstName`, `companyName`, `companySize`). Markdown table headers may remain human-readable. Never use snake_case in JSON field names.

**Output schema** (`agents/recon/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "recon",
  "timestamp": "ISO8601",
  "records": [{
    "firstName": "string (required)",
    "lastName": "string (required)",
    "title": "string (required)",
    "companyName": "string (required)",
    "email": "string (required)",
    "linkedinUrl": "string (required)",
    "companySize": "integer (required)",
    "industry": "string (required)",
    "icpTier": "1|2|3 (required)",
    "baseScore": "integer 0-100 (required)",
    "industryMultiplier": "number (required)",
    "icpScore": "number 0-150 (required)",
    "whyThisScore": "string (required)",
    "scoreBreakdown": "string (required — show math)"
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "exclusionsChecked": true,
    "disqualificationApplied": true,
    "recordsFoundBeforeFilter": "integer",
    "recordsExcluded": "integer",
    "recordsDisqualifiedCount": "integer"
  }
}
```

### 13.3 Enrichment Agent — `agents/enrichment/config.md`

**Purpose**: Fill data gaps via waterfall
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Waterfall order**: Apollo → BetterContact → Clay

**Timeout specifications:**
- Per-request timeout: Apollo=30s, BetterContact=45s, Clay=60s
- Per-step timeout: 10 minutes total per waterfall step across all records in the batch
- On timeout: treat as `MISS` for that step and proceed to the next waterfall step. Log the timeout event in the trace `waterfall_trace` field.

**Data source distinction**: Enrichment receives already-discovered leads (from Recon output or GHL contact list). It does NOT discover new leads. Its Apollo calls are detail/enrichment lookups on known contacts, not search queries for new prospects.

**Null email rule**: If `email = null` after completing the full waterfall (all three steps return MISS for email), the lead is automatically DISQUALIFIED for outreach. No Campaign Craft task may include a lead with null email.

**Quality thresholds:**
- 90-100: READY
- 70-89: PARTIAL (acceptable for outreach)
- 50-69: MINIMAL (flag — do not pass to Campaign Craft)
- <50: REJECT

**Anti-mocking rule (verbatim):**
> If a field is unavailable after completing the full waterfall, set field = null.
> Enrichment score reflects the gap honestly. DO NOT fabricate data. DO NOT estimate. Null is correct.

**Output schema** (`agents/enrichment/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "enrichment",
  "timestamp": "ISO8601",
  "records": [{
    "contactId": "string (required — FK to source record)",
    "email": "string|null",
    "title": "string|null",
    "companyName": "string|null",
    "companySize": "integer|null",
    "industry": "string|null",
    "revenue": "string|null",
    "linkedinUrl": "string|null",
    "enrichmentScore": "integer 0-100 (required)",
    "enrichmentGrade": "READY|PARTIAL|MINIMAL|REJECT (required)",
    "fieldsFilled": "integer (required)",
    "fieldsTotal": "integer (required)",
    "waterfallTrace": {
      "apollo": "HIT|MISS|SKIPPED",
      "bettercontact": "HIT|MISS|SKIPPED",
      "clay": "HIT|MISS|SKIPPED"
    }
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "recordsReceived": "integer",
    "recordsReady": "integer (enrichmentScore 90-100)",
    "recordsPartial": "integer (enrichmentScore 70-89)",
    "recordsMinimal": "integer (enrichmentScore 50-69)",
    "recordsRejected": "integer (enrichmentScore <50)"
  }
}
```

### 13.4 Segmentation Agent — `agents/segmentation/config.md`

**Purpose**: ICP scoring + tier assignment with full reasoning
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Context**: vault/icp/tier_definitions.md + vault/icp/scoring_rules.md + vault/icp/disqualification.md + vault/compliance/exclusions.md

**Mandatory output per record:**
- Normalized title + industry tier
- base_score + multiplier + icp_score
- Complete math shown
- "Why This Score" in plain language
- Tier assignment with rubric citation
- Disqualification flags if any apply

**Output schema** (`agents/segmentation/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "segmentation",
  "timestamp": "ISO8601",
  "records": [{
    "contactId": "string (required — FK to enriched record)",
    "normalizedTitle": "string (required)",
    "normalizedIndustry": "string (required)",
    "titleTier": "1|2|3|unmatched (required)",
    "industryTier": "1|2|3|unmatched (required)",
    "baseScore": "integer 0-100 (required)",
    "industryMultiplier": "number (required — from tier_definitions.md)",
    "icpScore": "number 0-150 (required)",
    "scoreBreakdown": "string (required — show full math)",
    "whyThisScore": "string (required — plain language)",
    "icpTier": "1|2|3|DISQUALIFIED (required)",
    "disqualificationReason": "string|null (required if DISQUALIFIED)",
    "rubricCitation": "string (required — which scoring_rules.md rule applied)"
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "recordsReceived": "integer",
    "tier1Count": "integer",
    "tier2Count": "integer",
    "tier3Count": "integer",
    "disqualifiedCount": "integer",
    "disqualificationApplied": true,
    "exclusionsChecked": true
  }
}
```

### 13.5 Campaign Craft Agent — `agents/campaign-craft/config.md`

**Purpose**: Draft cold/outbound campaign content (email, LinkedIn, sequences)
**Runtime**: Separate Claude Code session (execution)
**Session type justification**: Campaign Craft produces DELIVERABLE outputs (campaign drafts for Dani's approval dashboard) that require full 3-gate maker-checker validation with distinct session IDs. Per Section 5 Risk-Tiered Dispatch, deliverable-execution tasks use separate top-level sessions for maker-checker evidence. Campaign Craft qualifies under the "deliverable execution" criterion — it has no GHL permissions and needs no live integration access.
**Minimum context**: vault/playbook/email_angles.md + vault/playbook/signatures.md + vault/product/positioning.md + vault/product/proof_points.md + vault/product/cta_library.md
**Task-specific add-ons**: sequences.md, objections.md, or exclusions.md only when task requires them. Never exceed 5 vault files.

**Scope boundary**: Campaign Craft is the cold/outbound drafting surface. It is NOT reused for warm follow-up. Warm follow-up uses the separate Follow-Up Draft agent and may not inherit cold angle logic.

**If angle not specified in task spec → STOP. Report to orchestrator. Never guess.**

**Required in every email (Gate 2 checklist):**
1. Specific subject line (no "[TBD]")
2. Personalized opener (specific to lead/company/industry — nothing from banned list)
3. Body with specific pain point (not generic AI pitch)
4. Single clear CTA
5. Booking link: `https://caio.cx/ai-exec-briefing-call`
6. Signature: Dani Apgar, Head of Sales, Chief AI Officer
7. CAN-SPAM footer from vault/playbook/signatures.md

**Output schema** (`agents/campaign-craft/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "campaign-craft",
  "timestamp": "ISO8601",
  "drafts": [{
    "draftId": "string",
    "contactId": "string",
    "icpTier": "1|2|3",
    "angleId": "string",
    "subject": "string",
    "body": "string",
    "channel": "instantly|ghl|heyreach",
    "bookingLink": "https://caio.cx/ai-exec-briefing-call",
    "status": "PENDING",
    "trace": {
      "leadSignalsUsed": ["array"],
      "proofPointsUsed": ["array"],
      "ctaId": "string"
    }
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "angleSource": "string",
    "signaturesApplied": true,
    "complianceChecksPrepared": true
  }
}
```

### 13.6 Pipeline Ops Agent — `agents/pipeline-ops/config.md`

**Purpose**: GHL CRM operations — read contacts, triage, safe writes
**Runtime**: Top-level Claude Code session for all current PRD tasks. Sub-agent dispatch is deferred to a future PRD revision.
**Context**: vault/integrations/ghl.md + agents/pipeline-ops/config.md

**Phase 0 First Task — GHL Audit (read-only):**
1. Total contact count
2. Which contact fields are actually populated (vs. consistently empty)
3. Pipeline stages that exist in this GHL account
4. Distribution of `dateLastActivity` (contacts stale >30 days)
5. Opportunity stage distribution
6. Tag taxonomy (all tags + contact count per tag)
7. Custom fields in use
8. Verified capability matrix (which MCP tools actually work with which filters)

**Phase 0 dependencies (hard requirement):**
- `vault/integrations/ghl.md` must confirm the required Phase 0A tools are live
- Audit and triage task specs must declare only approved `Operation Intents`
- No Phase 0 task may assume sub-agent MCP access or an alternate execution path

**Output schema — Pipeline Ops** (`agents/pipeline-ops/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "pipeline-ops",
  "taskType": "capability_audit|triage",
  "timestamp": "ISO8601",
  "audit": {
    "totalContacts": "integer",
    "fieldInventory": {"fieldName": "populatedCount"},
    "pipelineStages": [{"pipelineId": "string", "pipelineName": "string", "stages": [{"id": "string", "name": "string"}]}],
    "staleContacts30d": "integer",
    "opportunityStageDistribution": {"stageName": "integer"},
    "tagTaxonomy": {"tagName": "integer"},
    "customFields": [{"key": "string", "label": "string", "type": "string"}],
    "capabilityMatrix": {"toolName": {"verified": "boolean", "pagination": "boolean", "filters": ["string"]}}
  },
  "triage": {
    "prioritizedContacts": [{"contactId": "string", "firstName": "string", "lastName": "string", "email": "string", "priorityRank": "integer", "priorityReason": "string"}],
    "count": "integer",
    "criteriaSource": "Phase 0 Triage Criteria section of vault/integrations/ghl.md",
    "criteriaStatus": "APPROVED",
    "fallbackUsed": "boolean"
  },
  "trace": {
    "vaultFilesUsed": ["array"],
    "toolsCalled": ["array"],
    "pagesFetched": "integer"
  }
}
```
Note: For audit tasks, `triage` is null. For triage tasks, `audit` is null. Combined audit+triage tasks are forbidden in the current PRD because Phase 0 triage must wait for human approval of the audit-derived criteria.

**Phase 0 triage fallback (mandatory):**
- If GHL lacks ICP-scorable fields: produce GHL-native priority list using only verified fields (dateLastActivity, open opportunity status, tags, owner, valid email presence)
- Full ICP scoring starts only after enrichment is live OR required fields confirmed in GHL
- If the audit shows required list/read capabilities are missing: STOP and escalate instead of fabricating an audit or partial triage

### 13.7 Conversation Analyst — `agents/conversation-analyst/config.md`

**Purpose**: Analyze warm conversation context before any drafting work happens
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Input**: Compact primary-thread context only — not full thread sprawl
**Model**: Claude Haiku via shared `src/integrations/anthropic_client.py`
**Allowed context**: `vault/playbook/signatures.md` + `vault/compliance/domain_rules.md` + `vault/compliance/exclusions.md` + minimal product proof/CTA context when needed

**Hard rules:**
- Deterministic trigger classification runs before the LLM call
- Only the selected primary thread is analyzed in v1
- Latest 8 messages from that primary thread are used, reordered chronologically
- One JSON repair retry max; repeated failure records a per-contact analysis failure and continues the batch
- Failed analysis must not auto-produce a draft

**Output schema** (`agents/conversation-analyst/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "conversation-analyst",
  "timestamp": "ISO8601",
  "analyses": [{
    "contactId": "string",
    "sourceConversationId": "string",
    "trigger": "no_reply|awaiting_our_response|gone_cold",
    "triggerReason": "string",
    "sentiment": "positive|neutral|negative|cold",
    "stage": "new|engaged|stalled|won|lost",
    "urgency": "hot|warm|cooling",
    "summary": "string",
    "keyTopics": ["array"],
    "recommendedAction": "string"
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "contactsReceived": "integer",
    "contactsAnalyzed": "integer",
    "analysisFailures": "integer",
    "model": "claude-haiku-4-5-20251001"
  }
}
```

### 13.8 Follow-Up Draft Agent — `agents/followup-draft/config.md`

**Purpose**: Generate personalized warm follow-up drafts grounded in the actual prior conversation
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Model**: Claude Sonnet via shared `src/integrations/anthropic_client.py`
**Input**: `ConversationAnalysis` + compacted primary-thread context + minimal signature/compliance/product context

**Hard rules:**
- Explicitly reference the real prior conversation
- No fabricated facts, fake recap, or invented meeting history
- No banned openers from `vault/playbook/signatures.md`
- Subject <60 chars; body <150 words
- CTA is stage-aware: reply CTA allowed; booking-link CTA optional, not mandatory
- One JSON repair retry max; repeated failure records a per-contact draft failure and continues the batch

**Output schema** (`agents/followup-draft/output_schema.md`):
```json
{
  "taskId": "string",
  "agent": "followup-draft",
  "timestamp": "ISO8601",
  "drafts": [{
    "draftId": "string",
    "contactId": "string",
    "sourceConversationId": "string",
    "businessDate": "YYYY-MM-DD",
    "generationRunId": "string",
    "trigger": "no_reply|awaiting_our_response|gone_cold",
    "urgency": "hot|warm|cooling",
    "sentiment": "positive|neutral|negative|cold",
    "stage": "new|engaged|stalled|won|lost",
    "subject": "string",
    "body": "string",
    "channel": "ghl",
    "status": "PENDING",
    "analysisSummary": "string",
    "trace": {
      "ctaId": "string|null",
      "proofPointsUsed": ["array"],
      "conversationFactsUsed": ["array"]
    }
  }],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "draftsGenerated": "integer",
    "draftFailures": "integer",
    "model": "claude-sonnet-4-6"
  }
}
```

### 13.9 Revenue Intel Agent — `agents/revenue-intel/config.md`

**Purpose**: Analytics, performance reporting, trend detection
**Runtime**: Separate top-level Claude Code session under the current implementation-ready contract
**Hard block**: Cannot write to ANY system. All output goes to `revtry/outputs/` only.
**Output schema**: Phase-gated stub — full specification deferred to Phase 5. Phase 0 creates `agents/revenue-intel/output_schema.md` as a formal phase-gated stub with fields: Status=STUB, Phase=5, Owner=Chris, Why deferred=Revenue Intel not active until Phase 5, Review trigger=Phase 4 completion.

### 13.10 Quality Guard — `agents/quality-guard/config.md`

**Purpose**: 3-gate validation used by `/validate`
**Runtime**: Fresh checker session — NEVER the same session that created the candidate output.

**Profile selection rule:**
- Cold campaign drafts use the existing campaign Gate 2 / Gate 3 profile
- Warm follow-up drafts use a dedicated follow-up Gate 2 / Gate 3 profile
- Gate 1 remains structural for both

**Gate vault dependencies (load before running each gate):**
- Gate 1: No vault dependencies — structural checks only
- Gate 2 (campaign profile): `vault/compliance/exclusions.md` + `vault/compliance/rate_limits.md` + `vault/compliance/domain_rules.md` + `vault/icp/disqualification.md` + `vault/playbook/signatures.md`
- Gate 2 (follow-up profile): `vault/compliance/exclusions.md` + `vault/compliance/rate_limits.md` + `vault/compliance/domain_rules.md` + `vault/playbook/signatures.md`
- Gate 3 (campaign profile): `vault/icp/scoring_rules.md` + `vault/icp/tier_definitions.md` + `vault/product/proof_points.md` + `vault/product/positioning.md`
- Gate 3 (follow-up profile): `vault/product/proof_points.md` + `vault/product/positioning.md` + validated conversation summary + trigger metadata

**Gate 1 — Structural Integrity** (`gate1_structural.md`):
```
PASS criteria (ALL must pass):
- All required fields present (zero missing)
- All fields correct type (no string where integer expected)
- No null/empty/"TBD"/"N/A" in required fields
- Trace log present: `taskId` + `agent` + `timestamp` + `vaultFilesUsed`
- Record count satisfies task spec expectation
- Output is valid JSON (parseable)

FAIL on ANY criterion: stop. Do not run Gate 2.
```

**Gate 2 — Compliance** (`gate2_compliance.md` for campaign drafts, `followup_gate2_validator.py` for warm drafts):
```
PASS criteria (ALL must pass):
- Zero contacts from 7 blocked domains
- Zero contacts from 27 blocked individual emails
- For dispatch tasks: daily rate limits not exceeded
- For dispatch tasks: channel routing correct (cold=Instantly, warm=GHL)
- For campaign drafts: ICP disqualification applied per disqualification.md
- For all outreach: CAN-SPAM footer present in every email
- For all outreach: Unsubscribe mechanism present
- For all outreach: No spam trigger words
- For all outreach: Subject ≤60 chars, no ALL CAPS, ≤1 exclamation mark
- For all outreach: No banned openers (GUARD-004 static list)
- For warm follow-up: unsupported thread types are skipped before validation rather than forced through

FAIL on ANY criterion: stop. Do not run Gate 3.
```

**Gate 3 — Business Alignment** (`gate3_alignment.md` for campaign drafts, `followup_gate3_validator.py` for warm drafts):
```
PASS criteria (ALL must pass):
- Campaign profile:
  - ICP score math correct (spot-check min(3, record_count))
  - Tier assignments match rubric (Tier 1 ≥80, Tier 2=60-79.9, Tier 3=40-59.9)
  - Email angle matches lead tier
  - Content references specific lead/company/industry (not generic)
  - Product proof points match vault/product/proof_points.md (no invented claims)
  - Booking link is https://caio.cx/ai-exec-briefing-call (exact)
  - Sender identity is Dani Apgar, Head of Sales, Chief AI Officer
- Follow-up profile:
  - Draft references the actual prior conversation
  - Trigger, urgency, and tone fit the conversation stage
  - No fabricated context or invented proof point
  - Sender identity is Dani Apgar, Head of Sales, Chief AI Officer
  - Cold angle-tier mapping is NOT applied to warm follow-up drafts

FAIL: identify specific misalignment (not generic "failed")
```

**Verdict output format (canonical — must match /validate output exactly):**
```json
{
  "verdict": "PASS|FAIL",
  "gateResults": {"gate1": "PASS|FAIL", "gate2": "PASS|FAIL", "gate3": "PASS|FAIL"},
  "failureReason": "string|null",
  "violations": ["specific violation 1"],
  "recommendation": "PROCEED|RERUN|ESCALATE",
  "notificationStatus": "SENT|SKIPPED_OPTIONAL|FAILED|NOT_APPLICABLE"
}
```

---

## 14. GUARDRAIL SPECIFICATIONS

### 14.1 `guardrails/hard_blocks.md`

**Absolute Prohibitions (no override, no exception):**

| Operation | Enforcement |
|-----------|-------------|
| `bulk_delete` contacts | `/execute` hard-block preflight refuses run before lock claim or candidate generation |
| `export_all_contacts` | Hard block |
| `mass_unsubscribe` | Hard block |
| Agent approves own output | Maker-checker: different session runs /validate |
| Manual fix of bad output | Scrap. Fix system. Rerun. |
| External write before preview + validation + approval | Hard block |
| Production-required file still contains placeholder or fake content | Hard block for the active phase |
| Phase-gated stub used as active-phase source material | Hard block |
| GHL API calls without MCP | Architecture violation |
| Mock data in validation | Anti-mocking rule. Real data only. |
| Cold email via GHL | Channel routing violation |
| Warm email via Instantly | Channel routing violation |
| Warm follow-up loads cold angle/playbook context without an explicit later-phase rule | Hard block during Phase 3A-3F |
| Zero-message or no-email contact sent to warm analysis/drafting | Hard block |
| Warm approval creates GHL task/upsert side effects | Hard block |
| Failed send recorded as `DISPATCHED` instead of `SEND_FAILED` | Hard block |
| Any tag removal, tag replacement, or tag-clear operation in GHL | Hard block |
| Any generic contact upsert/update payload containing `tags`, `tagIds`, or equivalent tag fields | Hard block |
| Any generic contact update touching blocked fields outside the allowlist in `safe_contact_write_fields.md` | Hard block |

**Stub policy**: Formal phase-gated stubs are allowed only outside the active phase and only when they use the required stub template (`Status`, `Phase`, `Owner`, `Why deferred`, `Review trigger`).

**Tag-safety policy**: All GHL tag writes are add-only. `ghl_add_tag` is the only permitted tag mutation operation. Generic contact writes are field-allowlisted only and must preserve existing tag state.

**Recovery policy**: Any future tag recovery must be executed from an exact incident manifest with dry-run diff, additive-only restore, and post-restore verification. No manual best-guess backfills and no full tag-array replacement are allowed.

**Execution sequencing rule**: `/execute` hard-block preflight checks normalized `Operation Intents` before any execution work, lock claim, or external mutation. Validation-only tasks may read candidate output files, but may not perform real writes while a hard block condition exists.

### 14.2 `guardrails/quality_guards.md`

**GUARD-001 — Rejection Count:**
Trigger: Lead has 2+ prior rejections in last 30 days → BLOCK
Override: Lead has 3+ approvals in the last 90 days AND approval:rejection ratio >= 2:1 within that 90-day window → bypass block
Storage: `revtry/guardrails/rejection_memory.md` (30-day TTL per lead for rejections; 90-day TTL for approvals)

**GUARD-002 — Repeat Draft Fingerprint:**
Trigger: SHA-256 hash of email body matches prior rejected draft → BLOCK
Storage: SHA-256 hashes in rejection_memory.md

**GUARD-003 — Evidence Minimum:**
Trigger: `enrichment_score < 70` (NOT `icp_score`) → Redirect to enrichment (not hard block)
Boundary note: enrichment_score = 70 PASSES this guard (threshold is strictly less-than)
Do NOT pass to Campaign Craft until enrichment_score ≥ 70

**GUARD-004 — Banned Openers:**
Canonical location: `vault/playbook/signatures.md` (single source of truth — quality_guards.md references it but does not duplicate it)
Static list: defined in vault/playbook/signatures.md
Dynamic (requires `FEEDBACK_LOOP_POLICY_ENABLED=true`): openers in rejection feedback ≥2x → auto-added to the banned list in vault/playbook/signatures.md via /metabolize

**GUARD-005 — Generic Density:**
Trigger: Email lacks specific reference to lead/company/industry → BLOCK
Rule: Every email must reference at least one specific detail (company name, industry challenge, title-specific pain point)

**Warm follow-up corollary**: Every follow-up email must reference at least one real conversation detail from the selected primary thread. Generic "checking in" follow-ups fail this guard.

### 14.3 `guardrails/circuit_breaker.md`

**Trip condition**: 3 consecutive failures on any single integration
**Integrations**: GHL API, Instantly, HeyReach, Apollo
**Reset**: Exponential backoff — 5 min (1st trip) → 15 min (2nd trip) → 60 min (3rd trip) → manual-only (4th+ trip). Each trip-reset cycle is logged to operations_log.md with a cumulative trip count.
**On trip**: Stop ALL operations to that integration. Log to operations_log.md. Send Slack alert.
**Manual override**: Requires Chris Daigle explicit approval. Required after 3rd consecutive trip cycle.

### 14.4 `guardrails/autonomy_graduation.md`

| Stage | Email Limit | Tiers | Approval Required | Graduation Criteria |
|-------|-------------|-------|-------------------|--------------------|
| **Ramp** (default) | 5/day | Tier 1 only | Chris + Dani both approve | Starting stage |
| **Supervised** | 25/day | All tiers | Dani approves via dashboard | Open ≥50% AND reply ≥8% AND bounce <5% for 14 consecutive days. Chris reviews KPIs and explicitly approves. |
| **Full Autonomy** | 25/day | All tiers + cadence | Human review for new campaigns only | Same KPI metrics for 30 additional days at Supervised. Dani also approves. |

**KPI Red Flags → EMERGENCY_STOP:**

| Metric | Target | Emergency Trigger |
|--------|--------|-------------------|
| Open rate | ≥50% | <30% |
| Reply rate | ≥8% | 0 replies after 15 sends |
| Bounce rate | <5% | >10% |
| Unsubscribe | <2% | >5% |

**EMERGENCY_STOP action**: Halt ALL outbound immediately. Log to operations_log.md. Send Slack alert. Require Chris approval to resume.

**Manual graduation override**: Chris may approve graduation at lower thresholds with documented rationale recorded in `registry/escalations.md`. The automated thresholds are targets, not hard gates — the system must not block graduation indefinitely if campaigns are performing well by industry standards but below the aggressive automated targets.

### 14.5 `guardrails/dedup_rules.md`

**Layer 1 — Daily State**: No same lead dispatched twice in one day
**Layer 2 — Lead Status**: No bounced (permanent block), unsubscribed (permanent block), or compliance-rejected (permanent block) leads. Dani-rejected leads follow GUARD-001 cooldown (30-day window) and require a different angle on re-targeting.
**Layer 3 — Cross-Channel**: No lead gets email AND LinkedIn on same day
**Layer 4 — Pipeline State Dedup**: No lead re-enters a pipeline stage it has already completed or been rejected from within the current campaign cycle (default: 30 days). A lead that was dispatched in Phase 2 may not re-enter the Recon pipeline within the same cycle.

**Warm identity rule**: Canonical GHL dedup key is `ghlContactId` when present. Warm follow-up dispatch must not rely on mixed email-vs-contact-id identity.

All 4 layers checked BEFORE any dispatch. Layers 1-3 apply at dispatch time. Layer 4 applies at task spec creation time (Orchestrator checks before writing Campaign Craft specs).

### 14.6 `guardrails/deliverability.md`

**4-Layer GHL Email Deliverability (run before any GHL email send):**

| Layer | Check | Action |
|-------|-------|--------|
| Layer 1 — RFC 5322 | Valid email address format | BLOCK if invalid |
| Layer 2 — Exclusion | Against exclusions.md domain + email lists | BLOCK if match |
| Layer 3 — Domain concentration | Max 3 emails per recipient domain per batch | BLOCK if exceeded |
| Layer 4 — Spam triggers | "free", "guarantee", "urgent", "act now", "limited time", "winner", "no obligation", "buy now" | BLOCK if present |

---

## 15. TASK SPEC TEMPLATE

Save as: `revtry/agents/orchestrator/task_spec_template.md`

**taskId definition**: Generated by `/plan-task` in the format `TASK-YYYYMMDD-HHmmssfff-RAND4`. Example: `TASK-20260307-101530127-Xk7Q`. This value is unique even when multiple tasks are planned in the same second.

**sessionId definition**: Generated by `/execute` at lock claim time in PowerShell. Format: `{agent-name}-{yyyyMMdd-HHmmssfff}-{random4}`. Example: `pipeline-ops-20260306-093015127-xKmR`. The 4-char random suffix eliminates timestamp collisions. This is written to `registry/active.md` and is unique per execution session. It is NOT the same as `taskId`.

**attemptNumber rule**: `/execute` computes `attemptNumber = count(registry/failures.md rows for taskId) + 1` before claiming a lock. If the next attempt would be `4`, execution is blocked and escalated.

**maker-checker evidence rule**: `/execute` records `makerSessionId`; `/validate` records `validatorSessionId`. PASS requires the two values to differ.

```markdown
# Task Spec: [TASK-YYYYMMDD-HHmmssfff-RAND4]
Created: YYYY-MM-DD HH:MM | Agent: [agent-name] | Priority: P0|P1|P2
Task Type: capability_audit | triage | enrichment | campaign_draft | conversation_analysis | followup_draft | dispatch | analytics

## 1. Goal Statement (Binary — testable yes/no)
[Must be answerable as PASS/FAIL when task completes]

BAD:  "Look at GHL contacts and find good ones"
GOOD: "Query all GHL contacts with dateLastActivity >14 days and no open deals,
       apply ICP scoring, return top 20 ranked by score. Output triage report."

## 2. Context Package (Max 5 vault files — apply inclusion test to each)
- [exact vault file path] — [why: what wrong decision happens without it?]

NOT included: [explicitly list excluded files]

## 3. Input Data
- Source: [exact tool, endpoint, filter]
- Filter: [exact logic — no interpretation required]
- Operation Intents: [normalized tokens such as `GHL_READ_CONTACTS`, `GHL_READ_PIPELINES`, `GHL_UPDATE_CONTACT`, `GHL_DELETE_CONTACT`]
- Required Phase Gates: [exact gate keys from `registry/phase_gates.md`, e.g. `PHASE_0A_MCP_VERIFIED_LIVE`, `PHASE_0B_WORKSPACE_READY`]
- Zero-result policy: [RETURN EMPTY WITH REASON | ESCALATE]
- Partial-data policy: [allowed nullable fields + how to handle them]
- Fallback policy: [exact fallback allowed if primary data is unavailable]
- Notification Policy: [required | best_effort | not_applicable]
- contactWriteFieldAllowlist: [required when any GHL contact write is present; list exact mutable fields]
- tagMutationPolicy: [add_only]
- unsafeFieldTouchPolicy: [block_and_escalate]
- Required gate dependencies: [Gate 2 files] + [Gate 3 files]
- Context isolation notes: [for warm tasks, explicitly list what cold/revenue-intel/autonomy context is excluded]

## 4. Output Schema (Exact — agent must match precisely)
{
  "taskId": "string",
  "agent": "string",
  "timestamp": "ISO8601",
  "records": [{}],
  "count": "integer",
  "trace": {
    "vaultFilesUsed": ["array"],
    "recordsQueried": "integer",
    "filtersApplied": ["array"],
    "exclusionsChecked": "boolean"
  }
}

## 5. Scope Boundaries
MAY: [explicit allowed operations]
MAY NOT: [explicit prohibitions]
IF [specific edge case]: [exact instruction — no improvisation]

## 6. Validation Criteria (All binary — ALL must pass)
- [ ] Output count matches goal
- [ ] All required fields populated (zero nulls in required fields; nullable optional fields explicitly declared)
- [ ] Trace log complete
- [ ] No excluded contacts
- [ ] Schema matches Section 4 exactly
- [ ] `Operation Intents` match the planned work exactly and pass hard-block lint
- [ ] Any GHL contact write declares `contactWriteFieldAllowlist`, `tagMutationPolicy=add_only`, and `unsafeFieldTouchPolicy=block_and_escalate`
- [ ] Every `Required Phase Gate` is already `PASSED` before `/execute` starts
- [ ] Required gate dependency files are sufficient for Gate 2 and Gate 3
- [ ] `makerSessionId` and `validatorSessionId` are both recorded before completion
- [ ] `notificationStatus` is recorded and consistent with Notification Policy
- [ ] [Task-specific criteria]

## 7. Failure Protocol
1. DO NOT submit partial output
2. Log `failureReason` + `rootCauseHypothesis` in trace
3. Return FAIL status to orchestrator
4. Orchestrator diagnoses root cause. Max 3 retry attempts (tracked in `registry/failures.md` by `taskId`).
5. Every failure log row MUST include Attempt #.
6. If the next attempt would be 4 → escalate to human — do NOT create a 4th attempt

## 8. Escalation Trigger
Escalate if:
- Same failure occurs 3x with different root cause fixes
- Agent discovers data contradicting vault rules
- Data in unexpected format not covered by agent rules
- Required gate dependencies or live tool capabilities are missing

## 9. Success Signal
COMPLETE when:
1. All validation criteria pass (Gates 1+2+3)
2. Output written to: revtry/outputs/[TASK-ID]_output.md
3. Registry updated: status=COMPLETED in `registry/completed.md`, including `makerSessionId` + `validatorSessionId` + `notificationStatus`
4. /metabolize run for any post-validation vault updates
5. Notification outcome recorded as `SENT`, `SKIPPED_OPTIONAL`, `FAILED`, or `NOT_APPLICABLE`
```

---

## 16. REGISTRY INITIALIZATION

### `registry/active.md`
```markdown
# Active Tasks
Last Updated: YYYY-MM-DD HH:MM

| Task ID | Agent | Goal | Status | Attempt # | Lock Owner (makerSessionId) | Lease Expires | Notification Policy | Notes |
|---------|-------|------|--------|-----------|-------------------------------|---------------|---------------------|-------|
| — | — | — | — | — | — | — | — | — |
```

### `registry/completed.md`
```markdown
# Completed Tasks
(Keep last 50 entries)

| Task ID | Agent | Goal | Completed | Gate Results | Maker Session | Validator Session | Notification Policy | Notification Status | Notes |
|---------|-------|------|-----------|-------------|---------------|-------------------|---------------------|---------------------|-------|
```

### `registry/failures.md`
```markdown
# Failure Log
(Keep all entries — never delete)

| Task ID | Attempt # | Gate Failed | Specific Reason | Root Cause | Fix Applied | Date |
|---------|-----------|-------------|----------------|-----------|-------------|------|

**Two-phase logging**: `/validate` FAIL writes the initial row with `Root Cause` = hypothesis (what it suspects). `/metabolize` FAIL upgrades `Root Cause` to confirmed category and fills `Fix Applied`. If `/metabolize` has not yet run, `Fix Applied` = blank.
**Archival policy**: After 100 entries, move entries older than 30 days to `registry/failures_archive.md`. `/execute` only scans active (non-archived) entries for `attemptNumber` computation.
```

### `registry/escalations.md`
```markdown
# Escalations Requiring Human Attention

| Task ID | Reason | Attempts | Escalated | Resolved | Resolution |
|---------|--------|----------|-----------|----------|------------|
```

### `registry/phase_gates.md`
```markdown
# Phase Gates

| Gate | Status | Passed At | Evidence Task ID | Notes |
|------|--------|-----------|------------------|-------|
| PHASE_0A_MCP_VERIFIED_LIVE | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after Task 3B live verification succeeds |
| PHASE_0B_WORKSPACE_READY | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED after Step 9 runtime scaffolding is initialized |
| PHASE_0_TRIAGE_CRITERIA_APPROVED | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after Chris + Dani approve the audit-derived triage criteria |
| PHASE_3_WARM_VALIDATED | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after Phase 3A-3E warm flow is validated locally/private staging |
| PHASE_3E_TAG_SAFETY_HOTFIX | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after the add-only tag hotfix is validated live on a safe smoke contact |
| PHASE_3E_TAG_RECOVERY_COMPLETE | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after an incident manifest restore completes with post-restore verification |
| PHASE_3F_VERCEL_DEPLOYED | NOT_STARTED\|IN_PROGRESS\|PASSED\|BLOCKED | ISO8601\|— | TASK-ID\|— | Set to PASSED only after deployed smoke checks and remote approval verification succeed |
```

### `registry/locks/[TASK-ID].lock`
```json
{
  "taskId": "TASK-YYYYMMDD-HHmmssfff-RAND4",
  "sessionId": "agent-yyyyMMdd-HHmmssfff-rand4",
  "agent": "string",
  "acquiredAt": "ISO8601",
  "leaseExpiresAt": "ISO8601",
  "lastHeartbeatAt": "ISO8601"
}
```

### `memory/operations_log.md`
```markdown
# Operations Log
(Running log — most recent first)

Format per entry:
[YYYY-MM-DD HH:MM] | [taskId] | [agent] | [action] | [result]
```

### `memory/learnings.md`
```markdown
# Cross-Task System Learnings
(Updated by /metabolize when same root cause appears 3x)

| Date | Pattern | Root Cause | Fix Applied | Files Updated |
|------|---------|-----------|-------------|---------------|
```

**Lock release behavior:**
- PASS: delete `registry/locks/[TASK-ID].lock`, remove the active lock row, append completed row with maker session, validator session, notification policy, and notification status
- BLOCKED_HARD_RULE: do not claim a lock, do not increment attempt count, and log the refusal in `memory/operations_log.md`
- FAIL: delete `registry/locks/[TASK-ID].lock`, keep task status history, clear or expire the lock so a later corrected attempt can reclaim it, and log the failure row with Attempt #
- Lease expiry: any later `/execute` may reclaim an expired lock, but must delete and recreate the stale `.lock` file and log the reclaim event in `memory/operations_log.md`

---

## 17. PHASE 0 IMPLEMENTATION SEQUENCE

Execute in this exact order. Do not skip steps.

**Step 1: Cleanup**
- Inventory legacy `GEMINI.md` and legacy `vault/` into `revtry/migration/legacy_inventory.md`
- Preserve source files until migration complete and reviewed

**Step 2: CLAUDE.md**
- Create or maintain `Project-RevTry/CLAUDE.md`
- Under 250 lines, all 9 sections required (spec in Section 11.1)

**Step 3A: Phase 0A — Extend and verify the external GHL MCP**
- Verify current baseline: 14 existing tools in `server.py`
- Add and verify the required Phase 0A read tools: `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_list_pipelines`, `ghl_list_custom_fields`
- Record live discovery results, pagination behavior, and filter support in `revtry/vault/integrations/ghl.md`
- If any required read capability is missing, stop here and log blocker to `revtry/registry/escalations.md`

**Step 3B: Task 3B live MCP discovery + `.mcp.json` confirmation**
- Run PowerShell-first preflight:
  ```powershell
  Test-Path 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
  python -m py_compile 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
  if (-not $env:GHL_API_KEY -or -not $env:GHL_LOCATION_ID) { throw 'Environment not ready' }
  python 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
  ```
- Create or maintain `Project-RevTry/.mcp.json` (config in Section 11.2) only after the preflight passes
- Launch a fresh Claude Code session from that same env-ready PowerShell shell. The current shell is not proof that the Claude runtime session inherited the same environment.
- Run `/prime`
- Confirm the live observed tool inventory matches the expected 18-tool set
- Verify read tools first: `ghl_list_pipelines`, `ghl_list_custom_fields` (`contact` and `opportunity`), `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_get_contact`, `ghl_get_calendars`, `ghl_get_free_slots`, `ghl_get_calendar_events`
- Verify write-capable tools second using only designated safe smoke assets: `ghl_create_contact`, `ghl_update_contact`, `ghl_add_tag`, `ghl_bulk_create_contacts`, `ghl_create_opportunity`, `ghl_trigger_workflow`, `ghl_create_appointment`, `ghl_get_appointment`, `ghl_update_appointment`, `ghl_delete_calendar_event`
- Record the full evidence matrix in `revtry/vault/integrations/ghl.md` under `## Task 3B Live MCP Verification`
- If safe smoke assets are missing or unsafe, PAUSE Task 3B and leave `PHASE_0A_MCP_VERIFIED_LIVE` closed
- If all 18 tools are callable and evidence is complete, set `PHASE_0A_MCP_VERIFIED_LIVE = PASSED`
- Treat missing Slack webhook as optional and log notification state explicitly

**Step 4: Slash Commands**
- Ensure `Project-RevTry/.claude/commands/` contains all 6 runtime command files
- Create any missing command files from the specs in Section 11.3
- Each must include self-validate checklist

**Step 5: revtry/ Folder Structure**
- Create all folders from Section 10 file structure
- Create all README.md files (index + purpose, not placeholder)

**Step 6: Vault Population (Priority Order)**
1. `vault/compliance/exclusions.md` — needed before any output
2. `vault/icp/tier_definitions.md`
3. `vault/icp/scoring_rules.md`
4. `vault/icp/disqualification.md`
5. `vault/integrations/ghl.md` — needed for Phase 0
6. `vault/compliance/domain_rules.md`
7. `vault/compliance/rate_limits.md`
8. `vault/product/` (5 files) — migration from legacy product_context.md
9. `vault/playbook/` (4 files) — migration from legacy email_angles.md
10. `vault/feedback/` — initialize with empty templates

Future-phase files created during this step must use the formal phase-gated stub template instead of freeform placeholders.

**Migration mapping (mandatory — complete before archiving any source file):**
- `vault/icp/scoring_rules.md` → `revtry/vault/icp/scoring_rules.md`
- `vault/icp/tier_definitions.md` → `revtry/vault/icp/tier_definitions.md`
- `vault/product/product_context.md` → split across `revtry/vault/product/offers.md` + `positioning.md` + `pricing.md` + `proof_points.md` + `cta_library.md`
- `vault/playbook/email_angles.md` → `revtry/vault/playbook/email_angles.md`

**Step 7: Guardrails**
- All guardrail files with binary rules only

**Step 8: Agent Definitions**
- 6 specialist agents × (config.md + output_schema.md): Recon, Enrichment, Segmentation, Campaign Craft, Pipeline Ops, Revenue Intel
- If future-phase agent folders are created early (`conversation-analyst`, `followup-draft`), they must use the formal phase-gated stub template until their phase starts
- Orchestrator: config.md + context_assembly.md + task_spec_template.md
- Quality Guard: config.md + gate dependency lists

**Step 9: Registry Initialization**
- active.md, completed.md, failures.md, escalations.md, phase_gates.md — headers/default gate rows only
- registry/locks/ — create empty folder for runtime `.lock` files
- memory/operations_log.md + memory/learnings.md — headers only
- Backfill `phase_gates.md` so `PHASE_0B_WORKSPACE_READY = PASSED` once Step 9 completes. Do NOT pre-pass `PHASE_0A_MCP_VERIFIED_LIVE`; that gate remains blocked until Task 3B succeeds.

**Step 10: First PIV Loop — GHL Audit**
- Dependency preflight first (Section 0)
- Orchestrator writes task spec for Pipeline Ops (`task_type = capability_audit`) with normalized `Operation Intents` and `Required Phase Gates = [PHASE_0A_MCP_VERIFIED_LIVE, PHASE_0B_WORKSPACE_READY]`
- Pipeline Ops runs via `/execute` in a new Claude Code session
- Output: contact count, field inventory, pipeline stages, stale count, tag taxonomy, custom fields, verified capability matrix
- Separate fresh session runs `/validate`
- On PASS: `/metabolize` updates `vault/integrations/ghl.md` with verified tools, parameter support, pagination notes, and the named `Phase 0 Triage Criteria` section as `Status: DRAFT`
- Do not treat any preexisting audit-style inventory or approval-looking criteria already in `ghl.md` as authoritative gate evidence; the maker-checker audit flow is the source of truth
- Chris + Dani review the audit-derived triage criteria and must explicitly change the section to `Status: APPROVED` before triage begins
- After approval, update `registry/phase_gates.md` so `PHASE_0_TRIAGE_CRITERIA_APPROVED = PASSED`

**Step 11: Second PIV Loop — Lead Triage**
- Orchestrator writes task spec for Pipeline Ops with normalized `Operation Intents` and `Required Phase Gates = [PHASE_0A_MCP_VERIFIED_LIVE, PHASE_0B_WORKSPACE_READY, PHASE_0_TRIAGE_CRITERIA_APPROVED]`
- Pipeline Ops runs via `/execute` in new Claude Code session
- Applies only the triage criteria recorded in the named `Phase 0 Triage Criteria` section and must STOP unless `Status = APPROVED`
- Produces prioritized list
- If ICP fields missing: uses Phase 0 fallback priority model (not fabricated scoring)
- Separate fresh session runs `/validate`
- On PASS: notification outcome is recorded via `notificationStatus`
- **Hero Outcome 1 Complete** ✅

---

## 18. PHASE 0 VERIFICATION CRITERIA

| Check | Pass Criteria |
|-------|--------------|
| Legacy migration | GEMINI.md + vault/ inventoried, mapped, preserved |
| Planning scaffold vs runtime | PRD and CLAUDE.md clearly distinguish scaffold commands from runtime slash commands |
| CLAUDE.md | Under 250 lines, all 9 sections, no "TBD" |
| Environment ready | `GHL_API_KEY` and `GHL_LOCATION_ID` present before Phase 0 runs; missing Slack webhook recorded as optional |
| Claude runtime env | Fresh Claude Code session for Task 3B is launched from an env-ready PowerShell shell |
| PowerShell standard | Canonical validation commands run in PowerShell on this machine |
| .mcp.json | GHL MCP loads — live tool discovery recorded |
| Task 3B inventory | Live observed MCP inventory matches the expected 18-tool set |
| Phase 0A capability baseline | 14 existing tools from `server.py` recorded accurately |
| Phase 0A capability extension | `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_list_pipelines`, and `ghl_list_custom_fields` verified live |
| Contacts pagination | `ghl_list_contacts` pagination and `query` behavior recorded |
| Opportunities pagination | `ghl_list_opportunities` pagination and `pipeline_id` behavior recorded |
| Custom fields (contact) | `ghl_list_custom_fields` works with `object_type=contact` |
| Custom fields (opportunity) | `ghl_list_custom_fields` works with `object_type=opportunity` |
| Safe write verification | Write-tool smokes use designated safe test assets only |
| Missing test assets | Unsafe or missing safe test assets cause PAUSE, not PASS |
| GHL write scope ready | Private Integration token can perform safe smoke writes for contacts/tags/opportunities/calendars/events/workflows |
| `ghl.md` evidence section | `## Task 3B Live MCP Verification` exists with required fields and tool matrix |
| Provisional `ghl.md` state | Existing audit-style inventory or approval-looking triage content in `ghl.md` does not count as passed gate evidence |
| 6 slash commands | /prime, /plan-task, /execute, /validate, /metabolize, /status all functional |
| Vault completeness | All production-required vault files populated, freshness-dated; future-phase files use formal phase-gated stubs only |
| Guardrails | All files with binary rules only |
| Agent configs | 6 specialist agents (config.md + output_schema.md) + Orchestrator (config.md + context_assembly.md + task_spec_template.md) + Quality Guard (config.md + gate dependency lists) |
| Gate 1 test | Feed intentionally bad output (missing field) → Gate 1 rejects |
| Gate 2 test | Feed contact from blocked domain → Gate 2 rejects |
| Gate 3 test | Feed wrong tier angle assignment → Gate 3 rejects |
| GHL connected | Pipeline Ops can call GHL tools and receive real data |
| GHL audit | Returns: contact count, field inventory, pipeline stages, stale count, capability matrix |
| Triage criteria | Defined from audit data, written into vault/integrations/ghl.md |
| Triage approval gate | `DRAFT` and `DEFERRED` block triage; `APPROVED` with approval metadata permits it |
| Triage output | Lead list produced, validated in separate checker session, notification outcome recorded |
| Phase gates | `/plan-task` records `Required Phase Gates`; `/execute` blocks when any listed gate is not `PASSED` |
| Notification status | `notificationStatus` matches task policy and actual webhook state |
| Slack format | When sent, notification matches: {taskId, agent, summary: {count, top3}, timestamp, outputPath} |
| sessionId format | `{agent}-{yyyyMMdd-HHmmssfff}-{random4}` in every active.md lock entry |
| Task ID uniqueness | Two task specs created within the same second still receive distinct `TASK-YYYYMMDD-HHmmssfff-RAND4` IDs |
| Lock lifecycle | `.lock` file is created, heartbeated, reclaimed safely, and deleted on PASS/FAIL cleanup |
| Context isolation evidence | Context package contains only approved files and execution trace lists only those files |
| One-shot discipline | Execution completes without follow-up task spec mutation between `/execute` start and `/validate` PASS |
| Metabolism PASS | vault/feedback/agent_learnings.md updated after successful run |
| Metabolism FAIL | failures.md `rootCause` is specific (not "unknown") |
| Audit metabolism | Validated capability audit updates `vault/integrations/ghl.md` via `/metabolize`, not `/validate` |
| Maker-checker verified | `makerSessionId` and `validatorSessionId` both recorded and differ |
| Fallback verified | If ICP fields missing: GHL-native priority list returned (not invented scores) |
| Hard block verified | `/execute` preflight rejects prohibited `Operation Intents` before candidate output generation |
| Tag preservation | Approval and enrichment flows add `revtry-*` tags without removing preexisting contact tags |
| Unsafe tag mutation blocked | MCP `ghl_update_contact` rejects payloads containing `tags`, `tagIds`, or clear/remove semantics |
| Unsafe contact fields blocked | Generic contact updates touching blocked fields outside the allowlist are refused |
| Add-only tagging | `ghl_add_tag` remains the only permitted tag mutation path |
| Live tag-safety smoke | Safe smoke contact proves plain upsert preserves existing tags and additive tagging appends only |
| Audited tag recovery | Incident manifest + dry-run diff + additive-only restore + post-restore verification complete with every affected contact passing |
| Combined audit+triage blocked | Pipeline Ops audit and triage remain separate Phase 0 tasks; a combined task is rejected |
| JSON casing | Machine-readable JSON examples use camelCase end-to-end |
| Retry counter | Three synthetic failures on same `taskId` allow attempts 1-3 and block attempt 4 |
| Registry table integrity | `active.md`, `completed.md`, and `failures.md` sample tables have header/row column counts that match |

---

## 18A. PHASE 3 WARM-FIRST VERIFICATION CRITERIA

| Check | Pass Criteria |
|-------|--------------|
| Warm eligibility | Zero-message contacts are skipped before analysis; no-email contacts are skipped before drafting |
| Primary-thread selection | Newest `lastMessageDate` thread is selected deterministically |
| Prompt compaction | Latest 8 primary-thread messages are reordered chronologically and trimmed before prompt assembly |
| Context isolation | Warm tasks load only conversation, compliance/signature, and minimal CTA/proof context |
| Analysis retry behavior | Invalid LLM JSON gets one repair retry; repeated failure records a per-contact analysis failure and continues |
| Draft retry behavior | Invalid LLM JSON gets one repair retry; repeated failure records a per-contact draft failure and continues |
| Follow-up validation profile | Warm drafts pass dedicated follow-up Gate 2/3 checks without cold angle-tier requirements |
| Warm approval semantics | Approve/reject updates follow-up draft state only; no GHL task creation or contact upsert side effects |
| Warm dispatch state | Failed send becomes `SEND_FAILED`, never `DISPATCHED` |
| Shared GHL safety | Warm dispatch still runs circuit breaker → rate limiter → dedup and consumes shared GHL budget before cold GHL sends |
| Briefing telemetry | `DailyBriefing` persists skipped counts, failure counts, urgency/trigger breakdowns, and estimated cost |
| Route compatibility | Local mixed mode keeps `GET /` backward-compatible; warm-only deployed mode redirects `/` to `/briefing` |
| Warm dashboard flow | Manual warm generate → review → approve → unified warm-first dispatch works end-to-end |
| Scheduler posture | Scheduler exists but is disabled by default; manual flow works without it |
| Auth | Deployed mode requires HTTP Basic Auth on all dashboard routes except `/healthz` |
| Warm-only mode | `WARM_ONLY_MODE=true` hides cold routes and prevents cold approval/dispatch surfaces from leaking into deployed warm mode |
| Storage backend | Local dev uses file storage; deployed warm mode requires Postgres-backed persistence |
| Idempotency | Same-day warm reruns overwrite the same draft; next-day reruns create a new draft |
| Business date | Briefing, follow-up queue, rate limiter, and scheduler all resolve daily semantics in `America/Chicago` |
| Health endpoint | `GET /healthz` is open and reports mode + storage backend for deploy smoke checks |
| Vercel readiness | Warm dashboard local/private validation completes and `PHASE_3E_DEPLOY_READY` passes before deployment begins |
| Vercel deployment | `/briefing` and `/followups` render in deployed mode; remote approve/reject works; no cold-flow dependency required |
| Cold-track isolation | Cold outbound remains roadmap-active but does not expand warm prompt context before Phase 4 |
| Later-track gate | Autonomy graduation and revenue-intel surfaces remain Phase 5 work until warm + cold paths are validated |

---

## 19. TEAM & APPROVAL FLOWS

**Chris Daigle** (GTM/PTO Engineer):
- Operates the orchestrator
- Opens new Claude Code sessions for execution tasks
- Reviews all agent outputs (technical review)
- Approves system changes and vault updates
- Handles all escalations
- Approves autonomy graduation decisions

**Dani Apgar** (AE, Head of Sales):
- Reviews lead triage list (Phase 0: Slack; Phase 1+: dashboard)
- Approves/rejects campaign drafts before any send
- Provides rejection feedback (updates GUARD-004 and vault/feedback/)
- Co-approves autonomy graduation (Supervised → Full Autonomy stage)

**Phase 0 Approval Flow:**
1. Capability audit passes and `/metabolize` writes `Phase 0 Triage Criteria` as `Status: DRAFT`
2. Chris + Dani review the criteria and explicitly change the section to `Status: APPROVED`
3. Pipeline Ops produces triage list
4. `/execute` saves candidate output
5. Separate fresh session runs `/validate` → PASS
6. Notification outcome recorded (`SENT`, `SKIPPED_OPTIONAL`, or `FAILED` under best-effort policy)
7. Chris reviews technical output. Dani reviews sales quality.
8. No formal approval needed for read-only triage output itself. The approval gate applies to the criteria, not the report.

**Phase 1 Approval Flow (Campaign Drafts):**
1. Campaign Craft produces draft batch
2. `/execute` saves candidate output
3. Separate fresh session runs `/validate` → PASS
4. FastAPI dashboard (`http://localhost:8000/drafts`) displays formatted drafts
5. Dani approves/rejects individual items with notes via POST /approve or POST /reject
6. Rejection notes → `/metabolize` → vault/feedback/campaign_performance.md

**Phase 3 Approval Flow (Warm Follow-Ups):**
1. Conversation Analyst + Follow-Up Draft pipeline produces warm draft batch
2. `/execute` saves candidate output
3. Separate fresh session runs `/validate` with the follow-up profile → PASS
4. Warm dashboard surfaces the queue at `/briefing` and `/followups`
5. Dani approves/rejects follow-up drafts
6. Approval changes file-backed draft state only; it does NOT create GHL tasks or contact upserts
7. Manual dispatch happens as a separate action through unified `/dispatch/run`
8. Send success → `DISPATCHED`; send failure → `SEND_FAILED`

---

## 20. PHASE ROADMAP

### Phase 0: Foundation + GHL Triage
Everything in Phase 0 is infrastructure and the first agent run. No outbound sends. (Steps 1–11 above.)

### Phase 1: Campaign Drafts
- Recon → Enrichment → Segmentation chain (separate top-level sessions under the current contract)
- Campaign Craft agent with full playbook context (new session)
- Local FastAPI dashboard (`http://localhost:8000`) with 4 routes: GET /drafts, GET /drafts/{id}, POST /drafts/{id}/approve, POST /drafts/{id}/reject
- First batch ICP-qualified campaign drafts → approval queue
- Legacy cold/campaign milestone remains deferred; same-day Hero Outcome 2 closes under the warm-first rule after 10+ real warm follow-up drafts are approved in the dashboard

### Phase 2: Outreach Dispatch Foundation
- Shared outbound safety chain (circuit breaker, rate limiter, dedup)
- Manual dispatch correctness and `SEND_FAILED` handling
- GHL budget + breaker ready for warm-first dispatch priority

### Phase 3: Warm Follow-Up System
- 3A: Conversation reader + data models
- 3B: Conversation Analyst
- 3C: Follow-Up Draft generation
- 3D: Warm review dashboard
- 3E: Warm deploy-readiness hardening (unified dispatch, auth, Postgres-backed deployed persistence, idempotent generation, business-date consistency, tag-safety hotfix validation, audited tag recovery if needed)

### Phase 3F: Warm Dashboard Deployment to Vercel
- Dashboard deployed at `caio-rev-try.vercel.app` (2026-03-10)
- Auth working, pages rendering, warm-only mode active with Postgres persistence
- DB connection hardening, healthz DB probe, graceful route fallbacks, and candidate-source fallback are implemented and locally validated
- Remaining: real pipeline population, deployed route verification with real data, and Dani remote verification
- Pipeline has never run against real GHL data — dashboard counters stay at zero until Task 62D writes real rows to Postgres

**Same-day Hero Outcome path (2026-03-10):**
- Hero Outcome 2 closes when Dani approves at least 10 real warm follow-up drafts in the dashboard
- Hero Outcome 3 closes when Dani accesses the deployed warm dashboard remotely, sees real data, and completes at least one approval or rejection from a non-dev machine

### Phase 4: Cold-Outbound Expansion
- Reactivate cold outbound as a separate tested operator surface
- Keep cold context assembly isolated from the warm path

### Phase 5: Revenue Intelligence + Autonomy Graduation
- Revenue Intel agent for analytics and trend detection
- /metabolize fully compounding across warm + cold operations
- Autonomy graduation: Ramp → Supervised when KPI targets are met and approved
- Autonomy graduation: Supervised → Full Autonomy after sustained validated performance

---

*RevTry PRD v2.9 — Greenfield Coding Workflow Standard*
*Source: E:\CAIO RevOps Claw\RevTry_PRD.md v1.0*
*v2.2 refinements: scaffold-vs-runtime separation, Phase 0A MCP extension gate, PowerShell-first command contracts, pre-execution hard-block enforcement, explicit `notificationStatus` tracking, approval-gated Phase 0 triage criteria, evidence-recorded maker-checker, executable retry/session rules, post-validation metabolism ownership, and formal phase-gated stub policy.*
*v2.3 refinements (deep peer review): unified verdict schema, approval-gated Phase 0 triage criteria, top-level-session-only runtime execution, explicit `notificationPolicy` and `notificationStatus` handling, `operationIntents`-based hard-block enforcement, and registry/task-spec cohesion across Phase 0.*
*v2.4 refinements (final hardening pass): requiredPhaseGates binding with phase_gates.md, full lock-file lifecycle and cleanup, deterministic validation ordering, simplified notification enum, collision-resistant task IDs, explicit capability-audit `/metabolize` write scope, separate audit and triage tasks, Campaign Craft output schema, and camelCase machine-readable JSON end-to-end.*
*v2.5 refinements (warm-first roadmap pass): warm-follow-up-first sequencing, immediate post-validation Vercel deployment, minimal-context isolation for warm prompts, Phase 3A-3F warm system definition, Phase 4 cold-outbound expansion, Phase 5 revenue-intel/autonomy graduation, dedicated warm data models and validators, and explicit warm approval/dispatch guardrails.*
*v2.6 refinements (pre-Vercel hardening pass): reopened Phase 3E for deploy-readiness hardening, unified warm-first `/dispatch/run`, HTTP Basic Auth for deployed dashboard access, warm-only deployed mode, storage backend abstraction with Postgres for deployed warm persistence, deployment-safe trace logging, idempotent warm draft generation by business date, `America/Chicago` business-date normalization, `GET /healthz`, date-filtered warm routes, and fail-fast GHL credential validation.*
*v2.7 refinements (tag-safety hardening pass): add-only tag policy across app/runtime/MCP layers, generic contact write allowlist, hard blocks for tag removal/replacement and unsafe contact fields, Task 3B safe-write scope checks, and a required `PHASE_3E_TAG_SAFETY_HOTFIX` gate before Phase 3F resumes.*
*v2.8 refinements (audited tag recovery pass): one-time incident-manifest restore procedure, dry-run diff + additive-only recovery tooling, post-restore verification requirement, `PHASE_3E_TAG_RECOVERY_COMPLETE`, and completed recovery evidence for the 2026-03-08 tag-loss incident.*
*v2.9 refinements (project-root consolidation pass): `Project-RevTry` promoted to the authoritative runtime root, project-local `.mcp.json` and runtime slash commands made self-contained, Task 3B bulk-create smoke independently verified, and the next operational chain re-centered on Task 15 before deployment work.*
*v2.10 refinements (runtime-priority sync pass): immediate next runtime sequence locked to Task 15–22 in the authoritative project root, and legacy CAIO tracker guidance reduced to reference-only redirect behavior so deployment does not jump ahead of the Phase 0 audit/triage chain.*
*v2.11 refinements (Vercel deployment pass): Phase 3F deployment live at `caio-rev-try.vercel.app`, deployment architecture documented (api/index.py + vercel.json + root requirements.txt), three deployment bugs fixed (missing files, python-multipart, DB error handling), remaining gaps identified (DB timeout, healthz probe, 4 unprotected routes, pipeline data population), Hero Outcome 3 priority elevated alongside Phase 0 audit chain.*

*v2.12 refinements (same-day Hero Outcome 2/3 execution pass): Phase 0 bookkeeping reconciled as complete, Phase 3F hardening validated locally (`connect_timeout=5`, DB-probing `/healthz`, graceful route fallbacks, triage-backed candidate-source fallback), and the immediate path narrowed to real pipeline population, deployed route verification, Dani remote approval, and warm-first Hero Outcome 2 closure.*
*v2.13 refinements (deployed warm-generation resilience pass): vault loading now auto-resolves the repo-local `revtry/vault` tree when `VAULT_DIR` is unset, `/followups/generate` now degrades to structured `503` JSON on unexpected startup failure instead of raw `500`, and the validated local suite increased to `330 passed`.*
*Build sequence: Steps 1–2 (workspace + runtime contract) → Step 3A (MCP extension) → Step 3B–9 (runtime infrastructure) → Step 10 (validated GHL audit) → Step 11 (validated hero outcome)*
*All files in Section 10 must be created with content. Future-phase files may use only formal phase-gated stubs.*
