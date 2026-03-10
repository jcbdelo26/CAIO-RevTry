# ICP Tier Definitions
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.2 + legacy `vault/icp/tier_definitions.md`
**Applies To**: Segmentation Agent, Pipeline Ops, Campaign Craft, Quality Guard

## Purpose
Defines title buckets, industry buckets, company-fit ranges, and multipliers for ICP scoring. Does NOT define arithmetic scoring (that lives in `scoring_rules.md`).

## Title Buckets

| Bucket | Titles | Points |
|--------|--------|--------|
| **Tier 1** | CEO, Founder, President, COO, Owner, Managing Partner | 25 |
| **Tier 2** | CTO, CIO, Chief of Staff, VP Operations, VP Strategy, VP Innovation, Managing Director | 22 |
| **Tier 3** | Director Ops, Director IT, Director Strategy, VP Engineering, Head of AI, Head of Data | 18 |
| **Manager** | Operations Manager, IT Manager, Project Manager, General Manager (any title containing "Manager" that does not match a higher tier) | 12 |
| **Unmatched** | Any title not matching Tier 1, 2, 3, or Manager buckets | 0 |

**Matching rule**: Normalize title to lowercase, strip punctuation, then match against bucket keywords. First match wins (check Tier 1 first, then Tier 2, then Tier 3, then Manager). Example: "VP of Operations" matches Tier 2 ("VP Operations"). Example: "Senior Manager, IT" matches Manager ("Manager").

## Industry Tiers

| Tier | Industries | Industry Score | Multiplier |
|------|-----------|---------------|------------|
| **Tier 1** | Agencies, Staffing, Consulting, Law/CPA, Real Estate, E-commerce | 20 | 1.5x |
| **Tier 2** | B2B SaaS, IT Services, Healthcare, Financial Services | 15 | 1.2x |
| **Tier 3** | Manufacturing, Logistics, Construction, Home Services | 10 | 1.0x |
| **Unmatched** | Any industry not listed above | 0 | 0.8x |

**Why Tier 1**: These buyers have direct budget authority, feel the AI pressure most acutely, and can make fast decisions. Fastest path to booked calls.

**Why Tier 2**: Technical buyers who can champion internally. Longer sales cycle but higher deal sizes. Need ROI proof and technical integration story.

**Why Tier 3**: Entry point buyers. May need to build consensus upward. Quick-win positioning works best.

## Company Fit — Employee Count

| Range | Score | Classification |
|-------|-------|---------------|
| 101-250 employees | 20 | Sweet spot |
| 51-100 employees | 15 | Acceptable |
| 251-500 employees | 15 | Acceptable |
| 10-50 employees | 10 | Review required |
| 501-1000 employees | 10 | Review required |
| <10 employees | DISQUALIFIED | Auto-DQ (see `disqualification.md`) |
| >1000 employees | DISQUALIFIED | Auto-DQ (see `disqualification.md`) |

## Revenue Fit

| Range | Score |
|-------|-------|
| $10M-$50M | 15 |
| $5M-$10M | 12 |
| $50M-$100M | 12 |
| $1M-$5M | 8 |
| >$100M | 8 |
| <$1M | 0 |
| Unknown | 0 |

## Multiplier Application

| Condition | Multiplier | Example Correct | Example Incorrect |
|-----------|-----------|-----------------|-------------------|
| Tier 1 industry AND/OR title fit | 1.5x | CEO at consulting firm: base 80 x 1.5 = 120.0 | Applying 1.5x to a manufacturing Director |
| Tier 2 industry AND/OR title fit | 1.2x | CTO at SaaS company: base 72 x 1.2 = 86.4 | Applying 1.2x when industry is Tier 1 |
| Tier 3 industry AND/OR title fit | 1.0x | Director Ops at construction company: base 48 x 1.0 = 48.0 | Applying 1.0x to a CEO |
| Unmatched industry | 0.8x | Unknown industry contact: base 50 x 0.8 = 40.0 | Treating unmatched same as Tier 3 (1.0x) |

**Multiplier selection rule**: Use the HIGHEST applicable multiplier between industry tier and title tier. Example: A CEO (Tier 1 title = 1.5x) at a manufacturing company (Tier 3 industry = 1.0x) gets 1.5x.

## Disqualification Handoff
If ANY disqualification rule from `disqualification.md` matches, STOP scoring immediately and mark `DISQUALIFIED`. Do not calculate base_score or apply multiplier.

## Do NOT Apply This File To
- Arithmetic scoring formulas (use `scoring_rules.md`)
- Exclusion list checks (use `compliance/exclusions.md`)
- Outreach channel selection (use `compliance/domain_rules.md`)

## Review Trigger
- When Chris or Dani identifies a new target vertical
- When win/loss data suggests a tier adjustment
- Quarterly during vault freshness review
