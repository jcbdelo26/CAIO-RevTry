# Rate Limits
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.6
**Applies To**: Pipeline Ops, Campaign Craft, Quality Guard

## Purpose
Defines maximum send/request rates per channel. Exceeding ANY limit = HARD BLOCK. The system must track cumulative usage per period and refuse to dispatch when a limit would be exceeded.

## Rate Limit Table

| Channel | Daily Cap | Monthly Cap | Hourly Cap | Ramp Rule | Notes |
|---------|-----------|-------------|------------|-----------|-------|
| Cold email (Instantly) | 25 (all domains combined) | -- | -- | Start at 5/day; increase by 5/day weekly until cap | 6 warmed domains total |
| GHL email | 150 | 3,000 | 20/domain | -- | Per-domain hourly cap applies independently |
| LinkedIn (HeyReach) | 5 to 20 | -- | -- | 4-week warmup: 5/day week 1, +5/day each week | Do NOT exceed daily cap during warmup |
| Revival email (Instantly) | 5 | -- | -- | -- | Separate from cold email daily cap |
| Apollo API | -- | -- | 200 req/hr | -- | Enrichment requests; back off if 429 received |
| GHL API | -- | -- | 60 req/min | -- | All GHL MCP tool calls count toward this limit |

## Enforcement Rules

| Rule | Condition | Action | Example Correct | Example Incorrect |
|------|-----------|--------|-----------------|-------------------|
| Pre-send check | Before ANY dispatch | Query today's send count for the channel; if count + batch_size > daily cap → BLOCK entire batch | 23 sent today + 3 in batch = 26 > 25 → BLOCK | Send 3 more anyway because "close enough" |
| Hourly enforcement | Per-hour window | Track sends per rolling hour; block if exceeded | 19 GHL emails this hour on domain A + 2 = 21 > 20 → BLOCK | Ignore hourly cap because daily cap not hit |
| Ramp compliance | During ramp period | Use ramp daily cap, not full daily cap | Week 1 Instantly: 5/day max | Week 1 Instantly: send 25 because "cap says 25" |
| Circuit breaker | 3 consecutive failures on a channel | HALT all sends on that channel; escalate | 3 bounces in a row → stop Instantly sends | Keep sending after 3 consecutive bounces |

## Ramp Schedule — Cold Email (Instantly)

| Week | Daily Cap | Cumulative Domains Active |
|------|-----------|--------------------------|
| Week 1 | 5/day | 2 domains |
| Week 2 | 10/day | 3 domains |
| Week 3 | 15/day | 4 domains |
| Week 4 | 20/day | 5 domains |
| Week 5+ | 25/day | 6 domains |

## Ramp Schedule — LinkedIn (HeyReach)

| Week | Daily Cap |
|------|-----------|
| Week 1 | 5/day |
| Week 2 | 10/day |
| Week 3 | 15/day |
| Week 4+ | 20/day |

## Do NOT Apply This File To
- GHL read operations during audit/triage (those have their own API rate limit but no send cap)
- Internal notifications (Slack webhooks)
- Dashboard data refresh requests

## Review Trigger
- When a new sending domain is added or removed
- When Instantly or HeyReach plan limits change
- When deliverability drops below acceptable thresholds
- Monthly during `/metabolize` review
