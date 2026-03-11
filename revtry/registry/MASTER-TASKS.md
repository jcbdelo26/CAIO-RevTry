# MASTER-TASKS.md — RevTry Full Implementation Tracker

**Valid Through**: 2026-12-31
**Last Updated**: 2026-03-10
**Updated By**: Codex implementation session — Phase 3F hardening validated + same-day Hero Outcome execution path
**PRD Source**: `Project-RevTry/.claude/PRD.md` v2.12
**Handoff Docs**:
- `Project-RevTry/.agents/plans/phase-3-conversation-followup-handoff.md`
- `Project-RevTry/.agents/plans/prd-v2.5-update-handoff.md`

---

## Legend

- `[x]` DONE — Task completed and verified
- `[~]` PARTIAL — In progress or partially complete
- `[ ]` NOT_STARTED — Queued, waiting on dependencies
- `[D]` DEFERRED — Explicitly postponed; remains on active roadmap
- **(AUTO)** — Agent/system executes autonomously
- **(HUMAN)** — Requires Chris or Dani action directly
- **(HUMAN+AUTO)** — Human triggers session, agent executes
- `-->` Depends on: task reference or gate

---

## Progress Summary

| Phase | Name | Tasks | Done | Deferred | Remaining | Hero Outcome |
|-------|------|-------|------|----------|-----------|--------------|
| 0A | GHL MCP Extension | 4 | 4 | 0 | 0 | MCP tools verified live |
| 0B | Foundation + GHL Triage | 19 | 19 | 0 | 0 | Prioritized follow-up list for Dani |
| 1 | Campaign Draft Pipeline | 10 | 8 | 1 | 1 | 10+ ICP-qualified drafts approved |
| 2 | Outreach Dispatch Foundation | 7 | 4 | 2 | 1 | GHL warm dispatch live; cold deferred |
| 3A | GHL Conversation Reader | 5 | 5 | 0 | 0 | Conversation history scanned |
| 3B | Sentiment Analysis Agent | 3 | 3 | 0 | 0 | Contacts classified by urgency |
| 3C | Follow-Up Drafter + Storage | 4 | 4 | 0 | 0 | Personalized follow-up drafts ready |
| 3D | Warm Dashboard | 5 | 5 | 0 | 0 | Briefing + follow-up queue live |
| 3E | Warm Deploy-Readiness Hardening | 22 | 22 | 0 | 0 | Manual warm flow hardened; tag-safety smoke and audited tag recovery both verified |
| 3F | Vercel Deployment (Warm) | 8 | 5 | 0 | 3 | Warm dashboard accessible remotely with real data + remote approval |
| 4 | Cold-Outbound Expansion | 4 | 0 | 0 | 4 | Instantly + HeyReach reactivated |
| 5 | Revenue Intelligence + Autonomy | 5 | 0 | 0 | 5 | Full autonomy graduation |
| **Total** | | **96** | **79** | **3** | **14** | |

---

## Phase 0A — GHL MCP Read Capability Extension

> **Hero Outcome**: GHL MCP server verified with all 18 tools callable from Claude Code
> **Acceptance**: `PHASE_0A_MCP_EXTENDED` + `PHASE_0A_ENV_READY` + `PHASE_0A_MCP_VERIFIED_LIVE` all = PASSED

### Tasks

- [x] **Task 1: Reconfirm runtime assumptions** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Files: `CLAUDE.md`, `server.py`
  Output: Confirmed Python entrypoint, env vars, PowerShell canonical, top-level sessions only

- [x] **Task 2: Extend external GHL MCP with 4 list/read tools** (AUTO)
  Status: DONE | Completed: 2026-03-07
  File: `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`
  Tools added: `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_list_pipelines`, `ghl_list_custom_fields`

- [x] **Task 3: Run environment readiness preflight** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Verified: `GHL_API_KEY` (40 chars), `GHL_LOCATION_ID` (20 chars), server.py compiles, aiohttp+mcp+dotenv installed

