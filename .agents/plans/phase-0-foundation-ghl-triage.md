# Feature Plan — Phase 0A/0B: Foundation + GHL Triage

## Feature Description

Phase 0 is split into two hard-gated stages:
- **Phase 0A** extends and verifies the external GHL MCP so RevTry can actually read the data needed for audit and triage.
- **Phase 0B** builds the runtime workspace in `e:/CAIO RevOps Claw/` and delivers the first hero outcome: a validated prioritized follow-up list for Dani.

No outbound sends occur in this phase. Phase 0A must pass before any audit or triage run begins.

## User Stories

- **US-1**: As Chris, I want a runtime `/prime` command so I can see system state in under 30 seconds.
- **US-2**: As Chris, I want a zero-ambiguity `/plan-task` workflow so runtime tasks are deterministic.
- **US-3**: As Dani, I want a validated prioritized follow-up list from GHL without opening the CRM.

## Problem / Solution

**Problem**: The current external `ghl-mcp/server.py` exposes 14 tools, but it does not expose the paginated list/search read capabilities required to audit contacts, pipelines, opportunities, and custom fields. The prior plan also assumed generic bash, relied on non-testable validation claims, and mixed scaffold commands with runtime commands.

**Solution**: Extend the external MCP first, standardize the runtime on PowerShell, separate scaffold from runtime responsibilities, then build the runtime workspace and execute audit and triage through top-level `/execute` and `/validate` sessions with explicit retry, lock, and maker-checker evidence.

## Assumptions Locked In

- Phase 0 path: extend the external MCP instead of downgrading the hero outcome
- Shell standard: PowerShell is canonical; Git Bash is optional only
- Phase 0 GHL-backed tasks: top-level sessions only
- Slack: optional and best-effort
- `mcp` is the correct package name; do not rely on a nonexistent `requirements.txt`

## Architecture Decisions

- **Planning scaffold vs runtime**: `Project-RevTry` is a planning scaffold only. Runtime files are created in `e:/CAIO RevOps Claw/`.
- **Current MCP baseline**: `server.py` currently exposes 14 tools, not 15.
- **Phase 0A hard gate**: audit and triage do not start until required list/read tools are verified live.
- **Maker-checker**: policy-enforced with evidence via distinct `makerSessionId` and `validatorSessionId`.
- **Retry counter**: `attemptNumber = count(failures.md rows for taskId) + 1`; attempt 4 is blocked.
- **Capability doc ownership**: `/validate` promotes and records verdicts; `/metabolize` updates `revtry/vault/integrations/ghl.md`.
- **Placeholder policy**: production-required files need real content; future-phase files may use formal phase-gated stubs only.

## Required MCP Contract Changes

These are mandatory Phase 0A deliverables in the external `ghl-mcp` server:

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

Tag inventory may be derived from paginated contact reads. A dedicated tag-list tool is optional unless live testing proves otherwise.

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| `server.py` exists but imports fail | Install explicit packages from imports: `mcp`, `aiohttp`, `python-dotenv`; retry |
| `GHL_API_KEY` or `GHL_LOCATION_ID` missing | Stop before `.mcp.json` is treated as usable; log blocker |
| Live discovery disagrees with docs | Live discovery wins; update `revtry/vault/integrations/ghl.md` |
| GHL lacks ICP-scorable fields | Use Phase 0 fallback priority model only after audit proves which fields exist |
| Slack webhook missing | `notificationPolicy=best_effort` may yield `notificationStatus=SKIPPED_OPTIONAL`; `required` must fail |
| Future-phase files needed early | Use formal phase-gated stubs only |

## Implementation Tasks

### Task 1 — Reconfirm runtime assumptions

**Goal**: Document in the runtime-facing docs that:
- `Project-RevTry` is scaffold only
- `e:/CAIO RevOps Claw/` is the runtime workspace
- PowerShell is canonical
- Phase 0 GHL-backed tasks run as top-level sessions

**Validation**: `CLAUDE.md` and `.claude/PRD.md` agree on all four points.

### Task 2 — Extend the external GHL MCP (Phase 0A)

**Goal**: Add the required list/read tools to `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py`.

**Required outcomes**:
- 14 existing tools remain functional
- `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_list_pipelines`, `ghl_list_custom_fields` exist
- New tools expose pagination and predictable output shape

**Validation**: live discovery sees all required tools.

### Task 3 — Run environment readiness preflight

**PowerShell sequence**:

```powershell
Test-Path 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
python -m py_compile 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
if (-not $env:GHL_API_KEY -or -not $env:GHL_LOCATION_ID) { throw 'Environment not ready' }
python 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
```

**Validation**: all checks pass or a blocker is logged.

### Task 4 — Create runtime `.mcp.json`

**File**: `e:/CAIO RevOps Claw/.mcp.json`

**Rule**: create only after Task 3 passes.

**Validation**: valid JSON; runtime points to `server.py`.

### Task 5 — Create runtime slash commands

