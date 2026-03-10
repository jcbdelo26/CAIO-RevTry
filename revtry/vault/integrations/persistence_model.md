# Persistence Model

**Last Updated**: 2026-03-11
**Valid Through**: 2026-06-30

## Backends

| Mode | Backend | Config |
|------|---------|--------|
| Local dev | `STORAGE_BACKEND=file` | Human-readable JSON/Markdown |
| Deployed warm | `STORAGE_BACKEND=postgres` | `DATABASE_URL` canonical, `POSTGRES_URL` fallback |

Deployed warm mode must not use file-backed persistence.

## Implementation Files

- `src/persistence/base.py` — abstract interface
- `src/persistence/file_store.py` — local JSON/Markdown
- `src/persistence/postgres_store.py` — Neon postgres
- `src/persistence/factory.py` — backend selection
- `src/persistence/schema.sql` — postgres DDL

## Systems Using Backend Abstraction

- Warm follow-up storage, briefing loading, conversation scan/analysis persistence
- Warm orchestrator, warm dispatcher
- Rate limiter, circuit breaker, dedup

## Trace Logging

- File backend: writes trace files to `OUTPUTS_DIR`
- Postgres backend: emits structured JSON logs (no local trace files)
