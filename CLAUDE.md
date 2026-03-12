# CLAUDE.md - RevTry

This file guides development inside `E:\Greenfield Coding Workflow\Project-RevTry\`.

---

## 1. Project State

RevTry is a warm-first Revenue Operations system for ChiefAIOfficer.com.

Phases: 0A-0B (foundation) → 1 (cold pipeline) → 2 (dispatch safety) → 3A-3F (warm system + Vercel) → 3G (agentic enhancements) → 4 (cold expansion) → 5 (revenue intel)

Current status:
- **Vercel deployment live** at `caio-rev-try.vercel.app` (2026-03-10)
- Warm generation, review, approval, dispatch, scheduler, auth, storage abstraction implemented
- Vercel Cron Job: daily pipeline + auto-dispatch at 6 AM CT (`GET /api/cron/warm-pipeline`)
- On-demand dispatch: `GET /api/cron/dispatch` (CRON_SECRET auth, curl-triggered)
- Test baseline: **384 passed** (2026-03-11)
- Remaining: Task 64 (Dani verification) → Task 63A (live dispatch flip) → Phase 3G

---

## 2. Workspace

- `src/` — application code (see `vault/integrations/code_structure.md` for full map)
- `revtry/vault/` — business rules, integration configs, compliance
- `revtry/registry/` — task tracking, phase gates, operational state
- `revtry/guardrails/` — validation gates, hard blocks, policies
- `.mcp.json` — MCP server config

---

## 3. Core Architecture

Warm operator path: `/briefing` → `/followups` → approve/reject → `/dispatch`

**Send safety chain** (mandatory order): circuit breaker → rate limiter → dedup → approval
- Warm GHL sends have priority over cold GHL sends
- Reference: `vault/guardrails/hard_blocks.md`

**Warm context isolation**:
- Allowed: compacted primary-thread conversation context, signatures/compliance, minimal CTA/proof context
- Not allowed: cold angle playbooks, broad ICP/campaign context, revenue-intel context

**Approval rule**: No email is ever sent without explicit human approval. Approval triggers immediate dispatch through the full safety chain (circuit breaker → rate limiter → dedup). If dispatch fails, the draft stays APPROVED and the cron job retries.

**Compatibility**: `GET /` stays backward-compatible in local mixed mode. `WARM_ONLY_MODE=true` redirects to `/briefing`.

---

## 4. Persistence & Deployment

- Local: `STORAGE_BACKEND=file` (JSON/Markdown)
- Deployed: `STORAGE_BACKEND=postgres` (Neon via `DATABASE_URL`)
- Full details: `vault/integrations/persistence_model.md`
- Vercel config: `vault/operations/vercel_deployment.md`

---

## 5. Dashboard & Auth

Key routes: `/healthz`, `/briefing`, `/followups`, `/followups/{id}`, `/dispatch`, `/api/cron/warm-pipeline`, `/api/cron/dispatch`
- `DASHBOARD_AUTH_ENABLED=true` for deployed mode (HTTP Basic Auth)
- `/healthz` stays open for smoke checks
- `WARM_ONLY_MODE=true` blocks cold routes in deployed mode

---

## 6. Environment Variables

High-frequency (must know every session):
- `GHL_API_KEY`, `GHL_LOCATION_ID`, `ANTHROPIC_API_KEY` — API access
- `STORAGE_BACKEND`, `DATABASE_URL` — persistence
- `WARM_ONLY_MODE`, `DASHBOARD_AUTH_ENABLED` — deployment mode
- `DISPATCH_DRY_RUN` — `true` logs dispatch payload without sending

Full contract: `vault/operations/environment_contract.md`

---

## 7. Development Rules

- Keep warm prompts lean; do not load cold playbook context into warm agents
- Do not mark failed sends as `DISPATCHED`; use `SEND_FAILED`
- Same-day warm reruns must be idempotent by `businessDate`
- Business-date logic must resolve in `America/Chicago`
- Do not add remote deployment assumptions that depend on local file paths
- Draft generation must aim for >90% success rate. If Gate 3 Check 2 rejects >10%, relax matching logic

**Gate failure behavior** (sequential blockers):
- Gate 1 FAIL → stops Gate 2
- Gate 2 FAIL → stops Gate 3
- Reference: `vault/guardrails/gate1_structural.md`, `gate2_compliance.md`, `gate3_alignment.md`

---

## 8. Tag Safety & Write Restrictions

- All tag writes are **add-only** via `ghl_add_tag` — no tag removals, replacements, or clears
- Contact field updates limited to: `firstName`, `lastName`, `companyName`
- `/execute` preflight refuses any operation touching tags, bulk deletes, or unsafe field writes
- Reference: `vault/guardrails/safe_contact_write_fields.md`, `vault/guardrails/hard_blocks.md`

---

## 9. DnD & Contact Filtering

- DnD/unsubscribed contacts must **never** reach `/followups`
- Contacts with recent manual outbound from sales team (`SALES_TEAM_USER_IDS`) are **tagged with an "Active Deal" badge** at display time, not excluded
- DnD filtering at **scan time** (`ghl_conversation_scanner.filter_eligible_summaries`); Active Deal badge computed at **display time** (`briefing_loader`)
- The `/followups` queue shows ONLY contacts with drafts (`draftId is not None`)
- Analysis-only contacts are not actionable and must not appear in the queue
- Reference: `vault/guardrails/hard_blocks.md`

---

## 10. Post-Implementation Verification Protocol

After every major UI/UX or backend change, spawn parallel verification agents BEFORE committing:

1. **Code Review Agent** — bugs, logic, security, conventions (`superpowers:code-reviewer`)
2. **Visual Validation Agent** — Playwright screenshots of affected dashboard pages
3. **Code Simplifier Agent** — clarity, consistency (`pr-review-toolkit:code-simplifier`)

Triggers: template changes, route handler changes, model changes affecting display, CSS changes.

---

## 11. Validation

Run tests: `cd src && python -m pytest tests -q` — baseline: **384 passed**
Full commands: `vault/operations/validation_commands.md`

---

## 12. Current Next Steps

**Phase 3F**: COMPLETE — `PHASE_3F_VERCEL_LIVE` PASSED (2026-03-11)
- Task 64: DONE — Dani verified remote access, approved 5 drafts
- Task 63A: DONE — `DISPATCH_DRY_RUN=false`, live dispatch active
- Auto-dispatch: DONE — cron auto-dispatches APPROVED drafts; `/api/cron/dispatch` for on-demand
- GHL links: DONE — dispatch history shows "View Thread" links to GHL conversations

**Phase 3G** (NOW UNBLOCKED): Agentic enhancements (Tasks 75-82)
- Spec: `docs/superpowers/specs/2026-03-11-phase-3g-agentic-enhancements-design.md`
- Batch 1 (Tasks 75-77): Measurement foundation — edit diffs, KPI metrics, confidence logging
- Batch 2 (Tasks 78-80): Slash command enhancements
- Batch 3 (Task 81): Enhanced retry with failure context
- Task 82: DONE — CLAUDE.md token audit

**Critical safety rules**:
- No email is sent without explicit human approval (approval changes draft state only)
- Phase 3G enhancements must not destabilize the warm pipeline
- Live dispatch active — send safety chain enforced: circuit breaker → rate limiter → dedup → approval
