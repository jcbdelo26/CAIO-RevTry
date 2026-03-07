# Phase 2 — Outreach Dispatch

## Executive Summary

Wire approved campaign drafts to Instantly (cold email), GHL (warm email), and HeyReach (LinkedIn). Enforce RAMP autonomy limits (≤5/day per channel, Tier 1 only), activate circuit breaker on all outbound integrations, and stand up KPI tracking with EMERGENCY_STOP thresholds.

**PRD Reference**: Section 6 Phase 2, User Stories US-7, US-8

---

## Scope

### In Scope
- **US-7**: Approved drafts dispatched via correct channel at enforced daily rate limits
- **US-8**: Circuit breaker halts sends on 3 consecutive failures per integration
- Pipeline Ops Agent (dispatcher for approved drafts)
- Instantly V2 client (cold email)
- HeyReach client (LinkedIn sequences)
- GHL dispatch for warm email (extends Step 1 GHL client)
- 3-layer dedup before every dispatch
- File-backed rate limiter (RAMP: ≤5/day)
- File-backed circuit breaker (trips on 3 consecutive failures)
- KPI tracker with EMERGENCY_STOP thresholds
- DISPATCHED status added to draft lifecycle

### Out of Scope
- Autonomy graduation (Ramp → Supervised → Full) — Phase 3
- Vercel dashboard deployment — Phase 3
- Revenue Intel weekly reports — Phase 3
- Sub-agent dispatch — deferred per PRD

---

## Architecture Decisions

1. **Pipeline Ops Agent as dispatcher** — reads APPROVED drafts from storage, routes to correct channel based on `draft.channel` enum
2. **Circuit breaker**: file-backed state at `registry/circuit_breaker_state.json`, 3 states: CLOSED → OPEN → HALF_OPEN
3. **Rate limiter**: file-backed daily counter at `registry/dispatch_counter_YYYY-MM-DD.json`
4. **Dedup**: 3 layers — (a) draft hash via GUARD-002, (b) contact+channel 30-day window, (c) GHL tag check
5. **No database** — all state is human-readable JSON/markdown files (per PRD)

---

## Implementation Steps

### Step 1: Instantly V2 Client
**Create** `src/integrations/instantly_client.py`

Pattern: same as `apollo_client.py` / `ghl_client.py`
- Auth: `Authorization: Bearer {INSTANTLY_API_KEY}` header
- Base URL: `https://api.instantly.ai/api/v2`
- Key endpoint: `POST /emails/send` — send single email
- Rate awareness: respect Instantly's own domain limits
- Env var: `INSTANTLY_API_KEY`

Methods:
- `send_email(from_email, to_email, subject, body, campaign_id=None)` → POST /emails/send
- `get_campaign_analytics(campaign_id)` → GET /campaigns/{id}/analytics
- `close()`

### Step 2: HeyReach Client
**Create** `src/integrations/heyreach_client.py`

Pattern: same structure
- Auth: `X-API-KEY: {HEYREACH_API_KEY}` header
- Base URL: `https://api.heyreach.io/api/v1`
- Key endpoint: `POST /campaigns/{id}/leads` — add lead to LinkedIn campaign
- Env var: `HEYREACH_API_KEY`

Methods:
- `add_lead_to_campaign(campaign_id, linkedin_url, first_name, last_name, company)` → POST
- `get_campaign_status(campaign_id)` → GET
- `close()`

### Step 3: Circuit Breaker
**Create** `src/pipeline/circuit_breaker.py`

```
States: CLOSED (normal) → OPEN (tripped) → HALF_OPEN (testing)

Trips after: 3 consecutive failures per integration
Recovery: HALF_OPEN after 30-minute cooldown → single test request
  - Test succeeds → CLOSED
  - Test fails → OPEN (reset cooldown timer)

File state: registry/circuit_breaker_state.json
{
  "instantly": {"state": "CLOSED", "consecutive_failures": 0, "tripped_at": null, "last_failure": null},
  "ghl": {"state": "CLOSED", ...},
  "heyreach": {"state": "CLOSED", ...},
  "apollo": {"state": "CLOSED", ...}
}
```

Class: `CircuitBreaker`
- `async def call(self, integration: str, func, *args, **kwargs)` — wraps any async dispatch call
- `def is_open(self, integration: str) -> bool`
- `def record_success(self, integration: str)`
- `def record_failure(self, integration: str)`

### Step 4: Rate Limiter
**Create** `src/pipeline/rate_limiter.py`

```
RAMP (Phase 2 default): ≤5/day per channel
SUPERVISED (Phase 3): ≤25/day per channel
FULL_AUTONOMY (Phase 3): ≤100/day per channel

File state: registry/dispatch_counter_YYYY-MM-DD.json
{
  "instantly": 3,
  "ghl": 1,
  "heyreach": 0
}
```

Class: `DailyRateLimiter`
- `def can_send(self, channel: str) -> bool`
- `def record_send(self, channel: str)`
- `def remaining(self, channel: str) -> int`

### Step 5: Dedup Layer
**Create** `src/pipeline/dedup.py`

3-layer check before dispatch:
1. **Hash dedup** — reuse `compute_draft_hash()` from GUARD-002 logic, check against `registry/sent_hashes.json`
2. **Contact+channel window** — no same contact on same channel within 30 days, tracked in `registry/dispatch_log.json`
3. **GHL tag check** — if contact has tag `revtry-sent-{channel}`, skip (requires GHL client read)

Returns: `(is_duplicate: bool, reason: str)`

### Step 6: Dispatch Orchestrator
**Create** `src/pipeline/dispatcher.py`

