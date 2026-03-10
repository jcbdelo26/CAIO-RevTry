# Legacy-to-RevTry Migration Inventory

**Created**: Phase 0B
**Status**: Migration complete (verified 2026-03-11)

## Source Material

| Source File | Location | Description |
|-------------|----------|-------------|
| RevTry_PRD.md | `E:\CAIO RevOps Claw\RevTry_PRD.md` | Original 66KB PRD v1.0 — planning reference only |
| GEMINI.md | `E:\CAIO RevOps Claw\GEMINI.md` | Core system prompt from prior architecture — extract business rules only |
| vault/icp/scoring_rules.md | `E:\CAIO RevOps Claw\vault\icp\scoring_rules.md` | ICP scoring with multipliers |
| vault/icp/tier_definitions.md | `E:\CAIO RevOps Claw\vault\icp\tier_definitions.md` | Tier 1/2/3 definitions |
| vault/product/product_context.md | `E:\CAIO RevOps Claw\vault\product\product_context.md` | Product/offer/positioning |
| vault/playbook/email_angles.md | `E:\CAIO RevOps Claw\vault\playbook\email_angles.md` | 11 email angles (Tier 1/2/3) |
| Alpha-swarm .env | `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\.env` | GHL credentials — do NOT copy; reference in place |

## Migration Map

| Source | Destination | Status | Notes |
|--------|-------------|--------|-------|
| vault/icp/scoring_rules.md | revtry/vault/icp/scoring_rules.md | DONE (2026-03-07) | Migrated with freshness metadata (Valid Through: 2026-06-30) |
| vault/icp/tier_definitions.md | revtry/vault/icp/tier_definitions.md | DONE (2026-03-07) | Migrated with freshness metadata (Valid Through: 2026-06-30) |
| vault/product/product_context.md | revtry/vault/product/offers.md + positioning.md + proof_points.md + cta_library.md + pricing.md | DONE (2026-03-07) | Split into 5 files; pricing.md is Phase-gated stub |
| vault/playbook/email_angles.md | revtry/vault/playbook/email_angles.md | DONE (2026-03-07) | Migrated with freshness metadata (Valid Through: 2026-06-30) |
| GEMINI.md (business rules only) | N/A | N/A | Architecture/system prompt only — business rules already embedded in vault files during Phase 0B |

## Rules

- Preserve all source files until migration is verified
- Every migrated file must have `Valid Through` freshness metadata
- Content is migrated; architecture and runtime assumptions are NOT
- After migration, source files remain for reference — do not delete