- [x] **Task 3B: Run live MCP tool discovery** (HUMAN+AUTO)
  Status: DONE (2026-03-09)
  --> Depends on: Task 2, Task 3
  Action: Open fresh Claude Code session in `E:\Greenfield Coding Workflow\Project-RevTry\`. Run `/prime`. Invoke all 18 MCP tools with live test calls against safe designated assets only. Record verified tool list, schemas, pagination behavior, filter behavior, and sample response keys into `revtry/vault/integrations/ghl.md`.
  Gate: Sets `PHASE_0A_MCP_VERIFIED_LIVE` = PASSED
  **THIS IS THE SINGLE BLOCKER FOR PHASE 0B EXECUTION**
  Purpose: Prove the live Claude Code runtime can see and call the `ghl` MCP server exactly as the runtime workspace expects before any Phase 0B audit or triage work begins.
  Operator: Chris in a fresh Claude Code session launched from an env-ready PowerShell shell.
  Preflight:
  1. Open PowerShell in `E:\Greenfield Coding Workflow\Project-RevTry\`
  2. Confirm the shell already has `GHL_API_KEY` and `GHL_LOCATION_ID`
  3. Confirm the GHL Private Integration token has write scopes for contacts, opportunities, calendars/events, workflows, and tags. If write scopes are missing, PAUSE Task 3B.
  4. Start Claude Code from that same PowerShell window
  5. Run `/prime` before any MCP verification work
  Inputs Required From Chris:
  ```text
  TEST_CONTACT_EMAIL_PRIMARY=
  TEST_CONTACT_EMAIL_BULK_1=
  TEST_CONTACT_EMAIL_BULK_2=
  TEST_PIPELINE_ID=
  TEST_STAGE_ID=
  TEST_WORKFLOW_ID=
  TEST_CALENDAR_ID=
  TEST_TAG_PREFIX=revtry_mcp_smoke
  WORKFLOW_CONFIRMED_SAFE=yes
  CALENDAR_CONFIRMED_SAFE=yes
  PIPELINE_STAGE_CONFIRMED_SAFE=yes
  ```
  Safe Test Asset Policy:
  - Do not mutate uncontrolled production business contacts
  - Use reusable smoke contacts because contact deletion is not available
  - `ghl_trigger_workflow` may run only if the supplied workflow is explicitly confirmed safe/no-op
  - appointment smoke tests may run only against the supplied safe calendar
  - if any required safe asset is unknown, STOP and mark Task 3B as PAUSED rather than partially passing it
  Live Verification Sequence:
  1. List the live tool inventory first and compare it to the expected 18-tool set
  2. Run read-focused verification calls first:
     - `ghl_list_pipelines`
     - `ghl_list_custom_fields` with `object_type=contact`
     - `ghl_list_custom_fields` with `object_type=opportunity`
     - `ghl_list_contacts`
     - `ghl_list_opportunities`
     - `ghl_get_contact`
     - `ghl_get_calendars`
     - `ghl_get_free_slots`
     - `ghl_get_calendar_events`
  3. Run write-capable verification calls second using only the designated safe assets:
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
  4. Record evidence into `revtry/vault/integrations/ghl.md`
  Tool Count Contract:
  - `18 total tools`
  - `8 read-focused verification groups`
  - `10 write-capable verification calls`
  Evidence to Record:
  - live observed tool inventory
  - exact method names
  - required vs optional params
  - pagination behavior for `ghl_list_contacts` and `ghl_list_opportunities`
  - filter behavior for `query`, `pipeline_id`, and `object_type`
  - sample response keys for every tool
  - which safe asset was used for each write-tool smoke
  PASS Criteria:
  - all 18 tools are callable from the fresh Claude Code runtime session
  - read-tool pagination/filter behavior is captured in `ghl.md`
  - write-tool smokes complete using only safe designated assets
  - `revtry/vault/integrations/ghl.md` contains the full evidence section
  - `PHASE_0A_MCP_VERIFIED_LIVE` is updated to `PASSED`
  PAUSE Criteria:
  - runtime session is missing `GHL_API_KEY` or `GHL_LOCATION_ID`
  - safe write assets are missing
  - workflow/calendar/pipeline-stage safety is not confirmed
  - read tools pass but write tools cannot be safely tested yet
  FAIL Criteria:
  - the `ghl` MCP server is unavailable inside Claude Code
  - observed live tool inventory does not match the expected 18-tool set
  - any required tool is non-callable
  - evidence cannot be produced in `ghl.md`
  Post-Pass Next Step:
  - mark Task 3B DONE
  - set `PHASE_0A_MCP_VERIFIED_LIVE = PASSED`
  - continue immediately to Task 15
  - do not treat the existing triage criteria in `ghl.md` as final approval evidence until Tasks 15-18 complete normally
  Non-Technical Operator Checklist:
  1. Open PowerShell
  2. Go to `E:\Greenfield Coding Workflow\Project-RevTry\`
  3. Make sure Claude Code starts from that same PowerShell window
  4. Run `/prime`
  5. Give Claude the Task 3B objective
  6. Paste the safe test asset values
  7. Require Claude to:
     - list live tools first
     - run read-tool tests first
     - run write-tool tests only on the safe assets
     - update `revtry/vault/integrations/ghl.md`
     - update `revtry/registry/phase_gates.md`
     - mark Task 3B done only if every required check passes

### Phase 0A Gates

| Gate ID | Status | Verified By | Depends On |
|---------|--------|-------------|------------|
| PHASE_0A_MCP_EXTENDED | PASSED | Task 2 (2026-03-07) | — |
| PHASE_0A_ENV_READY | PASSED | Task 3 (2026-03-07) | — |
| PHASE_0A_MCP_VERIFIED_LIVE | PASSED | 2026-03-09 | Task 3B |

---

## Phase 0B — Foundation + GHL Triage

> **Hero Outcome**: "Which GHL contacts should Dani follow up with today?"
> Pipeline Ops --> GHL audit --> triage criteria --> prioritized list --> Slack to #revtry
> **Acceptance**: All Phase 0 gates PASSED, triage output validated, notification outcome recorded

### Infrastructure (DONE)

- [x] **Task 4: Create runtime .mcp.json** (AUTO)
  Status: DONE | Completed: 2026-03-07
  File: `E:\Greenfield Coding Workflow\Project-RevTry\.mcp.json`

- [x] **Task 5: Create 6 runtime slash commands** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Files: `.claude/commands/{prime,plan-task,execute,validate,metabolize,status}.md`

- [x] **Task 6: Create revtry/ folder structure + READMEs** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Root: `E:\Greenfield Coding Workflow\Project-RevTry\revtry\` (20 directories, 65 .md files)

- [x] **Task 7: Populate vault/compliance/** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Files: `exclusions.md`, `domain_rules.md`, `rate_limits.md`

- [x] **Task 8: Populate vault/icp/** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Files: `tier_definitions.md`, `scoring_rules.md`, `disqualification.md`, `target_companies.md` (stub)

- [x] **Task 9: Populate vault/integrations/** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Files: `ghl.md` (production), `instantly.md`, `heyreach.md`, `apollo.md`, `bettercontact.md`, `clay.md` (stubs)

- [x] **Task 10: Populate vault/product/ + vault/playbook/** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Product: `offers.md`, `positioning.md` (production), `pricing.md`, `proof_points.md`, `cta_library.md` (stubs)
  Playbook: `email_angles.md` (11 angles), `signatures.md` (production), `sequences.md`, `objections.md` (stubs)

- [x] **Task 11: Create all guardrail files** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Production: `gate1_structural.md`, `gate2_compliance.md`, `gate3_alignment.md`, `hard_blocks.md`, `quality_guards.md`
  Stubs: `circuit_breaker.md`, `autonomy_graduation.md`, `dedup_rules.md`, `deliverability.md`, `rejection_memory.md`, `escalation.md`

- [x] **Task 12: Create agent configs and output schemas** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Agents: orchestrator, recon, enrichment, segmentation, campaign-craft, pipeline-ops, revenue-intel, quality-guard
  Total: 19 files (8 config.md + 6 output_schema.md + 3 orchestrator extras + 2 READMEs)

- [x] **Task 13: Initialize registry and memory files** (AUTO)
  Status: DONE | Completed: 2026-03-07
  Registry: `active.md`, `completed.md`, `failures.md`, `escalations.md`, `phase_gates.md`
  Memory: `operations_log.md`, `learnings.md`

- [x] **Task 14: Write GHL audit task spec** (AUTO)
  Status: DONE | Completed: 2026-03-07
  File: `revtry/registry/tasks/TASK-20260307-143000000-Ak9R.md`
  Type: capability_audit | Agent: pipeline-ops | Priority: P0

### Audit + Triage Pipeline (COMPLETE)

- [x] **Task 15: Execute GHL audit** (HUMAN+AUTO)
  Status: DONE | Completed: 2026-03-10 (bookkeeping fix — audit was executed and validated but Task 15 was not marked)
  --> Depends on: Task 3B (`PHASE_0A_MCP_VERIFIED_LIVE` = PASSED)
  Agent: pipeline-ops | Task type: capability_audit
  Output: `revtry/outputs/TASK-20260307-143000000-Ak9R_output.md` (23KB, verified by Task 16 validator)
  Scope: Total contacts, field inventory, pipeline stages, stale contacts (>30d), opportunity distribution, tag taxonomy, custom fields, capability matrix (18 tools)

- [x] **Task 16: Validate GHL audit** (HUMAN+AUTO)
  Status: DONE
  --> Depends on: Task 15
  Action: Chris opens **different** fresh session. Runs `/validate [candidate] [task-spec]`
  Rule: `makerSessionId` != `validatorSessionId` (maker-checker enforced)
  Gate: On PASS, sets `PHASE_0_AUDIT_PASSED`
  Completed: 2026-03-10 | validatorSessionId: quality-guard-20260310-004838246-bFye
  Verdict: PASS (Gate 1 PASS, Gate 2 PASS, Gate 3 PASS) | notificationStatus: SKIPPED_OPTIONAL

- [x] **Task 17: Metabolize audit results** (AUTO)
  Status: DONE
  --> Depends on: Task 16 (PASS verdict)
  Action: `/metabolize` runs in the validator session after PASS
  Updates: `revtry/vault/integrations/ghl.md` with verified capability matrix + audit facts
  Writes: `Phase 0 Triage Criteria` section with `Status: DRAFT`
  Rule: `/validate` must NOT update ghl.md directly — only `/metabolize` may
  Completed: 2026-03-10 | Executed in Task 16 validator session (quality-guard-20260310-004838246-bFye)
  Result: ghl.md updated with capability matrix + data quality stats. Triage criteria revised to v2 with Status: DRAFT.

- [x] **Task 18: Approve triage criteria** (HUMAN)
  Status: DONE
  --> Depends on: Task 17
  Completed: 2026-03-10 | Chris approved v2.1 criteria (5 gap fixes: EX-09 Smoke Pipeline, EX-10 Closed Won, 9 missing stages mapped, stageId matching note, Closed Won removed from score tier)
  Gate: `PHASE_0_TRIAGE_CRITERIA_APPROVED` = PASSED

- [x] **Task 19: Write triage task spec** (HUMAN+AUTO)
  Status: DONE
  --> Depends on: Task 18 (`PHASE_0_TRIAGE_CRITERIA_APPROVED` = PASSED)
  Completed: 2026-03-10 | Task spec: `revtry/registry/tasks/TASK-20260309-173228886-RMb2.md`
  TaskType: triage | 26 validation criteria | 10 exclusion rules | 3 read-only operation intents
  References approved Phase 0 Triage Criteria v2.1 in ghl.md

- [x] **Task 20: Execute GHL triage** (HUMAN+AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 19
  Agent: pipeline-ops | Task type: triage | Fallback: GHL-native signals (Phase 0)
  Output: `revtry/outputs/TASK-20260309-173228886-RMb2_output.json` + `_output.md`
  Results: 244 prioritized contacts (140 P1, 104 P2) from 355 contacts processed
  Exclusions: 96 excluded (79 test-seedlist, 8 closed-won, 6 no-email, 2 closed-lost, 1 domain-block)
  Data coverage: 269 opps from 9 pipelines (7 complete, 2 partial due to MCP pagination bug)
  makerSessionId: this session

- [x] **Task 21: Validate GHL triage** (HUMAN+AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 20
  Verdict: **PASS** — 26/26 validation criteria passed
  Note: Maker-checker ran in same session per user direction (deviation from spec)
  validatorSessionId: this session
  Gate: Sets `PHASE_0_TRIAGE_PASSED` = PASSED

- [x] **Task 22: Metabolize triage + send notification** (AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 21 (PASS verdict)
  Metabolized: `vault/feedback/agent_learnings.md` updated with 3 new entries (efficiency win, rule gap, escalation resolved)
  Output: `outputs/triage_summary_for_dani.md` — human-readable top-15 P1 + full stats
  notificationStatus: SKIPPED_OPTIONAL (Slack integration not configured; summary file ready for manual share)
  **HERO OUTCOME 1 COMPLETE**: Prioritized GHL follow-up list ready for Dani (140 P1 + 104 P2 contacts)

### Phase 0B Gates

| Gate ID | Status | Verified By | Depends On |
|---------|--------|-------------|------------|
| PHASE_0B_WORKSPACE_READY | PASSED | Tasks 4-13 (2026-03-07) | — |
| PHASE_0_AUDIT_PASSED | PASSED | quality-guard-20260310-004838246-bFye | Tasks 15-16 |
| PHASE_0_TRIAGE_CRITERIA_APPROVED | PASSED | 2026-03-10 | Task 18 (HUMAN) — Chris approved v2.1 |
| PHASE_0_TRIAGE_PASSED | PASSED | Task 21 validator — 26/26 criteria passed (2026-03-10) | Tasks 20-21 |

---

## Phase 1 — Campaign Draft Pipeline + Approval Dashboard

> **Hero Outcome**: "Here are 10 ICP-qualified campaign drafts ready to approve."
> Recon --> Enrichment --> Segmentation --> Campaign Craft --> FastAPI dashboard
> **Acceptance**: End-to-end pipeline produces ≥10 Tier 1/2 drafts, all 3 gates pass, Dani approves via dashboard
> **Code Status**: All pipeline code complete in `Project-RevTry/src/` (304 tests passing) as of 2026-03-09

### Tasks

- [x] **Task 23: Recon agent + Apollo integration** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/agents/recon_agent.py` + `src/integrations/apollo_client.py`
  Rate limit: 200 req/hr enforced

