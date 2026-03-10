# CTA Library

**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 1 setup
**Applies To**: Campaign Craft Agent

## Purpose

The CTA (Call-To-Action) library defines the approved CTAs that Campaign Craft may use in email drafts. Each CTA has an ID, display text, destination URL, and applicable context.

## Primary CTA

| ID | Display Text | URL | Context |
|----|-------------|-----|---------|
| exec_briefing | "Book a time here" / "Grab 15 minutes here" | https://caio.cx/ai-exec-briefing-call | Default CTA for all tiers. Links to Dani Apgar's executive briefing calendar. |

## Alternate CTAs (Tier-Specific)

| ID | Display Text | URL | Applicable Tiers | Context |
|----|-------------|-----|-------------------|---------|
| exec_briefing_t1 | "I'd love to walk you through what we're seeing with similar companies — grab 15 minutes here" | https://caio.cx/ai-exec-briefing-call | Tier 1 | High-touch, peer-level language for C-suite |
| exec_briefing_t2 | "Would you be open to a quick call to explore what's possible?" | https://caio.cx/ai-exec-briefing-call | Tier 2 | Mid-level, exploratory language |
| exec_briefing_t3 | "Here's a quick way to see if this fits your team" | https://caio.cx/ai-exec-briefing-call | Tier 3 | Low-commitment, practical language |

## CTA Rules

1. **One CTA per email** — Never include more than one booking link
2. **Exact URL only** — Always use `https://caio.cx/ai-exec-briefing-call`. Do NOT modify, shorten, or redirect
3. **Placement** — CTA appears in the final paragraph before the signature block
4. **No pressure language** — Do NOT use "limited spots", "act now", "don't miss out", or urgency framing
5. **Default** — If tier-specific CTA is unavailable, always fall back to `exec_briefing`

## Booking Link Validation

Gate 3 Check 6 verifies:
- `draft.booking_link == "https://caio.cx/ai-exec-briefing-call"`
- The booking link URL appears in the email body

Any draft that fails this check is BLOCKED.

## Review Trigger

- When booking link URL changes
- When new CTA variants are A/B tested
- Quarterly during vault freshness review
