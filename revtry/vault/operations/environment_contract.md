# Environment Contract

**Last Updated**: 2026-03-11
**Valid Through**: 2026-06-30

## All Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `GHL_API_KEY` | Yes | — | GHL API access |
| `GHL_LOCATION_ID` | Yes | — | GHL location scope + dispatch history GHL links |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API for analysis + drafting |
| `APOLLO_API_KEY` | No | — | Cold enrichment (Phase 4) |
| `VAULT_DIR` | No | auto-detected | Path to `revtry/vault/` |
| `REGISTRY_DIR` | No | `registry` | Scheduler state, dispatch logs |
| `STORAGE_BACKEND` | Yes | `file` | `file` (local) or `postgres` (deployed) |
| `DATABASE_URL` | Conditional | — | Required when `STORAGE_BACKEND=postgres` |
| `WARM_ONLY_MODE` | No | `false` | Hides cold routes when `true` |
| `DASHBOARD_AUTH_ENABLED` | No | `false` | Enable HTTP Basic Auth |
| `DASHBOARD_BASIC_AUTH_USER` | Conditional | — | Required when auth enabled |
| `DASHBOARD_BASIC_AUTH_PASS` | Conditional | — | Required when auth enabled |
| `DAILY_SCAN_BATCH_SIZE` | No | `50` | Max contacts per pipeline run |
| `FOLLOWUP_SCAN_DAYS` | No | `30` | Conversation lookback window |
| `SCHEDULER_ENABLED` | No | `false` | Start APScheduler on boot |
| `SCHEDULER_TIMEZONE` | No | `America/Chicago` | Cron timezone |
| `DISPATCH_DRY_RUN` | No | `false` | Log dispatch payload without sending |
| `CRON_SECRET` | Conditional | — | Vercel cron endpoint auth |
| `MAX_SCAN_CONTACTS` | Deprecated | — | Use `DAILY_SCAN_BATCH_SIZE` |

## Fail-Fast Rules

- `GHLClient` raises `MissingGhlCredentialsError` when GHL credentials are absent
- `validate_storage_configuration()` fails startup if `WARM_ONLY_MODE=true` without postgres