**Files**:
- `e:/CAIO RevOps Claw/.claude/commands/prime.md`
- `e:/CAIO RevOps Claw/.claude/commands/plan-task.md`
- `e:/CAIO RevOps Claw/.claude/commands/execute.md`
- `e:/CAIO RevOps Claw/.claude/commands/validate.md`
- `e:/CAIO RevOps Claw/.claude/commands/metabolize.md`
- `e:/CAIO RevOps Claw/.claude/commands/status.md`

**Required contract changes**:
- `/plan-task` generates `taskId` as `TASK-YYYYMMDD-HHmmssfff-RAND4`, populates normalized `operationIntents`, `notificationPolicy`, `requiredPhaseGates`, and runs hard-block lint before saving a task spec
- `/execute` checks `registry/phase_gates.md`, manages `registry/locks/[TASK-ID].lock`, runs hard-block preflight before lock claim, computes `attemptNumber`, blocks attempt 4, and records `makerSessionId`
- `/validate` records `validatorSessionId` with the same random-suffix session format, resolves `notificationStatus = SENT | SKIPPED_OPTIONAL | FAILED | NOT_APPLICABLE`, and does not mutate `ghl.md` directly
- `/metabolize` updates `ghl.md` after validated capability audits and writes `Phase 0 Triage Criteria` as `Status: DRAFT` unless approval metadata already exists

**Validation**: all six files exist and include self-validation checklists.

### Task 6 — Create runtime folder structure and READMEs

**Goal**: create `revtry/` tree from the PRD.

**Rule**:
- active-phase files must be real
- future-phase files may be formal phase-gated stubs only

**Validation**: structure exists; README files are real content, not placeholders.

### Task 7 — Migrate compliance vault files

**Files**:
- `revtry/vault/compliance/exclusions.md`
- `revtry/vault/compliance/domain_rules.md`
- `revtry/vault/compliance/rate_limits.md`

**Validation**: Gate 2 dependencies are satisfied.

### Task 8 — Migrate ICP vault files

**Files**:
- `revtry/vault/icp/tier_definitions.md`
- `revtry/vault/icp/scoring_rules.md`
- `revtry/vault/icp/disqualification.md`
- `revtry/vault/icp/target_companies.md`

**Rule**: `target_companies.md` may be a phase-gated stub if Phase 1 is not active yet.

**Validation**: scoring files are real; stubs, if any, use the formal stub template.

### Task 9 — Create `revtry/vault/integrations/ghl.md`

**Required sections**:
- verified existing tools
- required Phase 0A tools
- tool verification procedure
- critical contact fields
- safe read operations
- safe write operations
- hard blocked operations
- `## Phase 0 Triage Criteria`

**Additional schema for `## Phase 0 Triage Criteria`**:
- `Status: DRAFT | APPROVED | DEFERRED`
- `Approved By: Chris + Dani | null`
- `Approved At: ISO8601 | null`
- `Criteria Rules`
- `Review Notes`

**Validation**: file reflects live discovery, not assumptions, and triage criteria are unusable until `Status = APPROVED`.

### Task 10 — Populate product, playbook, and feedback files

**Rule**: active-phase content must be real; future-phase artifacts may use formal stubs only.

**Validation**: migration inventory maps all source-to-destination relationships.

### Task 11 — Create guardrails

**Required changes**:
- hard block on placeholder/fake content in production-required files
- hard block on using phase-gated stubs as active-phase source material
- hard block preflight on prohibited `operationIntents` before execution
- preview-first write rule

**Validation**: hard block file matches PRD.

### Task 12 — Create agent configs and schemas

**Critical runtime rule**:
- Pipeline Ops Phase 0 work uses fresh top-level sessions only and never an alternate execution mode

**Validation**: Quality Guard lists gate dependencies explicitly.

### Task 13 — Initialize registry and memory files

**Required schemas**:
- `active.md` includes `Attempt #` and `Lock Owner (makerSessionId)`
- `completed.md` includes `Maker Session`, `Validator Session`, and `Notification Status`
- `failures.md` includes `Attempt #`
- `phase_gates.md` exists before the first `/execute` run
- `registry/locks/` exists for atomic lock files

**Validation**: tables match the PRD exactly.

### Task 14 — Write GHL audit task spec

**Task type**: `capability_audit`

**Required fields in the spec**:
- `operationIntents`
- `requiredPhaseGates`
- `zero_result_policy`
- `partial_data_policy`
- `fallback_policy`
- `notificationPolicy`
- `required_gate_dependencies`

**Validation**: task spec is zero-ambiguity and references exact tool names from `ghl.md`.

### Task 15 — Execute and validate the GHL audit

**Flow**:
1. `/execute` in a fresh top-level session
2. Gate 1 precheck only in maker session
3. `/validate` in a different fresh session
4. `/metabolize` updates `ghl.md`

**Rule**: `/validate` must not update `ghl.md` directly.

