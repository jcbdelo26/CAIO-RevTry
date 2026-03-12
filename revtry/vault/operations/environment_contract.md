# Environment Contract

**Last Updated**: 2026-03-13
**Valid Through**: 2026-06-30

## All Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `GHL_API_KEY` | Yes | — | GHL API access |
| `GHL_LOCATION_ID` | Yes | — | GHL location scope + dispatch history GHL links |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API for analysis + drafting. Key must come from Anthropic **Default workspace** (Josh's account). All `load_dotenv()` calls use `override=True` so `.env` always wins over any Windows system/user env vars. |
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
| `FOLLOWUP_SCAN_DAYS` | No | `90` | Conversation lookback window |
| `SALES_TEAM_USER_IDS` | No | — | Comma-separated GHL user IDs for Active Deal badge tagging |
| `SCHEDULER_ENABLED` | No | `false` | Start APScheduler on boot |
| `SCHEDULER_TIMEZONE` | No | `America/Chicago` | Cron timezone |
| `DISPATCH_DRY_RUN` | No | `false` | Log dispatch payload without sending |
| `CRON_SECRET` | Conditional | — | Vercel cron endpoint auth |
| `MAX_SCAN_CONTACTS` | Deprecated | — | Use `DAILY_SCAN_BATCH_SIZE` |
| `ALERT_SLACK_WEBHOOK_URL` | No | — | Slack Incoming Webhook URL; fires when all drafts fail (`draft_failed >= actionable`) or any dispatch fails (`dispatch.failed > 0`) |

## Fail-Fast Rules

- `GHLClient` raises `MissingGhlCredentialsError` when GHL credentials are absent
- `validate_storage_configuration()` fails startup if `WARM_ONLY_MODE=true` without postgres

## Known Operational Notes

- **Windows env var override**: All `load_dotenv()` calls use `override=True` (added 2026-03-13) to ensure `.env` values always take precedence over Windows User/System environment variables. If pipeline returns "credit balance too low" despite a valid key in `.env`, check for a stale `ANTHROPIC_API_KEY` in Windows Environment Variables (User and System sections) and delete it.
- **Anthropic 529 overloaded**: Retry backoff for 529 errors is 30s × (attempt+1). MAX_RETRIES=3 (4 total attempts). Run pipeline during off-peak hours (before 7 AM CT) for best success rates with 50-contact batches.
- **WARM_ONLY_MODE**: `.env` must have only one `WARM_ONLY_MODE` line. Duplicate entries cause the last value to win (python-dotenv behavior).
