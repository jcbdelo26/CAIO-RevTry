# Vault — Versioned Business Rules

All business rules are stored as markdown files with freshness metadata. Agents read these files as context; only `/metabolize` and system evolution rules may update them.

## 7 Laws of Vault Files

1. Every vault file has a `Valid Through` date — agents must check freshness before relying on content
2. Vault files are the single source of truth for business rules — agents do not infer or assume beyond what is written
3. Changes to vault files are logged in `memory/operations_log.md` with rationale
4. Only `/metabolize` may update vault files after validated task outcomes
5. Conflicting rules between vault files must be escalated — agents do not resolve conflicts autonomously
6. Future-phase content may exist as formal phase-gated stubs only (with Status, Phase, Owner, Why deferred, Review trigger)
7. Production-required vault files must contain real, verified content — no `TBD`, `TODO`, or placeholders

## Directories

| Directory | Purpose | Gate Dependencies |
|-----------|---------|-------------------|
| `icp/` | Ideal Customer Profile definitions, scoring, disqualification | Gate 3 |
| `product/` | Offers, positioning, pricing, proof points | Gate 3 |
| `playbook/` | Email angles, sequences, objections, signatures | Gate 2, Gate 3 |
| `compliance/` | Exclusions, domain rules, rate limits | Gate 2 |
| `feedback/` | Campaign performance, win/loss patterns, agent learnings | None (output only) |
| `integrations/` | GHL, Instantly, HeyReach, Apollo tool specs | Gate 1 (structural) |
