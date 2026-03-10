# BetterContact Integration

**Status**: Deferred
**Phase**: Phase 2+ (when subscription is activated)
**Owner**: Chris Daigle
**Why deferred**: No active BetterContact subscription. Apollo is the sole enrichment provider for Phase 1 launch. BetterContact will be evaluated as a waterfall fallback when enrichment coverage data shows gaps that Apollo alone cannot fill.
**Review trigger**: When enrichment_score analysis reveals consistent gaps in Apollo-only enrichment, or when BetterContact subscription is activated.

## Future Role
- Enrichment waterfall step 2 (fallback after Apollo)
- Email verification and discovery
- The `integrations/bettercontact_client.py` code is already implemented and ready for activation

## Reactivation Steps
1. Obtain BetterContact API key
2. Add `BETTERCONTACT_API_KEY` to `.env`
3. Update `waterfall.py` to re-enable Step 2
4. Update this file with API docs
5. Test waterfall with both providers
