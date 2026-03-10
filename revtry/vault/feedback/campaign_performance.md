# Campaign Performance
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: Initialized empty for runtime population
**Applies To**: Quality Guard, Orchestrator, /metabolize

## Purpose
Tracks campaign-level KPIs (open rate, reply rate, bounce rate, conversion rate) to inform vault evolution and feedback metabolism. Populated by agents after campaign dispatches.

## Performance Log

| Date | Campaign ID | Channel | Angle ID | Tier | Sends | Opens | Replies | Bounces | Conversions | Notes |
|------|------------|---------|----------|------|-------|-------|---------|---------|-------------|-------|
| | | | | | | | | | | |

## Aggregate Metrics

| Metric | Current Value | Target | Status |
|--------|--------------|--------|--------|
| Open Rate | -- | >40% | -- |
| Reply Rate | -- | >5% | -- |
| Bounce Rate | -- | <3% | -- |
| Conversion Rate | -- | >2% | -- |

## Do NOT Apply This File To
- Individual lead scoring (use `icp/scoring_rules.md`)
- Real-time send decisions (use `compliance/rate_limits.md`)

## Review Trigger
- After every campaign batch completes
- Weekly during `/metabolize` review cycles
- When any metric falls below target threshold