```python
async def dispatch_approved_drafts(
    max_dispatches: int = 5,  # RAMP default
) -> DispatchResult:
    """Load APPROVED drafts, apply safety checks, dispatch to channels."""
    # 1. Load all APPROVED drafts from storage
    # 2. Filter: Tier 1 only (RAMP restriction)
    # 3. For each draft:
    #    a. Dedup check → skip if duplicate
    #    b. Rate limit check → stop if daily limit reached
    #    c. Circuit breaker check → skip if integration is OPEN
    #    d. Route: channel="instantly" → InstantlyClient
    #             channel="ghl" → GHLClient (warm email workflow)
    #             channel="heyreach" → HeyReachClient
    #    e. On success: mark draft DISPATCHED, record in dispatch log, add GHL tag
    #    f. On failure: increment circuit breaker, log error
    # 4. Return summary: {dispatched: N, skipped_dedup: N, skipped_rate_limit: N, failed: N}
```

### Step 7: KPI Tracker
**Create** `src/pipeline/kpi_tracker.py`

Reads dispatch logs and integration analytics to track:
- `sent_count`, `open_count`, `reply_count`, `bounce_count`, `unsub_count`

EMERGENCY_STOP thresholds (from PRD):
- Open rate < 30%
- 0 replies after 15 sends
- Bounce rate > 10%
- Unsubscribe rate > 5%

When any threshold is breached → set all circuit breakers to OPEN, log to `registry/escalations.md`

File state: `outputs/kpi/kpi_YYYY-MM-DD.json`

### Step 8: Schema Updates
**Modify** `src/models/schemas.py`

- Add `DISPATCHED` to `DraftApprovalStatus` enum
- Add to `StoredDraft`:
  - `dispatched_at: Optional[str]`
  - `dispatch_channel: Optional[str]`
  - `dispatch_error: Optional[str]`

### Step 9: Env Vars
**Modify** `.env.example`

```
# === Phase 2: Outreach Dispatch ===
INSTANTLY_API_KEY=
HEYREACH_API_KEY=
HEYREACH_CAMPAIGN_ID=
DISPATCH_DAILY_LIMIT=5
DISPATCH_TIER_RESTRICTION=1
```

### Step 10: Dashboard Dispatch View
**Modify** `src/dashboard/app.py`

- `GET /dispatch` — show dispatch queue (APPROVED drafts ready to send) and recent dispatch history
- `POST /dispatch/run` — trigger a dispatch cycle (calls `dispatch_approved_drafts()`)
- `GET /dispatch/status` — JSON: circuit breaker states, daily counts, KPI summary

### Step 11: Tests
**Create**:
- `src/tests/test_instantly_client.py` (~4 tests)
- `src/tests/test_heyreach_client.py` (~4 tests)
- `src/tests/test_circuit_breaker.py` (~6 tests: state transitions, trip on 3 failures, recovery)
- `src/tests/test_rate_limiter.py` (~4 tests: daily limit, channel isolation, reset on new day)
- `src/tests/test_dedup.py` (~4 tests: hash, contact window, clean pass)
- `src/tests/test_dispatcher.py` (~6 tests: full flow, rate limit stop, circuit breaker skip, dedup skip)

---

## Files Summary

| Action | File |
|--------|------|
| CREATE | `src/integrations/instantly_client.py` |
| CREATE | `src/integrations/heyreach_client.py` |
| CREATE | `src/pipeline/circuit_breaker.py` |
| CREATE | `src/pipeline/rate_limiter.py` |
| CREATE | `src/pipeline/dedup.py` |
| CREATE | `src/pipeline/dispatcher.py` |
| CREATE | `src/pipeline/kpi_tracker.py` |
| CREATE | `src/tests/test_instantly_client.py` |
| CREATE | `src/tests/test_heyreach_client.py` |
| CREATE | `src/tests/test_circuit_breaker.py` |
| CREATE | `src/tests/test_rate_limiter.py` |
| CREATE | `src/tests/test_dedup.py` |
| CREATE | `src/tests/test_dispatcher.py` |
| MODIFY | `src/models/schemas.py` |
| MODIFY | `src/dashboard/app.py` |
| MODIFY | `.env.example` |

---

## Acceptance Criteria (from PRD)

- [ ] Cold email dispatched ONLY via Instantly (never GHL)
- [ ] Warm email dispatched ONLY via GHL (never Instantly)
- [ ] Circuit breaker trips on 3 consecutive failures — verified by intentional test
- [ ] RAMP limits enforced: ≤5 emails/day, Tier 1 leads only, Chris + Dani both approve
- [ ] KPI red flags trigger EMERGENCY_STOP: open <30% OR 0 replies after 15 sends OR bounce >10% OR unsub >5%
- [ ] 3-layer dedup prevents duplicate sends
- [ ] All new files compile and import
- [ ] ≥28 new tests pass

---

## Validation Commands

```bash
cd "E:/Greenfield Coding Workflow/Project-RevTry/src"

# Compile all
for f in $(find . -name "*.py"); do python -m py_compile "$f"; done

# Import chain
python -c "
from pipeline.circuit_breaker import CircuitBreaker
from pipeline.rate_limiter import DailyRateLimiter
from pipeline.dedup import check_dedup
from pipeline.dispatcher import dispatch_approved_drafts
from pipeline.kpi_tracker import KPITracker
from integrations.instantly_client import InstantlyClient
from integrations.heyreach_client import HeyReachClient
print('Phase 2 imports OK')
"

# Full test suite
python -m pytest tests/ -v
```

---

## Prerequisites

Before implementing Phase 2:
1. **Instantly API key** — requires active Instantly V2 account with warmed domains
2. **HeyReach API key** — requires active account + 4-week warmup complete
3. **GHL warm email workflow** — decide: trigger GHL workflow or send via GHL email API
4. **Chris + Dani approval** of RAMP limits and Tier 1 restriction