- [x] **Task 24: Enrichment agent + waterfall** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/agents/enrichment_agent.py` + `src/integrations/waterfall.py`
  Note: Apollo-only for Phase 1; BetterContact and Clay remain deferred

- [x] **Task 25: Segmentation agent + ICP scoring** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/agents/segmentation_agent.py`
  Scoring: 6-component base score + industry multiplier → T1/T2/T3/DQ

- [x] **Task 26: Campaign Craft agent** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/agents/campaign_craft_agent.py`
  Context: vault email_angles, signatures, proof_points, cta_library

- [x] **Task 27: Build FastAPI approval dashboard** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/dashboard/app.py` + `src/dashboard/storage.py`
  Endpoints: 12 routes — drafts CRUD + dispatch + status

- [x] **Task 28: End-to-end pipeline + 3-gate validation** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/pipeline/runner.py` + `src/validators/gate{1,2,3}_validator.py` + `src/validators/guards.py`
  Tests: 304 tests across 27 test files — all passing
  Config verification: dashboard startup now covered when `SCHEDULER_ENABLED=true` but APScheduler is unavailable

- [x] **Task 29: Rejection feedback loop** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/pipeline/feedback_processor.py`
  Flow: dashboard rejection → registry/pending_feedback/ → /metabolize → vault/feedback/

- [D] **Task 30: HeyReach warmup initiation** (HUMAN)
  Status: DEFERRED — warm-first sequencing; resume in Phase 4
  --> Depends on: Phase 3F complete, Phase 4 activation
  Action: Chris/Dani configure HeyReach campaigns (T1/T2/T3), begin 4-week LinkedIn warmup
  Record: Start date in `vault/integrations/heyreach.md`
  Note: Phase 4 LinkedIn dispatch gated on warmup_start + 28 days

- [x] **Task 31: Complete legacy vault migration** (HUMAN+AUTO)
  Status: DONE | Verified: 2026-03-11
  --> Depends on: `PHASE_0_TRIAGE_PASSED`
  Source: `revtry/migration/legacy_inventory.md`
  Migration completed during Phase 0B (2026-03-07). All vault files populated with freshness metadata.
  Verified: scoring_rules, tier_definitions, product split (5 files), email_angles all migrated.
  GEMINI.md: architecture-only system prompt — no business rules to extract (N/A).

- [~] **Task 32: First approved campaign batch** (HUMAN)
  Status: PARTIAL — GHL warm dispatch active; cold channels deferred
  --> Depends on: Tasks 28-29
  Action: Dani approves first batch of ≥10 Tier 1/2 drafts via dashboard
  Note: GHL warm email dispatch verified live. Instantly/HeyReach resume in Phase 4.
  **HERO OUTCOME 2 PARTIAL**: GHL warm drafts approved and dispatched; cold expansion deferred

### Phase 1 Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_1_PIPELINE_OPERATIONAL | PASSED | Tasks 23-28 (code complete) |
| PHASE_1_DASHBOARD_LIVE | PASSED | Task 27 (code complete) |
| PHASE_1_FIRST_BATCH_APPROVED | PARTIAL | Task 32 — GHL active; cold channels pending Phase 4 |

---

## Phase 2 — Outreach Dispatch Foundation

> **Hero Outcome**: GHL warm dispatch live with full safety infrastructure; cold channels deferred to Phase 4
> **Acceptance**: GHL sends land, circuit breaker wired, dedup enforced, KPI monitoring active with EMERGENCY_STOP
> **Code Status**: Core safety infrastructure complete; Instantly/HeyReach explicitly deferred

### Tasks

- [D] **Task 33: Instantly integration (cold email)** (AUTO)
  Status: DEFERRED — resumes in Phase 4 after warm dashboard validated
  --> Depends on: Phase 3F complete (`PHASE_3F_VERCEL_LIVE`)
  Note: Cold email ONLY via Instantly (never GHL) — channel routing hard block
  Limit on resume: Start at ≤5/day (RAMP)

- [D] **Task 34: HeyReach integration (LinkedIn)** (AUTO)
  Status: DEFERRED — resumes in Phase 4 after 28-day warmup
  --> Depends on: Task 30 (+28 days warmup), Phase 3F complete
  Note: LinkedIn dispatch gated on warmup_start + 28 days

- [x] **Task 35: Wire circuit breaker** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/pipeline/circuit_breaker.py`
  Coverage: GHL, Apollo, Instantly (stub), HeyReach (stub)
  Behavior: Trips on 3 consecutive failures, 30-minute cooldown, HALF_OPEN test recovery

- [x] **Task 36: Implement 3-layer dedup check** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/pipeline/dedup.py`
  Layers: hash + contact/channel window + GHL tag check
  Note: Warm dedup key = `ghlContactId` (canonical per PRD v2.6)

- [x] **Task 37: GHL warm dispatch + KPI monitoring** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  Files: `src/pipeline/dispatcher.py` + `src/pipeline/kpi_tracker.py` + `src/pipeline/rate_limiter.py`
  Note: Revenue Intel agent activation moved to Phase 5; KPI tracking is active baseline; failed sends now persist as `SEND_FAILED` instead of `DISPATCHED`
  Limits: RAMP ≤5/day GHL; SUPERVISED ≤25/day; FULL ≤100/day

- [x] **Task 38: Begin RAMP stage (GHL warm)** (HUMAN)
  Status: DONE — GHL warm dispatch active
  Note: Warm follow-up dispatch (Phase 3) consumes GHL budget first per PRD v2.6 shared-limit rule

- [ ] **Task 39: Validate EMERGENCY_STOP thresholds live** (HUMAN+AUTO)
  Status: NOT_STARTED
  --> Depends on: sustained warm dispatch in Phase 3
  Thresholds: Open rate <30% | 0 replies after 15 sends | Bounce >10% | Unsub >5%
  File: `src/pipeline/kpi_tracker.py`
  Action: Monitor first 15 warm sends; confirm EMERGENCY_STOP triggers correctly

### Phase 2 Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_2_GHL_DISPATCH_LIVE | PASSED | Tasks 35-38 (code + GHL active) |
| PHASE_2_SAFETY_WIRED | PASSED | Tasks 35-36 (circuit breaker + dedup complete) |
| PHASE_2_COLD_DISPATCH_LIVE | DEFERRED | Tasks 33-34 — Phase 4 |
| PHASE_2_RAMP_VALIDATED | NOT_STARTED | Task 39 |

---

## Phase 3A — GHL Conversation Reader + Data Models

> **Goal**: Scan GHL conversation history for active contacts; establish warm data models
> **Acceptance**: Scanner reads threads, filters 30 days, writes outputs/conversations/; all models compile

### Tasks

- [x] **Task 40: GHL client conversation read methods** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/integrations/ghl_client.py`
  Methods added: `search_conversations()`, `get_messages(limit=50)`, `get_contact()`
  Note: `_request()` updated with backward-compatible `params=` kwarg

- [x] **Task 41: Conversation data models** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/models/schemas.py`
  Added: `ConversationSentiment`, `ConversationStage`, `FollowUpTrigger`, `UrgencyLevel`, `ConversationMessage`, `ConversationThread`, `ContactConversationSummary`, `ConversationAnalysis`, `FollowUpDraft`, `DailyBriefing`
  All follow Pydantic v2 + camelCase alias pattern

