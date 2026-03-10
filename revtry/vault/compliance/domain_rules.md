# Domain Rules (Channel Routing)
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.5
**Applies To**: Campaign Craft, Pipeline Ops, Quality Guard

## Purpose
Defines which outreach channel is used for which message type. A channel mismatch = domain reputation destruction. This is a HARD compliance rule, not a suggestion.

## Channel Routing Rules

| Message Type | Required Platform | Domain/Account | Rule | Example Correct | Example Incorrect |
|-------------|-------------------|----------------|------|-----------------|-------------------|
| Cold outreach email | **Instantly V2 ONLY** | 6 warmed domains | All first-touch cold emails go through Instantly | Cold lead → Instantly campaign | Cold lead → GHL email |
| Warm/nurture email | **GHL ONLY** | chiefai.ai domain | Existing relationship emails through GHL only | Follow-up after call → GHL | Follow-up after call → Instantly |
| LinkedIn outreach | **HeyReach ONLY** | T1/T2/T3 campaigns | All LinkedIn messaging through HeyReach | LinkedIn connect request → HeyReach | LinkedIn message → manual send |
| Revival email | **Instantly ONLY** | Warmed domains | Re-engagement of cold/stale contacts | 90-day no-activity contact → Instantly | Revival → GHL |

## HARD VIOLATIONS (NEVER do these)

| Violation | Consequence | Detection |
|-----------|-------------|-----------|
| Cold email via GHL | Domain reputation destroyed for chiefai.ai | Quality Guard Gate 3 must reject |
| Warm email via Instantly | Deliverability risk; brand confusion | Quality Guard Gate 3 must reject |
| Any outreach via unverified channel | Unpredictable deliverability | Pre-send channel validation required |

## Priority
`compliance/domain_rules.md` > `playbook/sequences.md` > agent preference. If a sequence template suggests a channel that conflicts with this file, this file wins.

## Do NOT Apply This File To
- Internal Slack notifications
- Dashboard or reporting communications
- GHL workflow automations that are not outbound email

## Review Trigger
- When a new sending domain is warmed and added
- When a channel integration is added or removed
- When deliverability issues are detected on any domain
