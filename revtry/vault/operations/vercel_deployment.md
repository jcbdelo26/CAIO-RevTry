# Vercel Deployment Reference

**Last Updated**: 2026-03-11
**Valid Through**: 2026-06-30

## Deployment Files

- `api/index.py` — Vercel serverless entry point (adds `src/` to sys.path, imports FastAPI app)
- `vercel.json` — Build/route config (all traffic → `api/index.py`), cron jobs, maxDuration
- `requirements.txt` (root) — Production dependencies for Vercel

## Vercel Config

- Plan: Pro ($20/mo) — 300s function timeout
- Cron: `GET /api/cron/warm-pipeline` at `0 12 * * *` (12:00 UTC / 6 AM CT)
- Auth: `CRON_SECRET` Bearer token for cron endpoint
- Domain: `caio-rev-try.vercel.app`

## Required Environment Variables (Vercel Dashboard)

`DATABASE_URL`, `STORAGE_BACKEND=postgres`, `WARM_ONLY_MODE=true`,
`DASHBOARD_AUTH_ENABLED=true`, `DASHBOARD_BASIC_AUTH_USER`, `DASHBOARD_BASIC_AUTH_PASS`,
`GHL_API_KEY`, `GHL_LOCATION_ID`, `ANTHROPIC_API_KEY`, `CRON_SECRET`,
`DISPATCH_DRY_RUN` (true until live dispatch approved)
