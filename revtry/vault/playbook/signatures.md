# Signatures
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.8
**Applies To**: Campaign Craft, Quality Guard

## Purpose
Defines sender identity, CAN-SPAM compliance footer, booking link, banned openers, and subject line rules. Every outbound email MUST include the correct signature and footer. Quality Guard MUST reject any draft that violates these rules.

## Sender Identity

```
Dani Apgar
Head of Sales, Chief AI Officer
```

## CAN-SPAM Footer (include VERBATIM in every email)

```
Reply STOP to unsubscribe.
Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705
```

## Booking Link

`https://caio.cx/ai-exec-briefing-call`

## Banned Openers (GUARD-004 Static List)

These phrases MUST NEVER appear as the opening line of any email draft. Quality Guard Gate 2 must reject any draft that starts with these:

| # | Banned Opener |
|---|--------------|
| 1 | "Hope this finds you well" |
| 2 | "I wanted to reach out" |
| 3 | "Are you open to" |
| 4 | "I came across your profile" |
| 5 | "Just checking in" |
| 6 | "I hope you're doing well" |
| 7 | "I noticed" |
| 8 | "Quick question" |

**Dynamic updates**: When `FEEDBACK_LOOP_POLICY_ENABLED=true`, `/metabolize` may add new banned openers based on campaign performance feedback. Additions are appended to a `## Dynamic Banned Openers` section below the static list.

## Subject Line Rules

| Rule | Condition | Example Correct | Example Incorrect |
|------|-----------|-----------------|-------------------|
| Length | 60 characters or fewer | "AI strategy for [Company]" (26 chars) | "Here's an incredible opportunity to transform your business with AI today" (74 chars) |
| No ALL CAPS words | No word entirely in uppercase | "AI strategy call" | "FREE AI Strategy Call" |
| Exclamation marks | 1 or fewer | "Quick question about AI at [Company]" | "Don't miss this!! Amazing opportunity!" |
| No spam triggers | None of: free, guarantee, urgent, act now, limited time, winner, no obligation, buy now | "Streamlining ops at [Company]" | "Free consultation - act now!" |

## Do NOT Apply This File To
- LinkedIn messages (HeyReach has separate templates)
- Internal Slack notifications
- Dashboard communications

## Review Trigger
- When Dani's title or contact info changes
- When booking link URL changes
- When CAN-SPAM requirements change
- When banned opener list is updated via feedback metabolism
