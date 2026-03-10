# Email Angles Playbook
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: PRD Section 12.9 + legacy `vault/playbook/email_angles.md`
**Applies To**: Campaign Craft, Quality Guard, Orchestrator

## Purpose
Defines the available outreach angles, their tier applicability, and selection rules. The Orchestrator MUST specify an angle from this file in every Campaign Craft task spec. Campaign Craft MUST STOP if the angle is not specified.

## Angle Definitions

| Angle ID | Name | Applicable Tiers | Description | When to Use |
|----------|------|-----------------|-------------|-------------|
| `ai_executive_briefing` | AI Executive Briefing | Tier 1 | CEO/Founder-level -- strategic AI transformation, competitive advantage, board-level ROI | C-suite titles, high-revenue companies |
| `operational_efficiency` | Operational Efficiency | Tier 1, Tier 2 | Process automation, team productivity, cost reduction via AI workflows | Operations/Strategy VPs, Directors |
| `tech_modernization` | Tech Modernization | Tier 2, Tier 3 | AI stack adoption, integration with existing systems, technical ROI | CTO/CIO/VP Engineering, IT Directors |
| `competitive_edge` | Competitive Edge | Tier 1, Tier 2 | Industry-specific AI use cases, competitor analysis, market positioning | Any tier where industry context is strong |
| `quick_win` | Quick Win | Tier 2, Tier 3 | Low-lift AI pilots, 30-day results, minimal disruption | Mid-level decision makers, skeptical prospects |

## Tier-to-Angle Mapping Rule

| Tier | Allowed Angles | Default Angle |
|------|---------------|---------------|
| Tier 1 | `ai_executive_briefing`, `competitive_edge` | `ai_executive_briefing` |
| Tier 2 | `operational_efficiency`, `tech_modernization`, `competitive_edge` | `operational_efficiency` |
| Tier 3 | `tech_modernization`, `quick_win` | `quick_win` |

**Gate 3 validation**: Email angle must match the lead's tier per this mapping. A Tier 1 lead receiving a `quick_win` angle = FAIL. A Tier 3 lead receiving `ai_executive_briefing` = FAIL.

## Detailed Angle Playbooks (Migrated from Legacy)

### Tier 1 Angles (C-Suite / Founders)

#### `ai_executive_briefing` — Executive Buy-In
- **Hook**: The "Fractional CAIO" gap -- companies that need AI leadership but not a full-time hire
- **Mechanism**: M.A.P. 90-day pitch
- **CTA**: Day 1 Bootcamp / Executive Briefing Call
- **Best for**: CEOs/Founders at agencies and consulting firms

#### `competitive_edge` (Tier 1 variant) — Industry-Specific
- **Hook**: YPO/Construction/Manufacturing pain points
- **Mechanism**: Back-office automation, 300+ hrs saved
- **CTA**: Case study share
- **Best for**: Industry-specific verticals where peer proof exists

#### Hiring Trigger (sub-variant of `ai_executive_briefing`)
- **Hook**: Company is hiring for AI roles
- **Mechanism**: "Bridge strategy" -- set roadmap before hire starts
- **CTA**: Strategy call
- **Best for**: Companies with open AI/ML job postings

#### Value-First (sub-variant of `ai_executive_briefing`)
- **Hook**: 2-minute AI Readiness audit
- **Mechanism**: Soft CTA ("Mind if I send the link over?")
- **CTA**: Assessment link
- **Best for**: Cold leads with no prior engagement

### Tier 2 Angles (CTO, CIO, VP Ops)

#### `tech_modernization` — Tech Stack Integration
- **Hook**: AI integration playbook for their specific stack
- **Examples**: Lead enrichment, doc processing, support triage
- **CTA**: Brief sync

#### `operational_efficiency` — Operations Efficiency
- **Hook**: 40-60% time savings
- **Mechanism**: M.A.P. framework application
- **CTA**: "Open to a brief sync?"

#### `competitive_edge` (Tier 2 variant) — Innovation Champion
- **Hook**: 75% of AI pilots stall
- **Mechanism**: AI Council inside company, 90-day bootcamp to co-pilot to handoff
- **CTA**: Briefing call

### Tier 3 Angles (Directors, Managers)

#### `quick_win` — Quick Win
- **Hook**: One workflow to automate, 8 hrs/month back
- **CTA**: "Reply yes"

#### `quick_win` (variant B) — Time Savings
- **Hook**: 10 hrs/week back, AI agents not chatbots
- **CTA**: "Send a quick video?"

#### `competitive_edge` (Tier 3 variant) — Competitor FOMO
- **Hook**: Others already automating, 40-60% time savings
- **CTA**: "Reply show me"

#### DIY Resource (sub-variant of `quick_win`)
- **Hook**: Free 1-page checklist, tools <$100/mo
- **CTA**: Softest possible (resource share)

## Examples

| Scenario | Correct | Incorrect |
|----------|---------|-----------|
| CEO at consulting firm, Tier 1 | Angle: `ai_executive_briefing` | Angle: `quick_win` (wrong tier) |
| CTO at SaaS company, Tier 2 | Angle: `operational_efficiency` | Angle: `ai_executive_briefing` (Tier 1 only) |
| Director Ops at construction firm, Tier 3 | Angle: `quick_win` | Angle: `ai_executive_briefing` (Tier 1 only) |
| VP Strategy at healthcare company, Tier 2, strong industry context | Angle: `competitive_edge` | Angle: `quick_win` (not allowed for Tier 2) |

## Do NOT Apply This File To
- LinkedIn outreach (HeyReach has its own message templates)
- Revival emails (use separate revival angle rules when defined in Phase 2)
- Internal communications or Slack messages

## Review Trigger
- When win/loss data reveals angle effectiveness differences
- When new angles are developed from campaign performance feedback
- When Chris or Dani identifies a new messaging approach
- Quarterly during vault freshness review