**Validation**:
- audit output exists
- `completed.md` records distinct maker and validator session ids
- `ghl.md` is updated by `/metabolize`
- `Phase 0 Triage Criteria` is written as `Status: DRAFT` until Chris + Dani approve it
- `PHASE_0_TRIAGE_CRITERIA_APPROVED` remains blocked until approval happens

### Task 16 — Write, execute, and validate the triage task

**Task type**: `triage`

**Rule**:
- use only the named `Phase 0 Triage Criteria` section
- STOP unless `Phase 0 Triage Criteria` has `Status: APPROVED` with approval metadata
- combined audit+triage tasks are forbidden in Phase 0
- if required ICP fields are missing, use the fallback GHL-native priority model

**Validation**:
- triage output exists
- exclusions are enforced
- notification outcome recorded via `notificationStatus`

## Testing Strategy

### MCP capability smoke tests

- `ghl_list_contacts` returns paginated data
- `ghl_list_pipelines` returns stage data
- `ghl_list_custom_fields` returns metadata
- `ghl_list_opportunities` returns paginated deal data

### Validation gate tests

- Gate 1 rejects a missing required field
- Gate 2 rejects a blocked domain
- Gate 3 rejects wrong tier/angle alignment

### Retry and maker-checker tests

- three logged failures allow attempts 1-3
- attempt 4 is blocked
- `/execute` and `/validate` record distinct session ids
- prohibited `operationIntents` are rejected before candidate generation
- task IDs are unique even when two specs are created within the same second

### Phase gate and lock tests

- missing `requiredPhaseGates` blocks task planning
- unmet phase gates block `/execute`
- `.lock` file is created, heartbeated, reclaimed safely, and deleted on PASS/FAIL

### Triage approval gate tests

- `Status=DRAFT` blocks triage
- `Status=DEFERRED` blocks triage
- `Status=APPROVED` with approval metadata permits triage

### Notification status tests

- `notificationPolicy=best_effort` + missing webhook yields `notificationStatus=SKIPPED_OPTIONAL`
- `notificationPolicy=required` + missing webhook yields FAIL
- `notificationPolicy=best_effort` + send failure yields `notificationStatus=FAILED`

### Audit metabolism test

- validated capability audit updates `revtry/vault/integrations/ghl.md` via `/metabolize`, not `/validate`

### Stub policy tests

- future-phase formal stub passes placeholder scan
- production-required file with `TBD` fails the scan

## Validation Commands

Run in PowerShell:

```powershell
(Get-Content 'e:/CAIO RevOps Claw/CLAUDE.md' | Measure-Object -Line).Lines
python -c "import json; json.load(open(r'e:/CAIO RevOps Claw/.mcp.json')); print('JSON valid')"
python -m py_compile 'D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py'
Get-Item 'e:/CAIO RevOps Claw/revtry/vault/integrations/ghl.md'
Get-Item 'e:/CAIO RevOps Claw/revtry/registry/active.md'
Get-Item 'e:/CAIO RevOps Claw/revtry/registry/completed.md'
Get-Item 'e:/CAIO RevOps Claw/revtry/registry/failures.md'
```

Placeholder/stub scan:

```powershell
$files = Get-ChildItem 'e:/CAIO RevOps Claw/revtry' -Recurse -File -Include *.md
$bad = $files | Select-String -Pattern 'TODO|TBD|placeholder' | Where-Object { $_.Line -notmatch 'Status:|Phase:|Owner:|Why deferred:|Review trigger:' }
if ($bad) { $bad | ForEach-Object { $_.Path + ':' + $_.LineNumber + ' ' + $_.Line } } else { 'OK' }
```

## Acceptance Criteria

- [ ] Scaffold docs and runtime assumptions are explicitly separated
- [ ] PowerShell is the canonical shell everywhere in runtime instructions
- [ ] External MCP baseline is recorded as 14 tools
- [ ] Required Phase 0A list/read tools are verified live
- [ ] No plan step assumes `requirements.txt` exists
- [ ] No Phase 0 GHL-backed task uses sub-agent execution
- [ ] `operationIntents`, `notificationPolicy`, and `notificationStatus` are specified consistently
- [ ] `requiredPhaseGates` and `phase_gates.md` are specified consistently
- [ ] Phase 0 triage is blocked until `Phase 0 Triage Criteria` is explicitly approved
- [ ] `/validate` does not claim ownership of `ghl.md` updates
- [ ] Retry counting is fully specified and testable
- [ ] Maker-checker evidence is fully specified and testable
- [ ] Placeholder policy distinguishes production files from formal phase-gated stubs
- [ ] Audit and triage are blocked until environment readiness and Phase 0A pass
- [ ] Hard-block preflight is specified separately from Gate 1
- [ ] Registry table schemas match the PRD exactly
- [ ] Combined audit+triage is explicitly forbidden in Phase 0
- [ ] Machine-readable JSON examples are camelCase end-to-end

---

*This plan is synced to `Project-RevTry/.claude/PRD.md` v2.4 and assumes runtime implementation has not started yet.*
