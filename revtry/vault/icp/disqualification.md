# Disqualification Rules
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.4
**Applies To**: Segmentation Agent, Pipeline Ops, Quality Guard

## Purpose
Defines automatic disqualification criteria. If ANY rule matches, the contact is marked `DISQUALIFIED` immediately. Do not calculate scores. Do not draft outreach. Do not enrich.

## Disqualification Criteria

| Rule ID | Disqualifier | Condition | Action | Example Correct | Example Incorrect |
|---------|-------------|-----------|--------|-----------------|-------------------|
| DQ-001 | Too small | <10 employees | BLOCK | 8-person startup → DISQUALIFIED | 8-person startup → scored as Tier 3 |
| DQ-002 | Too large | >1,000 employees | BLOCK | 5,000-person enterprise → DISQUALIFIED | 5,000-person enterprise → scored as Tier 2 |
| DQ-003 | Government | Industry = Government | BLOCK | Federal agency contact → DISQUALIFIED | Government contact → scored normally |
| DQ-004 | Non-profit | Industry = Non-profit | BLOCK | 501(c)(3) org → DISQUALIFIED | Non-profit → cold email sent |
| DQ-005 | Education | Industry = Education/Academia | BLOCK | University department head → DISQUALIFIED | Professor → scored as Tier 3 |
| DQ-006 | Current customer | In GHL with "Customer" tag | BLOCK | Contact tagged "Customer" → DISQUALIFIED | Customer → sent cold outreach |
| DQ-007 | Competitor | Known competitor domain | BLOCK | Competitor company contact → DISQUALIFIED | Competitor → scored and emailed |
| DQ-008 | Blocked domain | Email domain in `compliance/exclusions.md` domain list | BLOCK | `anyone@jbcco.com` → DISQUALIFIED | Blocked domain → scored normally |
| DQ-009 | Blocked email | Exact email in `compliance/exclusions.md` email list | BLOCK | `cole@exitmomentum.com` → DISQUALIFIED | Blocked email → campaign drafted |

## Evaluation Order

1. Check DQ-008 and DQ-009 first (exclusion list — fastest lookup)
2. Check DQ-006 and DQ-007 (GHL tag lookup)
3. Check DQ-003, DQ-004, DQ-005 (industry match)
4. Check DQ-001 and DQ-002 (company size)

**First match wins** — stop checking once any rule triggers.

## Output When Disqualified

Every disqualified contact MUST include:
- `tier`: "DISQUALIFIED"
- `disqualificationReason`: The specific Rule ID and human-readable reason (e.g., "DQ-002: Company has 3,500 employees (>1,000 limit)")
- `icpScore`: null
- `baseScore`: null

## Do NOT Apply This File To
- Contacts that have already been scored and tiered (disqualification is a pre-scoring check)
- Re-evaluation of existing leads unless a re-scoring event is triggered
- Internal team members or test contacts

## Review Trigger
- When a new disqualification category is identified from win/loss feedback
- When Chris or Dani requests an exception for a specific category
- When competitor list changes
