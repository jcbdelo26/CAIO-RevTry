# Clay Integration

**Status**: Deferred
**Phase**: Phase 2+ (requires async architecture evaluation)
**Owner**: Chris Daigle
**Why deferred**: Clay uses a webhook/table-based enrichment model (not a synchronous API like Apollo). Integrating Clay as a real-time fallback requires async job submission and polling, which adds complexity incompatible with Phase 1's launch timeline. Clay remains actively used for bulk website visitor enrichment via the RB2B pipeline (separate from RevTry).
**Review trigger**: When Phase 1 is live and enrichment gap analysis is complete, or when Clay releases a synchronous enrichment API.

## Current Usage (Outside RevTry)
- **Active workspace**: chiefaiofficer.com
- **Pipeline**: RB2B website tracking → Clay workspace table → Google Sheets → N8N → GHL
- **Purpose**: Bulk enrichment of website visitors, not per-contact real-time enrichment

## Why Not Phase 1
Clay's programmatic access is via webhooks to tables:
1. POST data to a Clay table webhook URL
2. Clay enriches asynchronously using 100+ data sources
3. Results retrieved via export or HTTP API action

This is batch-oriented and async — unsuitable for per-contact enrichment in an active pipeline without significant architecture changes.

## Future Integration Options
1. **Async enrichment queue**: Push contacts to Clay webhook, poll for results
2. **Shared table**: Query the existing RB2B enrichment table for matching contacts
3. **Clay Enterprise API**: Direct enrichment API (enterprise plan only)

## Reactivation Steps
1. Choose integration pattern (async queue vs shared table vs enterprise API)
2. Update `integrations/clay_client.py` for chosen pattern
3. Add `CLAY_API_KEY` or `CLAY_WEBHOOK_URL` + `CLAY_WEBHOOK_AUTH_TOKEN` to `.env`
4. Update `waterfall.py` to re-enable Step 3
5. Update this file with implementation docs
