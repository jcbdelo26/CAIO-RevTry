# ICP Scoring Rules
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.3 + legacy `vault/icp/scoring_rules.md`
**Applies To**: Segmentation Agent, Quality Guard

## Purpose
Deterministic arithmetic for ICP scoring. Use together with `tier_definitions.md` (for bucket lookups) and `disqualification.md` (for pre-score blocking).

## Calculation Order (MANDATORY — follow in this exact sequence)

1. Check `disqualification.md`. If ANY rule matches → mark `DISQUALIFIED`, STOP. Do not score.
2. Calculate `base_score` (0-100) by summing all component scores below.
3. Look up `industry_multiplier` from `tier_definitions.md` (use highest of industry tier or title tier).
4. Calculate `icp_score = round(base_score * multiplier, 1)` (max theoretical = 100 x 1.5 = 150.0).
5. Assign tier from `icp_score` using thresholds below.

## Base Score Components

| Component | Max Points | Logic | Example Correct | Example Incorrect |
|-----------|-----------|-------|-----------------|-------------------|
| Company Size | 20 | 101-250=20, 51-100=15, 251-500=15, 10-50=10, 501-1000=10 | 150 employees = 20 pts | 150 employees = 15 pts |
| Title Match | 25 | Tier 1=25, Tier 2=22, Tier 3=18, Manager=12, unmatched=0 | CEO = 25 pts | CEO = 20 pts |
| Industry Match | 20 | Tier 1=20, Tier 2=15, Tier 3=10, unmatched=0 | Consulting = 20 pts | Consulting = 15 pts |
| Revenue Fit | 15 | $10M-$50M=15, $5M-$10M=12, $50M-$100M=12, $1M-$5M=8, >$100M=8, <$1M=0, unknown=0 | $25M revenue = 15 pts | $25M revenue = 12 pts |
| Tech Signal | 10 | Active AI hiring=10, AI tools adopted=7, no signal=0 | Job posting for "AI Engineer" = 10 pts | No signal = 5 pts |
| Engagement Signal | 10 | Website visit=10, content download=7, social engagement=5, none=0 | Downloaded whitepaper = 7 pts | No engagement = 3 pts |

**Maximum base_score**: 20 + 25 + 20 + 15 + 10 + 10 = **100**

## Tier Thresholds (use comparison operators exactly as written)

| Tier | Condition | Status |
|------|-----------|--------|
| Tier 1 | `icp_score >= 80.0` | QUALIFIED |
| Tier 2 | `60.0 <= icp_score < 80.0` | QUALIFIED |
| Tier 3 | `40.0 <= icp_score < 60.0` | QUALIFIED |
| Disqualified | `icp_score < 40.0` OR any disqualification rule match | DISQUALIFIED |

## Worked Example (MANDATORY — include verbatim in every scoring output)

```
Lead: CEO at a consulting firm, 150 employees, $25M revenue, no tech signal, no engagement
  Company Size: 20 (101-250 = sweet spot)
  Title Match:  25 (CEO = Tier 1)
  Industry:     20 (Consulting = Tier 1)
  Revenue Fit:  15 ($10M-$50M)
  Tech Signal:   0 (no signal)
  Engagement:    0 (none)
  ──────────────────────────
  base_score = 80
  multiplier = 1.5 (highest of: Tier 1 title = 1.5, Tier 1 industry = 1.5)
  icp_score  = round(80 * 1.5, 1) = 120.0
  → TIER 1 QUALIFIED (120.0 >= 80.0)
```

## "Why This Score" Requirement

Every scored lead MUST include a `why_this_score` text explanation that traces each component. This is mandatory for Quality Guard review and provides audit trail for feedback metabolism.

Format: `"Size: {pts} ({reason}), Title: {pts} ({reason}), Industry: {pts} ({reason}), Revenue: {pts} ({reason}), Tech: {pts} ({reason}), Engagement: {pts} ({reason}) → base={base}, mult={mult}, icp_score={score} → {TIER}"`

## Priority Rule
`compliance/exclusions.md` > `icp/disqualification.md` > `icp/scoring_rules.md`. If a contact is on the exclusion list, do not even check disqualification rules. If a contact matches a disqualification rule, do not calculate scores.

## Do NOT Apply This File To
- Channel selection (use `compliance/domain_rules.md`)
- Email angle selection (use `playbook/email_angles.md`)
- Outreach timing or rate limits (use `compliance/rate_limits.md`)

## Review Trigger
- When win/loss data reveals scoring inaccuracy (e.g., Tier 3 leads converting at higher rates than Tier 1)
- When new scoring signals are identified
- Quarterly during vault freshness review
