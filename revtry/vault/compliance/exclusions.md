# Exclusions
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.1 + GHL DND audit
**Applies To**: Pipeline Ops, Campaign Craft, Quality Guard

## Purpose
Complete list of blocked domains and individual emails. Every agent MUST check this file before ANY outreach action. A match here = HARD BLOCK, no override, no exceptions.

## Blocked Domains (7 domains — ALL contacts blocked forever)

| Domain | Status | Added |
|--------|--------|-------|
| jbcco.com | BLOCKED | 2026-03-07 |
| frazerbilt.com | BLOCKED | 2026-03-07 |
| immatics.com | BLOCKED | 2026-03-07 |
| debconstruction.com | BLOCKED | 2026-03-07 |
| credegroup.com | BLOCKED | 2026-03-07 |
| verifiedcredentials.com | BLOCKED | 2026-03-07 |
| exitmomentum.com | BLOCKED | 2026-03-07 |

**Rule**: If `contact.email` ends with ANY domain above → BLOCK. Do not score. Do not enrich. Do not draft.

## Blocked Individual Emails (27 contacts)

| Email | Domain | Status |
|-------|--------|--------|
| chudziak@jbcco.com | jbcco.com | BLOCKED |
| hkephart@frazerbilt.com | frazerbilt.com | BLOCKED |
| jmusil@jbcco.com | jbcco.com | BLOCKED |
| imorris@jbcco.com | jbcco.com | BLOCKED |
| mdabler@jbcco.com | jbcco.com | BLOCKED |
| maria.martinezcisnado@immatics.com | immatics.com | BLOCKED |
| mm@immatics.com | immatics.com | BLOCKED |
| slee@debconstruction.com | debconstruction.com | BLOCKED |
| bzupan@jbcco.com | jbcco.com | BLOCKED |
| mfolsom@jbcco.com | jbcco.com | BLOCKED |
| kelsey.irvin@credegroup.com | credegroup.com | BLOCKED |
| michael.loveridge@credegroup.com | credegroup.com | BLOCKED |
| amejia@debconstruction.com | debconstruction.com | BLOCKED |
| kjacinto@debconstruction.com | debconstruction.com | BLOCKED |
| lagriffin@frazerbilt.com | frazerbilt.com | BLOCKED |
| aneblett@verifiedcredentials.com | verifiedcredentials.com | BLOCKED |
| tek@debconstruction.com | debconstruction.com | BLOCKED |
| wmitchell@frazerbilt.com | frazerbilt.com | BLOCKED |
| cole@exitmomentum.com | exitmomentum.com | BLOCKED |
| alex.wagas@credegroup.com | credegroup.com | BLOCKED |
| avali@debconstruction.com | debconstruction.com | BLOCKED |
| jnavarro@jbcco.com | jbcco.com | BLOCKED |
| kvale@frazerbilt.com | frazerbilt.com | BLOCKED |
| phirve@frazerbilt.com | frazerbilt.com | BLOCKED |
| mkcole@frazerbilt.com | frazerbilt.com | BLOCKED |
| tschaaf@jbcco.com | jbcco.com | BLOCKED |
| sharrell@frazerbilt.com | frazerbilt.com | BLOCKED |

## Global Exclusion Categories

| Category | Rule | Example Correct | Example Incorrect |
|----------|------|-----------------|-------------------|
| Blocked domain match | Email domain in blocked domains list → BLOCK | `anyone@jbcco.com` → BLOCKED | `anyone@jbcco.com` → scored as Tier 2 |
| Blocked email match | Exact email in blocked emails list → BLOCK | `cole@exitmomentum.com` → BLOCKED | `cole@exitmomentum.com` → sent campaign |
| Current customer | GHL tag contains "Customer" → BLOCK | Contact with tag "Customer" → skip | Contact with tag "Customer" → cold email |
| Competitor | Known competitor domain → BLOCK | Competitor domain → skip | Competitor domain → outreach |

## Do NOT Apply This File To
- Internal team communications
- Existing customer success workflows (those contacts are blocked from outreach, not from all communication)

## Review Trigger
- When a new DND request is received
- When a bounce/complaint is logged against a domain
- Monthly review during `/metabolize` cycles