- [x] **Task 42: GHL conversation scanner script** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/scripts/ghl_conversation_scanner.py`
  Behavior: Loads `outputs/ghl_followup_candidates.json` → fetches threads → filters 30d → writes `outputs/conversations/{id}.json` + `index.json`
  Rate limit: 0.5s between contacts (stays under 100 req/min GHL limit)
  Env: `DAILY_SCAN_BATCH_SIZE` (canonical), `MAX_SCAN_CONTACTS` (deprecated fallback only)

- [x] **Task 43: Phase 3A tests** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  File: `src/tests/test_conversation_scanner.py`
  Coverage: 15+ tests — GHL GET methods, message date filtering, scan_contact, scan_all_contacts, load_candidates, file output structure

- [x] **Task 44: Phase 3A model contract cleanup** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  Files: `src/models/schemas.py`, `src/models/__init__.py`, `src/scripts/ghl_conversation_scanner.py`
  Completed:
  - warm models exported from `src/models/__init__.py`
  - `sourceConversationId`, `triggerReason`, `SEND_FAILED`, and DailyBriefing skip/failure/cost counters aligned to PRD v2.6
  - scanner eligibility helpers added (`has_valid_email`, `select_primary_thread`, `compact_thread_messages`, `filter_eligible_summaries`)
  - `DAILY_SCAN_BATCH_SIZE` retained as canonical env; `MAX_SCAN_CONTACTS` remains deprecated fallback only
  Tests: `test_conversation_scanner.py` expanded for eligibility skips, primary-thread selection, compaction, and canonical env behavior

### Phase 3A Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3A_MODELS_COMPLETE | PASSED | Task 44 |
| PHASE_3A_SCANNER_VERIFIED | PASSED | Tasks 40-43 |

---

## Phase 3B — Sentiment Analysis Agent

> **Goal**: Classify each contact's conversation by sentiment, stage, trigger, and urgency
> **Acceptance**: Analyst agent produces `ConversationAnalysis` per contact; batch runs with per-contact isolation; no failed analysis auto-produces a draft

### Tasks

- [x] **Task 45: Shared Anthropic client wrapper** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 44 (`PHASE_3A_MODELS_COMPLETE`)
  File: `src/integrations/anthropic_client.py`
  Completed:
  - explicit `ANTHROPIC_API_KEY` guard
  - timeout + retry handling retained at client layer
  - one JSON repair retry retained on parse failure
  - lazy SDK initialization added for safer test/runtime behavior
  - invocation trace logging added via `trace_context`

- [x] **Task 46: Conversation analyst agent** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 45
  File: `src/agents/conversation_analyst_agent.py`
  LLM: Claude Haiku (`claude-haiku-4-5-20251001`)
  Input: `ContactConversationSummary`
  Output: `ConversationAnalysis` → written to `outputs/conversation_analysis/{contact_id}.json`
  Eligibility filter (pre-LLM): skip if `totalMessages == 0` OR no valid email
  Trigger classification (deterministic, pre-LLM):
  - `awaiting_our_response` — last message was inbound
  - `gone_cold` — two-way thread inactive for 7+ days
  - `no_reply` — last outbound 2+ days ago, no inbound since
  Batch method: `analyze_batch(summaries, max_concurrent=5)` with `asyncio.Semaphore`
  Context loaded: compacted primary-thread conversation only (latest 8 messages, chronological, trimmed; no email_angles.md, no ICP playbook)
  Cost: ~$0.05/day for 50 contacts

- [x] **Task 47: Phase 3B tests** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 46
  File: `src/tests/test_conversation_analyst.py`
  Coverage: mocked Anthropic client, trigger scenarios, eligibility skips, response parsing, per-contact failure isolation, file output serialization, batch concurrency

### Phase 3B Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3B_ANALYST_COMPLETE | PASSED | Tasks 45-47 |

---

## Phase 3C — Personalized Follow-Up Drafter + Storage

> **Goal**: Draft hyper-personalized follow-up emails referencing actual prior conversation exchanges
> **Acceptance**: Drafts reference conversation context; pass warm validators; stored correctly; no cold assumptions reused

### Tasks

- [x] **Task 48: Follow-up draft agent** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: `PHASE_3B_ANALYST_COMPLETE`
  File: `src/agents/followup_draft_agent.py`
  LLM: Claude Sonnet (`claude-sonnet-4-6`)
  Input: `ConversationAnalysis` + `ContactConversationSummary`
  Output: `FollowUpDraft` with `subject` + `body` + `sourceConversationId`
  Hard rules (in system prompt):
  - reference prior conversation explicitly (use actual topics/words from last 3 messages)
  - match tone to stage (engaged=warm, stalled=re-energizing, cold=gentle re-intro)
  - subject: <60 chars
  - body: <150 words
  - no banned openers: "hope this finds you well", "just checking in", "following up", "circling back"
  Context loaded: signatures + compliance + minimal CTA/proof — NO email_angles.md, NO ICP playbook
  Concurrency: max 3 concurrent (quality over throughput)
  Cost: ~$0.60/day for 50 contacts
  Tests: `src/tests/test_followup_draft_agent.py` covers prompt scope, valid draft generation, banned opener rejection, terminal-stage blocking, and batch failure isolation

- [x] **Task 49: Follow-up storage module** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 44 (`SEND_FAILED` in enum)
  File: `src/dashboard/followup_storage.py`
  Pattern: mirrors `src/dashboard/storage.py` exactly — separate module, same structure
  Storage: `outputs/followups/{draft_id}.json` + `outputs/followups/index.json`
  Functions: `save_followup_draft`, `get_followup_draft`, `list_followup_drafts`, `approve_followup_draft`, `reject_followup_draft`, `mark_followup_dispatched`, `mark_followup_send_failed`
  Rule: warm approval changes file state only — no cold GHL approval side effects
  Rule: only confirmed send success sets DISPATCHED; failed send sets SEND_FAILED
  Tests: `src/tests/test_followup_storage.py` covers save/get/index, ordering, approve/no-side-effect behavior, rejection feedback, dispatch success, and SEND_FAILED persistence

- [x] **Task 50: Warm-specific validators** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 48
  Files: `src/validators/followup_gate2_validator.py`, `src/validators/followup_gate3_validator.py`
  Note: Cold gate2/gate3 are not suitable for warm follow-up — separate warm profiles required
  Gate2 warm checks: CAN-SPAM compliance, no banned openers, subject length, no spam triggers
  Gate3 warm checks: conversation reference present, tone matches stage, prior contact acknowledged
  Tests: `src/tests/test_followup_validators.py` covers compliant pass, banned opener/footer failure, missing conversation reference, and cold-language rejection

- [x] **Task 51: Phase 3C tests** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Tasks 48-50
  Files: `src/tests/test_followup_draft_agent.py`, `src/tests/test_followup_storage.py`, `src/tests/test_followup_validators.py`
  Coverage: mocked Sonnet, prompt rules, vault context isolation, storage CRUD, SEND_FAILED status, warm validator checks

### Phase 3C Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3C_DRAFTER_COMPLETE | PASSED | Tasks 48-51 |

---

## Phase 3D — Warm Dashboard

> **Goal**: Give HoS a daily briefing view and follow-up queue with conversation context
> **Acceptance**: `GET /briefing` renders; `GET /followups` shows contact cards; `GET /` still works; approve/reject flow end-to-end

### Tasks

- [x] **Task 52: Briefing loader** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: `PHASE_3C_DRAFTER_COMPLETE`
  File: `src/dashboard/briefing_loader.py`
  Functions:
  - `load_daily_briefing()` → `DailyBriefing` (reads analyses + drafts, computes counts)
  - `load_followup_queue()` → list of combined analysis + draft data per contact
  - `load_contact_conversation(contact_id)` → full conversation context for detail view
  Tests: `src/tests/test_briefing_loader.py` covers persisted-briefing load, computed counts, queue assembly, and conversation detail loading

- [x] **Task 53: New dashboard routes** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 52
  File: `src/dashboard/app.py` (add routes — do not modify existing cold routes)
  Routes: `GET /briefing`, `GET /followups`, `GET /followups/{id}`, `POST /followups/{id}/approve`, `POST /followups/{id}/reject`, `POST /followups/batch/approve`, `POST /followups/batch/reject`, `POST /followups/generate`
  Compatibility: `GET /` stays backward-compatible; `GET /cold-drafts` alias added
  Scheduler: lifespan hook added — `start_scheduler()` called only if `SCHEDULER_ENABLED=true` and scheduler module exists
  Note: `POST /followups/generate` was activated in Task 61 as the manual warm pipeline trigger

- [x] **Task 54: New Jinja2 templates** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 53
  Files: `src/dashboard/templates/briefing.html`, `src/dashboard/templates/followup_list.html`, `src/dashboard/templates/followup_detail.html`
  Briefing: urgency stat cards (HOT/WARM/COOLING), trigger breakdown, draft queue count, link to /followups
  Followup list: contact cards with sentiment/stage/urgency badges, days since last activity, conversation snippet, recommended action, [View Draft] [Approve] [Reject] buttons
  Followup detail: conversation history panel (inbound/outbound color-coded, scrollable), analysis badges, drafted email preview, approve/reject forms

- [x] **Task 55: Update base.html nav** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Task 54
  File: `src/dashboard/templates/base.html`
  New nav: Briefing (`/briefing`) / Follow-Ups (`/followups`) / Cold Drafts (`/`) / Dispatch (`/dispatch`)

- [x] **Task 56: Phase 3D tests + existing test updates** (AUTO)
  Status: DONE | Code complete: 2026-03-08
  --> Depends on: Tasks 52-55
  Updates: `src/tests/test_dashboard.py` — verify `GET /` still works; add tests for all new routes
  Note: existing test assertions must not break — no breaking root-route change
  Validation: `python -m pytest tests -q` — 267 passed, 2 warnings (plus recurring post-run Python 3.13 access-violation trace after exit code 0)

### Phase 3D Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3D_DASHBOARD_WARM | PASSED | Tasks 52-56 |
| PHASE_3D_BACKWARD_COMPAT | PASSED | Task 56 (GET / still passes) |

---

## Phase 3E — Warm Orchestrator + Deploy-Readiness Hardening

> **Goal**: Automated daily scan → analyze → draft pipeline with safety-checked warm dispatch
> **Acceptance**: Manual flow works end-to-end before scheduler is enabled; unified warm-first dispatch is live; deployed mode is auth-protected, warm-only, and backed by Postgres-safe persistence; add-only tag hotfix is validated live on a smoke contact before Vercel work resumes

### Tasks

- [x] **Task 57: Follow-up orchestrator** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: `PHASE_3D_DASHBOARD_WARM`
  File: `src/pipeline/followup_orchestrator.py`
  Pipeline: abort if GHL circuit breaker OPEN → load candidates → scan conversations → filter eligible (totalMessages>0, valid email) → analyze batch (Haiku) → filter actionable → draft batch (Sonnet) → save drafts → compute DailyBriefing
  Safety: NEVER dispatches — only generates drafts for HoS review
  Returns: dict with scanned/analyzed/drafted/skipped/failed counts + estimatedCostUsd
  Behaviors implemented:
  - blocks immediately when the shared GHL circuit breaker is OPEN
  - persists `outputs/briefings/{YYYY-MM-DD}.json`
  - skips duplicate same-day runs unless `force=true`
  - validates warm drafts through follow-up Gate 2 and Gate 3 before saving
  - records per-run trace logs in `outputs/logs/`
  Tests: `src/tests/test_followup_orchestrator.py` covers breaker abort, no-candidate empty briefing, successful briefing+draft persistence, and invalid draft rejection before storage

- [x] **Task 58: Follow-up dispatcher** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 57
  File: `src/pipeline/followup_dispatcher.py`
  Pattern: mirrors `src/pipeline/dispatcher.py` — same 6-check safety chain
  Safety chain: deferred channel check → tier check → GHL rate limit (shared budget) → GHL circuit breaker (shared) → dedup (ghlContactId as canonical key) → GHL send
  On success: `mark_followup_dispatched()`
  On failure: `mark_followup_send_failed()` — NEVER leaves failed send as DISPATCHED
  Implemented warm rules:
  - canonical dedup identity is `ghlContactId` for hash/window/tag checks
  - approved warm drafts dispatch through shared `ghl` rate limiter + shared `ghl` circuit breaker
  - missing `ghlContactId` or missing email marks the warm draft `SEND_FAILED`
  Tests: `src/tests/test_followup_dispatcher.py` covers success, no-approved no-op, rate-limit skip, breaker skip, canonical dedup identity, missing-ID failure, and send-failure persistence

- [x] **Task 59: APScheduler cron** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 57
  File: `src/pipeline/scheduler.py`
  Schedule: `CronTrigger(hour=6, minute=0, timezone="America/Chicago")` = 6 AM America/Chicago
  Default: disabled — `SCHEDULER_ENABLED=false`
  Rule: manual flow via `POST /followups/generate` must work before scheduler is relied on
  Implemented:
  - persists scheduler state in `REGISTRY_DIR/followup_scheduler_state.json`
  - blocks overlapping runs and duplicate same-day runs unless `force=true`
  - exposes `start_scheduler()` / `stop_scheduler()` plus a sync wrapper for APScheduler jobs
  - degrades cleanly when APScheduler is not installed so dashboard startup does not crash
  Tests: `src/tests/test_scheduler.py` covers 6 AM America/Chicago config, local business-date handling, overlap protection, forced reruns, and job registration

- [x] **Task 59A: Vercel Cron Job for daily pipeline** (AUTO)
  Status: DONE | Code complete: 2026-03-11
  --> Depends on: Task 59
  Problem: APScheduler requires a long-running process; Vercel serverless functions spin down between requests.
  Solution: Vercel Cron Job (`vercel.json` crons config) triggers `GET /api/cron/warm-pipeline` daily at 12:00 UTC (6:00 AM CT).
  Files: `src/dashboard/app.py` (cron endpoint + CRON_SECRET auth), `vercel.json` (crons + maxDuration=300)
  Implemented:
  - `GET /api/cron/warm-pipeline` endpoint with `CRON_SECRET` Bearer token validation
  - `vercel.json` crons config: `0 12 * * *` (daily 6 AM CT)
  - `maxDuration: 300` for Vercel Pro (5-min pipeline timeout)
  - Vercel Pro plan activated ($20/mo, $1.87/$20.00 used)
  - Pipeline refresh run 2026-03-11: 50 candidates → 39 eligible → 27 saved drafts ($0.38)
  Tests: `src/tests/test_dashboard.py::TestCronWarmPipeline` — 4 tests (missing secret, bad token, valid trigger, pipeline failure)

- [x] **Task 60: Environment contract finalization** (AUTO)
  Status: DONE | Config complete: 2026-03-09
  --> Depends on: Tasks 57-59
  File: `Project-RevTry/.env.example`
  Add: `ANTHROPIC_API_KEY`, `DAILY_SCAN_BATCH_SIZE=50`, `FOLLOWUP_SCAN_DAYS=30`, `SCHEDULER_ENABLED=false`, `SCHEDULER_TIMEZONE=America/Chicago`
  Deprecate: `MAX_SCAN_CONTACTS` (document as transitional alias only)
  Implemented:
  - added the canonical warm Phase 3 env vars to the root `.env.example`
  - documented `MAX_SCAN_CONTACTS` as a deprecated alias only
  - kept the env contract aligned with the current scanner, orchestrator, scheduler, and Anthropic client code paths

- [x] **Task 61: Phase 3E tests + full validation run** (AUTO)
  Status: DONE | Validation complete: 2026-03-09
  --> Depends on: Tasks 57-60
  Files: `src/dashboard/app.py`, `src/tests/test_dashboard.py`, `src/tests/test_followup_orchestrator.py`
  Coverage:
  - manual `POST /followups/generate` route now calls `run_followup_orchestrator(task_id=\"warm-followup-manual\")`
  - blocking orchestrator states (`blocked_missing_anthropic_api_key`, `circuit_open`) return HTTP 503
  - dashboard startup remains safe when `SCHEDULER_ENABLED=true` but APScheduler is unavailable
  - orchestrator/dispatcher/scheduler/dashboard slice passes together
  Final validation: `python -m pytest tests -q` — all 286 tests pass
  Manual flow verification: `POST /followups/generate` now triggers the warm generate pipeline instead of returning the Phase 3E placeholder 503

- [x] **Task 61A: Phase 3E deployment-readiness truth sync** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61
  Files: `Project-RevTry/.claude/PRD.md`, `Project-RevTry/CLAUDE.md`, `Project-RevTry/.agents/plans/phase-3-conversation-followup-handoff.md`, `Project-RevTry/revtry/registry/MASTER-TASKS.md`
  Completed:
  - reopened Phase 3E as a deploy-readiness hardening phase instead of treating local warm generation as deployment-ready
  - inserted the new `PHASE_3E_GENERATION_COMPLETE` and `PHASE_3E_DEPLOY_READY` gate chain
  - kept Task 3B visible as a required parallel runtime blocker

- [x] **Task 61B: Unified warm-first dispatch integration** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Tasks 58, 61
  Files: `src/dashboard/app.py`, `src/dashboard/templates/dispatch.html`, `src/tests/test_dashboard.py`
  Completed:
  - `GET /dispatch` now renders a unified warm/cold operational view
  - `POST /dispatch/run` now dispatches warm follow-ups first, then cold drafts
  - one shared `DailyRateLimiter` and one shared `CircuitBreaker` are used across both dispatch paths
  - warm-only mode hides cold sections and skips cold dispatch entirely

- [x] **Task 61C: Dashboard auth + warm-only deployed mode** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 61A
  Files: `src/dashboard/auth.py`, `src/dashboard/app.py`, `src/dashboard/templates/base.html`, `src/tests/test_dashboard.py`
  Completed:
  - added HTTP Basic Auth for all dashboard and mutating routes when enabled
  - added unauthenticated `GET /healthz`
  - added `WARM_ONLY_MODE` behavior: `/` redirects to `/briefing`, cold routes return 404, nav hides cold surfaces
  - startup now fails fast if warm-only mode is configured without the required deployed storage backend or if auth is enabled without credentials

- [x] **Task 61D: Warm deployed persistence backend** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 61A
  Files: `src/persistence/{base.py,file_store.py,postgres_store.py,factory.py,schema.sql}`, `src/dashboard/followup_storage.py`, `src/dashboard/briefing_loader.py`, `src/pipeline/{rate_limiter.py,circuit_breaker.py,dedup.py}`, `src/scripts/ghl_conversation_scanner.py`, `src/utils/trace_logger.py`
  Completed:
  - introduced a storage backend abstraction with `file` and `postgres` implementations
  - kept file-backed local dev behavior intact
  - required `STORAGE_BACKEND=postgres` for warm-only deployed mode
  - moved warm drafts, briefings, conversation snapshots, shared limiter state, circuit-breaker state, dedup hashes, and dispatch logs behind backend-selected persistence
  - made deployed trace logging stdout-based instead of file-only

- [x] **Task 61E: Warm idempotency + timezone + env hardening** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Tasks 57-60
  Files: `src/utils/business_time.py`, `src/agents/followup_draft_agent.py`, `src/models/schemas.py`, `src/dashboard/briefing_loader.py`, `src/pipeline/{followup_orchestrator.py,rate_limiter.py,scheduler.py}`, `src/integrations/ghl_client.py`, `Project-RevTry/.env.example`
  Completed:
  - follow-up drafts are now idempotent per business date via deterministic IDs
  - `FollowUpDraft` now carries `businessDate` and `generationRunId`
  - business-date logic is standardized on `America/Chicago`
  - `GHLClient` now fails fast on missing `GHL_API_KEY` or `GHL_LOCATION_ID`
  - added deploy-readiness env vars: dashboard auth, storage backend, database URL, warm-only mode

- [x] **Task 61F: Phase 3E deploy-readiness validation** (AUTO)
  Status: DONE | Validation complete: 2026-03-09
  --> Depends on: Tasks 61B-61E
  Files: `src/tests/test_dashboard.py`, `src/tests/test_followup_draft_agent.py`, `src/tests/test_followup_storage.py`, `src/tests/test_followup_orchestrator.py`, `src/tests/test_briefing_loader.py`, `src/tests/test_ghl_client.py`, `src/tests/test_persistence_backend.py`
  Validation:
  - auth challenge + warm-only route behavior verified
  - unified `/dispatch/run` payload verified
  - same-day reruns overwrite deterministic warm draft IDs; next-day reruns create new drafts
  - default briefing date and scheduler business date behavior verified
  - Postgres backend contract verified with mocked connection layer
  - full suite passes: `python -m pytest tests -q` → **304 passed**

- [x] **Task 61G: Freeze non-essential GHL writes after tag-safety incident** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61F
  Files: `CLAUDE.md`, `revtry/guardrails/hard_blocks.md`, `revtry/vault/integrations/ghl.md`
  Completed:
  - documented the temporary write freeze after the tag-removal incident
  - narrowed allowed live writes to read-only work plus designated smoke validations
  - made add-only tag policy explicit in runtime guardrails and operator-facing GHL guidance

- [x] **Task 61H: Harden GHL client to forbid tag replacement in upsert/update** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 61G
  Files: `src/integrations/ghl_client.py`, `src/tests/test_ghl_client.py`
  Completed:
  - `GHLClient.upsert_contact(...)` now rejects `tags`
  - added `UnsafeContactMutationError`
  - added additive `add_contact_tag(...)` / `add_contact_tags(...)`
  - added regression tests proving upsert no longer sends tag arrays

- [x] **Task 61I: Migrate approval/enrichment flows to additive tag writes only** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 61H
  Files: `src/integrations/ghl_service.py`, `src/scripts/ghl_enrich.py`, `src/tests/test_ghl_client.py`, `src/tests/test_ghl_enrich.py`
  Completed:
  - approval flow now upserts without tags and appends `revtry-approved` separately
  - enrichment writeback now upserts without tags and appends `revtry-enriched` separately
  - regression tests now assert additive tagging behavior in both flows

- [x] **Task 61J: Harden external MCP update_contact to reject tag mutation** (AUTO)
  Status: DONE | Code complete: 2026-03-09
  --> Depends on: Task 61H
  File: `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`
  Completed:
  - `ghl_update_contact` now rejects tag fields and any blocked contact field outside the allowlist
  - `ghl_create_contact` / `ghl_bulk_create_contacts` now reject tag payloads
  - tool descriptions now state that `ghl_add_tag` is the only permitted tag mutation path
  Validation: `python -m py_compile` + inline helper assertions both passed

- [x] **Task 61K: Add tag-preservation regression tests** (AUTO)
  Status: DONE | Validation complete: 2026-03-09
  --> Depends on: Tasks 61H-61J
  Files: `src/tests/test_ghl_client.py`, `src/tests/test_ghl_enrich.py`
  Completed:
  - added rejection test for tag mutation through contact upsert
  - added additive-tag helper coverage
  - added approval/enrichment regression assertions that tags are appended separately
  - added failure-path coverage for additive tag write errors
  Validation: focused slice passed — `python -m pytest src/tests/test_ghl_client.py src/tests/test_ghl_enrich.py -q` → **28 passed**

- [x] **Task 61L: Update runtime prompt + PRD + guardrails for add-only tag policy** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61K
  Files: `CLAUDE.md`, `revtry/guardrails/hard_blocks.md`, `revtry/guardrails/safe_contact_write_fields.md`, `.claude/commands/{plan-task,execute}.md`, `revtry/agents/orchestrator/task_spec_template.md`, `Project-RevTry/.claude/PRD.md`, `revtry/vault/integrations/ghl.md`
  Completed:
  - added explicit hard blocks for tag removal/replacement and unsafe contact field writes
  - added the contact write allowlist contract and add-only tag policy to runtime prompts and task-spec scaffolding
  - updated the PRD so Phase 3F remains blocked until the tag-safety hotfix is validated

- [x] **Task 61M: Validate hotfix against safe smoke contact before resuming normal dev** (HUMAN+AUTO)
  Status: DONE | Live smoke completed: 2026-03-09
  --> Depends on: Tasks 61H-61L
  Files: `Project-RevTry/.env`, `src/integrations/ghl_client.py`, `revtry/recovery/tag_safety_hotfix_live_smoke_2026-03-09.json`
  Validation completed:
  - local focused regression slice passed
  - external MCP compile + helper validation passed
  - full suite passed after recovery tooling landed: `python -m pytest src/tests -q`
  Live smoke proved:
  - plain `upsert_contact(...)` preserved an existing baseline tag on the smoke contact
  - additive tag append added a new tag without shrinking the contact's tag set
  Evidence:
  - smoke contact: `4XFxvKc2zUnnzX0zd58j`
  - baseline preserved: `revtry-smoke-preserve-baseline-20260309`
  - append added: `revtry-smoke-append-check-20260309`

- [x] **Task 61N: Build tag-restore manifest from audit CSV** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61M
  Files: `src/scripts/restore_contact_tags_from_audit.py`, `revtry/recovery/tag_restore_manifest_2026-03-08.json`
  Completed:
  - parsed the audit CSV at `C:\Users\ADMIN\Downloads\GHL Audit Logs for contact tags that were removed without Permission. - Sheet1 (1).csv`
  - generated a deterministic manifest with `75` unique contacts and exact per-contact `removedTags`
  - preserved original tag strings exactly; no normalization or inferred tags

- [x] **Task 61O: Run dry-run restore diff against current GHL tag state** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61N
  Files: `revtry/recovery/tag_restore_dry_run_report_2026-03-08.md`
  Completed:
  - read all `75` affected contacts successfully from GHL
  - computed per-contact `missingTags` vs `alreadyPresentTags`
  - confirmed additive-only restore scope with no contact-ID ambiguity
  Dry-run outcome:
  - `75` READY_TO_RESTORE
  - `0` NO_OP
  - `0` CONTACT_MISSING / READ_FAILED

- [x] **Task 61P: Execute additive tag restore from approved manifest** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61O
  Files: `revtry/recovery/tag_restore_execution_log_2026-03-08.json`, `revtry/recovery/tag_restore_execution_log_2026-03-08_smoke_xYe59JyAA8OBQNMnUHnX.json`
  Completed:
  - ran a one-contact smoke restore first on `xYe59JyAA8OBQNMnUHnX` (Will Hovey)
  - then executed the full additive restore in conservative batches
  - used only `add_contact_tags(...)`; no upsert or generic contact update path was used
  Restore outcome:
  - one-contact smoke: PASS
  - full restore execution entries: `74` (one contact already satisfied from the smoke pass)
  - no batch stop condition was triggered

- [x] **Task 61Q: Run post-restore verification and archive evidence** (AUTO)
  Status: DONE | Completed: 2026-03-09
  --> Depends on: Task 61P
  Files: `revtry/recovery/tag_restore_post_verify_2026-03-08.md`
  Completed:
  - re-read all `75` contacts after restore
  - verified every contact's current tags are a superset of the exact tags listed in the audit CSV
  Verification outcome:
  - `PASS=75`
  - `PARTIAL=0`
  - `FAIL=0`

### Phase 3E Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3E_ORCHESTRATOR_COMPLETE | PASSED | Tasks 57-61 |
| PHASE_3E_MANUAL_FLOW_VERIFIED | PASSED | Task 61 |
| PHASE_3E_GENERATION_COMPLETE | PASSED | Tasks 57-61 |
| PHASE_3E_DEPLOY_READY | PASSED | Tasks 61A-61F |
| PHASE_3E_TAG_SAFETY_HOTFIX | PASSED | Tasks 61G-61M |
| PHASE_3E_TAG_RECOVERY_COMPLETE | PASSED | Tasks 61N-61Q |
| PHASE_3_WARM_COMPLETE | PASSED | `PHASE_3E_GENERATION_COMPLETE` + `PHASE_3E_DEPLOY_READY` + `PHASE_3E_TAG_SAFETY_HOTFIX` + `PHASE_3E_TAG_RECOVERY_COMPLETE` |

---

## Phase 3F — Vercel Deployment (Warm Dashboard)

> **Goal**: Warm dashboard accessible by Dani via web URL — no local server required
> **Acceptance**: `GET /briefing` and `GET /followups` accessible at Vercel URL; approve/reject flow works remotely
> **Starts**: Immediately after `PHASE_3E_DEPLOY_READY`, `PHASE_3E_TAG_SAFETY_HOTFIX`, and `PHASE_3E_TAG_RECOVERY_COMPLETE`

### Tasks

- [x] **Task 62: Vercel deployment config + env hardening** (HUMAN+AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: `PHASE_3E_DEPLOY_READY`, `PHASE_3E_TAG_SAFETY_HOTFIX`, `PHASE_3E_TAG_RECOVERY_COMPLETE`
  Action: Configure Vercel project, set all env vars, deploy warm dashboard
  Completed:
  - Vercel project created at `caio-rev-try.vercel.app`
  - `api/index.py` entry point created (adds `src/` to sys.path, imports FastAPI app)
  - `vercel.json` routes all traffic to `api/index.py` via `@vercel/python` builder
  - Root `requirements.txt` created with all production dependencies
  - Env vars configured on Vercel: `GHL_API_KEY`, `GHL_LOCATION_ID`, `ANTHROPIC_API_KEY`, `DASHBOARD_AUTH_ENABLED=true`, `DASHBOARD_BASIC_AUTH_USER`, `DASHBOARD_BASIC_AUTH_PASS`, `STORAGE_BACKEND=postgres`, `DATABASE_URL`, `WARM_ONLY_MODE=true`, `SCHEDULER_ENABLED=false`
  - HTTP Basic Auth working — login prompt appears
  - Dashboard accessible and rendering (shows zeros — pipeline not yet run)
  Commits:
  - `de10c48` — feat: Phases 2-3E + Vercel deployment config (60 files)
  - `282db25` — fix: add python-multipart dependency for FastAPI Form() support
  - `2841253` — fix: handle DB connection errors gracefully in /briefing and /followups
  Issues resolved:
  - 404 NOT_FOUND: 60 source files not committed to git (fixed)
  - 500 FUNCTION_INVOCATION_FAILED: `python-multipart` missing (fixed)
  - 500 on /briefing after login: unhandled DB connection errors (fixed with try/except)
  Remaining sub-tasks: see Tasks 62A-62C below

- [x] **Task 62A: DB connection hardening** (AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 62
  Action: Add `connect_timeout=5` to `psycopg.connect()` in `postgres_store.py:38` to prevent Neon cold-start hangs on Vercel's 10s Lambda timeout
  File: `src/persistence/postgres_store.py` line 38
  Validation: `src/tests/test_persistence_backend.py` asserts all Postgres connects use `connect_timeout=5`

- [x] **Task 62B: Healthz DB probe** (AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 62
  Action: Add `SELECT 1` DB connectivity check to `GET /healthz` when `STORAGE_BACKEND=postgres`; return `{"status":"ok","db":"connected"}` or `{"status":"degraded","db":"error","detail":"..."}`
  File: `src/dashboard/app.py` — healthz handler
  Validation: `src/tests/test_dashboard.py` covers healthy and degraded Postgres probe responses

- [x] **Task 62C: Error handling for remaining unprotected routes** (AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 62
  Action: Add try/except with graceful fallbacks to routes that still crash on DB errors:
  - `GET /followups/{id}` — return 404 page on DB error
  - `GET /dispatch` — return empty dispatch view on DB error
  - `GET /dispatch/status` — return empty JSON on DB error
  - `POST /dispatch/run` — return error JSON on DB error
  - `POST /followups/generate` — return structured 503 JSON on unexpected pipeline startup failure
  File: `src/dashboard/app.py`
  Validation: `src/tests/test_dashboard.py` covers graceful fallbacks for all five routes

- [x] **Task 62D0: Candidate-source fallback hardening** (AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Task 62
  Action: Teach the warm pipeline to fall back to the latest validated `revtry/outputs/TASK-*_output.json` triage output when `outputs/ghl_followup_candidates.json` is missing, then write a normalized cache artifact for later runs
  Files:
  - `src/scripts/ghl_conversation_scanner.py`
  - `src/tests/test_conversation_scanner.py`
  - `src/utils/vault_loader.py`
  - `src/tests/test_vault_loader.py`
  Output: `outputs/ghl_followup_candidates.json` generated automatically from triage fallback when needed
  Validation: `src/tests/test_conversation_scanner.py` verifies fallback mapping, ordering, cache write, and batch-size behavior; `src/tests/test_vault_loader.py` verifies repo-local `revtry/vault` fallback so deployed/local generation does not depend on manually setting `VAULT_DIR`

- [x] **Task 62D: Run warm pipeline against real GHL data** (HUMAN+AUTO)
  Status: DONE | Completed: 2026-03-10
  --> Depends on: Tasks 62A-62C, Task 62D0
  Action: Ran the follow-up orchestrator against Neon Postgres DB to populate real data
  Completed:
  - Pipeline executed successfully — real contacts scanned, conversations analyzed, drafts generated
  - Dashboard at `caio-rev-try.vercel.app/followups` shows 20+ real contacts with urgency/sentiment/stage data
  - All contacts received PENDING drafts (orchestrator generates drafts for all actionable analyses)
  - `/briefing` shows real contact counts and urgency breakdown
  Note: NEVER send real emails — drafts are for review only

- [x] **Task 63: Route + approval flow verification** (HUMAN+AUTO)
  Status: DONE | Started: 2026-03-10 | Completed: 2026-03-10
  --> Depends on: Task 62D
  Action: Verify all warm routes show real data at Vercel URL; test approve/reject end-to-end from remote browser
  Checks: `GET /briefing` (shows real counts), `GET /followups` (shows contact cards), `GET /followups/{id}` (shows full draft), `POST /followups/{id}/approve`, `POST /followups/{id}/reject`, `GET /dispatch`
  Completed:
  - All warm routes verified with real data on Vercel (28 drafts populated via local pipeline run)
  - `/followups` shows 28 contacts with View Draft links
  - `/dispatch` shows circuit breaker healthy state + dry-run banner when DISPATCH_DRY_RUN=true
  - DISPATCH_DRY_RUN feature added (commit 6a9a168) — logs email payload without sending real emails
  - Edited draft content verified to flow through to dispatch (not originals) via unit tests
  - 375 tests passing including 3 new dry-run tests
  - Non-functional Re-Generate/Refresh buttons removed from /briefing (commit 7a88481)

- [x] **Task 63A: Transition from dry-run to live dispatch** (HUMAN)
  Status: DONE | Completed: 2026-03-11
  --> Depends on: Task 64
  Dani approved 5 drafts remotely. User flipped DISPATCH_DRY_RUN=false on Vercel and redeployed.
  Live dispatch is now active — approved drafts will send real emails via GHL.

- [x] **Task 64: Dani remote access verification** (HUMAN)
  Status: DONE | Completed: 2026-03-11
  --> Depends on: Task 63
  Dani accessed `caio-rev-try.vercel.app` remotely, reviewed warm follow-up drafts, and approved 5 contacts.
  Gate: Sets `PHASE_3F_VERCEL_LIVE` → PASSED

### Phase 3F Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3F_DEPLOYMENT_LIVE | PASSED | Task 62 — dashboard accessible at `caio-rev-try.vercel.app` |
| PHASE_3F_CODE_HARDENED | PASSED | Tasks 62A-62C |
| PHASE_3F_CANDIDATE_SOURCE_READY | PASSED | Task 62D0 |
| PHASE_3F_PIPELINE_POPULATED | PASSED | Task 62D — real data visible on dashboard |
| PHASE_3F_VERCEL_LIVE | PASSED (2026-03-11) | Tasks 62-64 — Dani verified remote access, approved 5 drafts, live dispatch enabled |

---

## Phase 3G — Agentic Engineering Enhancements

> **Goal**: Improve warm pipeline measurement, validation quality, and developer workflow
> **Starts**: After `PHASE_3F_VERCEL_LIVE`
> **Spec**: `docs/superpowers/specs/2026-03-11-phase-3g-agentic-enhancements-spec.md`

### Batch 1: Runtime — Measurement Foundation

- [ ] **Task 75: Capture human edit diffs on follow-up drafts** (AUTO)
  Status: NOT_STARTED
  --> Depends on: `PHASE_3F_VERCEL_LIVE`
  Files: `src/dashboard/app.py` (L521), `src/models/schemas.py`, persistence layer
  Metric: Edit rate (% of approved drafts that were edited)

- [ ] **Task 76: Add storage-derived pipeline metrics to KPI tracker** (AUTO)
  Status: NOT_STARTED
  --> Depends on: `PHASE_3F_VERCEL_LIVE`
  Files: `src/pipeline/kpi_tracker.py` (L25-38)
  Metric: 6 new draft-lifecycle counts (generated, edited, approved, dispatched, rejected, approval_rate)

- [ ] **Task 77: Shadow-log confidence on ConversationAnalysis** (AUTO)
  Status: NOT_STARTED
  --> Depends on: `PHASE_3F_VERCEL_LIVE`
  Files: `src/models/schemas.py` (L359), `src/agents/conversation_analyst_agent.py`
  Note: Shadow telemetry ONLY — no routing, filtering, or display changes

### Batch 2: Slash-Command — Validation & Specification Quality

- [ ] **Task 78: Output-only validation with evidence packets** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Tasks 75-77
  Files: `.claude/commands/validate.md`

- [ ] **Task 79: Prompt contracts with complexity gate** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Task 78
  Files: `.claude/commands/plan-task.md`

- [ ] **Task 80: Self-modifying candidate rules in /metabolize** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Task 78
  Files: `.claude/commands/metabolize.md`, `revtry/memory/candidate_rules.md` (new)

### Batch 3: Runtime — Enhanced Retry

- [ ] **Task 81: Feed gate failure context into existing retry** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Tasks 75-77 (need metrics baseline)
  Files: `src/pipeline/followup_orchestrator.py` (L342-363)

### Batch 4: CLAUDE.md Token Audit

- [x] **Task 82: CLAUDE.md token audit and compaction-resilience** (AUTO)
  Status: DONE | Completed: 2026-03-11
  --> Depends on: Tasks 75-77 (executed early — documentation-only, zero runtime risk)
  Files: `Project-RevTry/CLAUDE.md`
  Results: 282 → 146 lines (48% reduction)
  Anchored: tag safety rules, gate-failure behavior, DnD filtering, dispatch safety chain
  Moved to vault: persistence model, code structure, deployment config, validation commands, env contract
  Created: 5 new vault files in `vault/integrations/` and `vault/operations/`

### Phase 3G Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_3G_MEASUREMENT_BASELINE | NOT_STARTED | Tasks 75-77 |
| PHASE_3G_SLASH_COMMANDS_ENHANCED | NOT_STARTED | Tasks 78-80 |
| PHASE_3G_ENHANCED_RETRY | NOT_STARTED | Task 81 |

---

## Phase 4 — Cold-Outbound Expansion

> **Goal**: Reactivate Instantly cold email and HeyReach LinkedIn after warm path is validated and deployed
> **Acceptance**: Cold email sends via Instantly; LinkedIn via HeyReach; both share GHL safety infrastructure; warm budget remains priority
> **Starts**: After `PHASE_3F_VERCEL_LIVE`

### Tasks

- [ ] **Task 65: Initiate HeyReach 28-day warmup** (HUMAN)
  Status: NOT_STARTED
  --> Depends on: `PHASE_3F_VERCEL_LIVE` (can start in parallel with Phase 4 prep)
  Action: Chris/Dani configure HeyReach campaigns (T1/T2/T3), begin 4-week LinkedIn warmup
  Record: Start date in `vault/integrations/heyreach.md`
  Gate: LinkedIn dispatch gated on warmup_start + 28 days

- [ ] **Task 66: Reactivate Instantly integration** (AUTO)
  Status: NOT_STARTED
  --> Depends on: `PHASE_3F_VERCEL_LIVE`
  File: `src/integrations/instantly_client.py` (existing stub — activate and test)
  File: `src/pipeline/dispatcher.py` (remove DEFERRED skip for `instantly` channel)
  Limit: ≤5/day RAMP; cold email ONLY via Instantly (never GHL) — channel routing hard block

- [ ] **Task 67: Reactivate HeyReach integration** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Task 65 (+28 days warmup)
  File: `src/integrations/heyreach_client.py` (existing stub — activate and test)
  File: `src/pipeline/dispatcher.py` (remove DEFERRED skip for `heyreach` channel)
  Limit: ≤5/day RAMP; LinkedIn sequencing per vault/integrations/heyreach.md

- [ ] **Task 68: Cold expansion validation** (HUMAN+AUTO)
  Status: NOT_STARTED
  --> Depends on: Tasks 66-67
  Action: Chris + Dani approve first cold batch; confirm Instantly sends land, HeyReach touches fire
  Gate: Sets `PHASE_4_COLD_ACTIVE`

### Phase 4 Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_4_COLD_ACTIVE | NOT_STARTED | Tasks 65-68 (HUMAN) |

---

## Phase 5 — Revenue Intelligence + Autonomy Graduation

> **Hero Outcome**: Self-improving revenue operations system with earned autonomy
> **Acceptance**: Revenue Intel weekly reports live; autonomy graduated Ramp → Supervised → Full
> **Depends on**: Validated outbound history from both warm (Phase 3) and cold (Phase 4)

### Tasks

- [ ] **Task 69: Revenue Intel agent** (AUTO)
  Status: NOT_STARTED
  --> Depends on: `PHASE_4_COLD_ACTIVE`, sustained dispatch history (warm + cold)
  Agent: revenue-intel
  Output: Weekly KPI reports — open rate, reply rate, bounce rate, unsub rate, campaign count, date range
  Access: Read-only vault access; reads `outputs/` dispatch history; no write to vault except via `/metabolize`

- [ ] **Task 70: Full compounding metabolism** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Task 69
  Action: `/metabolize` processes every win and failure automatically
  Verification: `vault/feedback/agent_learnings.md` has ≥5 entries after Phase 5 week 1

- [ ] **Task 71: Autonomy graduation — RAMP to Supervised** (HUMAN)
  Status: NOT_STARTED
  --> Depends on: Task 69 (+14 days sustained KPIs)
  Criteria: Open ≥50% AND reply ≥8% AND bounce <5% sustained for 14 consecutive days
  Approval: Chris reviews KPIs and explicitly approves
  New limits: 25/day, all tiers, Dani approves via dashboard (no Chris approval needed per send)

- [ ] **Task 72: Autonomy graduation — Supervised to Full Autonomy** (HUMAN)
  Status: NOT_STARTED
  --> Depends on: Task 71 (+30 days sustained KPIs)
  Criteria: Same metrics sustained for 30 additional days
  Approval: Chris + Dani both approve
  New limits: 25/day, all tiers + cadence, human review for new campaigns only

- [ ] **Task 73: Vercel dashboard expansion** (AUTO)
  Status: NOT_STARTED
  --> Depends on: Tasks 69-70
  Action: Add Revenue Intel views to Vercel dashboard; cold draft approval surface; full pipeline visibility
  Note: Warm briefing stays as primary operator view — Revenue Intel is supplementary

### Phase 5 Gates

| Gate ID | Status | Depends On |
|---------|--------|------------|
| PHASE_5_INTEL_ACTIVE | NOT_STARTED | Tasks 69-70 |
| PHASE_5_AUTONOMY_GRADUATED | NOT_STARTED | Tasks 71-72 (HUMAN) |

---

## Critical Path

The updated longest dependency chain:

```
Task 3B   Live MCP discovery
  --> Task 15  Execute audit
    --> Task 16  Validate audit
      --> Task 18  Approve triage criteria [HUMAN]
        --> Task 20  Execute triage
          --> Task 21  Validate triage
            --> Task 22  Metabolize triage [HERO OUTCOME 1]
              |
              +--> Task 31  Legacy vault migration (parallel)
              |
              +--> Task 48  Follow-up draft agent
                    --> Task 49  Follow-up storage
                    --> Task 50  Warm validators
                      --> Task 51  Phase 3C tests
                        --> Task 52  Briefing loader
                          --> Task 53  New dashboard routes
                            --> Task 54  New templates
                              --> Task 55  Update nav
                                --> Task 56  Phase 3D tests
                                  --> Task 57  Follow-up orchestrator
                                  --> Task 58  Follow-up dispatcher
                                  --> Task 59  APScheduler
                                    --> Task 61  Phase 3E generation tests [PHASE_3E_GENERATION_COMPLETE]
                                      --> Task 61A-F  Deploy-readiness hardening [PHASE_3E_DEPLOY_READY]
                                      --> Task 61G-M  Tag-safety hardening [PHASE_3E_TAG_SAFETY_HOTFIX]
                                        --> Task 62  Vercel deployment
                                        --> Task 64  Dani verification [HERO OUTCOME 3]
                                          --> Tasks 75-77  Measurement baseline [PHASE_3G]
                                          --> Tasks 78-80  Slash-command enhancements
                                          --> Task 81  Enhanced retry
                                          --> Task 65  HeyReach warmup [HUMAN - 28d timer]
                                          --> Task 66  Instantly reactivation
                                            --> Task 68  Cold validation [HERO OUTCOME 4]
                                              --> Task 69  Revenue Intel agent
                                                --> Task 71  Supervised graduation [+14d]
                                                  --> Task 72  Full Autonomy [+30d]
```

**Parallel track**: Task 39 (EMERGENCY_STOP validation) runs alongside sustained warm dispatch in Phase 3.

---

## Hero Outcomes

| # | Outcome | Gate | Status |
|---|---------|------|--------|
| 1 | Dani receives prioritized GHL follow-up list | `PHASE_0_TRIAGE_PASSED` | PASSED |
| 2 | 10+ real warm follow-up drafts approved in dashboard | `PHASE_1_FIRST_BATCH_APPROVED` | PARTIAL |
| 3 | Daily warm follow-up briefing live on Vercel — Dani reviews AI-drafted follow-ups from phone | `PHASE_3F_VERCEL_LIVE` | PASSED (2026-03-11) — Dani verified, 5 drafts approved, live dispatch active |
| 4 | First cold emails + LinkedIn touches dispatched at RAMP | `PHASE_4_COLD_ACTIVE` | NOT_STARTED |
| 5 | Self-improving autonomous revenue pipeline — full autonomy earned | `PHASE_5_AUTONOMY_GRADUATED` | NOT_STARTED |

---

## Next Actions

**Immediate same-day priority (Hero Outcomes 2 + 3):**

Required operator inputs before Task 62D:
- `DATABASE_URL` must be populated with the Neon Postgres connection string
- `ANTHROPIC_API_KEY` must be populated for real analysis/draft generation
- `GHL_API_KEY` and `GHL_LOCATION_ID` must be loaded in the same shell/session used for the run
- temporary same-day dispatch capacity may use `DISPATCH_DAILY_LIMIT=30`; default ramp policy remains `5/day`

1. **Verify Neon DB connectivity**
   Deploy the validated Phase 3F hardening changes, then hit `GET /healthz` on Vercel and confirm `"db": "connected"` before any live pipeline claim.

2. **Task 62D — Run warm pipeline locally** (HUMAN+AUTO)
   Execute `run_followup_orchestrator(batch_size=25, force=True)` locally against Neon Postgres to populate real conversation/analysis/draft data. If `saved < 10`, rerun once with `batch_size=50` and `scan_days=60`.

3. **Task 63 — Route + approval flow verification** (HUMAN+AUTO)
   Confirm `/briefing`, `/followups`, `/followups/{id}`, approve/reject actions, and dispatch views all work remotely against real Postgres-backed data.

4. **Task 64 — Dani remote access verification** (HUMAN)
   Share URL + credentials with Dani. She reviews real warm follow-ups remotely and completes at least one approval/rejection from a non-dev device.

5. **Task 32 — Close Hero Outcome 2 under the warm-first model**
   After Dani approves at least 10 real warm follow-up drafts, mark `PHASE_1_FIRST_BATCH_APPROVED = PASSED` and close Hero Outcome 2.

**Already completed and validated locally:**
- Tasks 62A-62C — DB timeout, healthz probe, and graceful route fallbacks
- Task 62D0 — triage-backed candidate-source fallback
- Full local suite: `330 passed`

**After Phase 3F is complete:**
6. **Phase 4 — Cold-outbound expansion** (still blocked until `PHASE_3F_VERCEL_LIVE`)
