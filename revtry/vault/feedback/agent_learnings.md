# Agent Learnings
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 0B migration
**Source**: Initialized empty for runtime population
**Applies To**: Orchestrator, Quality Guard, /metabolize

## Purpose
Captures agent-level operational learnings, failure patterns, and improvement signals. Populated by `/metabolize` and Quality Guard during validation cycles. Used to inform vault evolution decisions.

## Learning Log

| Date | Agent | Task ID | Learning Type | Description | Action Taken | Vault File Updated |
|------|-------|---------|--------------|-------------|-------------|-------------------|
| 2026-03-10 | pipeline-ops | TASK-20260307-143000000-Ak9R | EFFICIENCY_WIN | Capability audit completed in single pass with 50-page pagination cap. Key vault files (ghl.md, output_schema.md, hard_blocks.md) provided sufficient context for clean execution. dateLastActivity not returned by list endpoint — partial-data policy (null=stale) was correctly applied. | Updated ghl.md with validated capability matrix and revised data quality stats | vault/integrations/ghl.md |
| 2026-03-10 | pipeline-ops | TASK-20260309-173228886-RMb2 | EFFICIENCY_WIN | Phase 0 triage produced 244 prioritized contacts (140 P1, 104 P2) from 269 opportunities across 9 pipelines. All 26 validation criteria passed. GHL-native scoring (stage + tags + data completeness) proved sufficient for initial prioritization without ICP enrichment. | Output: TASK-20260309-173228886-RMb2_output.json/md | vault/integrations/ghl.md |
| 2026-03-10 | pipeline-ops | TASK-20260309-173228886-RMb2 | RULE_GAP | MCP pagination bug: ghl_list_contacts and ghl_list_opportunities tools did not expose start_after_id cursor parameter. GHL API uses cursor-based pagination (startAfterId), not offset-based. Without this, every page request returned the same first 100 records. ABM High (100/488) and ABM Low/Med (100/707) pipelines had incomplete opportunity data. | Fixed server.py to expose start_after_id in both tool schemas and handlers. MCP server restart needed. | mcp-servers/ghl-mcp/server.py |
| 2026-03-10 | pipeline-ops | TASK-20260309-173228886-RMb2 | ESCALATION_RESOLVED | EX-01 (test-seedlist-glockapps) excluded 79 contacts — largest exclusion category. These are deliverability test contacts from GlockApps that polluted pipeline data. Scoring system correctly identified and excluded them. | No action needed — exclusion rule working as designed | — |

## Learning Types

| Type | Definition |
|------|-----------|
| FAILURE_PATTERN | Recurring failure mode across multiple tasks |
| SCORING_DRIFT | Scoring results not matching conversion outcomes |
| RULE_GAP | Missing rule that caused incorrect agent behavior |
| EFFICIENCY_WIN | Process improvement that reduced task time or errors |
| ESCALATION_RESOLVED | Blocker that was resolved and should inform future behavior |

## Do NOT Apply This File To
- Campaign-level performance metrics (use `feedback/campaign_performance.md`)
- Individual task failures (those go in `registry/failures.md`)

## Review Trigger
- After every `/metabolize` cycle
- When failure count for any agent exceeds 3 in a 7-day window
- When scoring drift is detected in win/loss patterns
