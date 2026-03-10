# Code Structure Reference

**Last Updated**: 2026-03-11
**Valid Through**: 2026-06-30

## Agents
- `src/agents/conversation_analyst_agent.py` — Analyzes GHL conversations
- `src/agents/followup_draft_agent.py` — Generates warm follow-up drafts
- `src/agents/campaign_craft_agent.py` — Cold campaign drafts

## Dashboard
- `src/dashboard/app.py` — FastAPI routes (briefing, followups, dispatch, cron)
- `src/dashboard/auth.py` — HTTP Basic Auth
- `src/dashboard/followup_storage.py` — Warm draft CRUD
- `src/dashboard/briefing_loader.py` — Daily briefing data
- `src/dashboard/storage.py` — Cold draft CRUD

## Pipeline
- `src/pipeline/followup_orchestrator.py` — Warm pipeline entry point
- `src/pipeline/followup_dispatcher.py` — Warm dispatch engine
- `src/pipeline/scheduler.py` — APScheduler cron (local dev)
- `src/pipeline/dispatcher.py` — Cold dispatch engine
- `src/pipeline/rate_limiter.py` — Daily send limits
- `src/pipeline/circuit_breaker.py` — Failure circuit breaker
- `src/pipeline/dedup.py` — Content/contact dedup

## Integrations
- `src/integrations/ghl_client.py` — GHL API client
- `src/integrations/anthropic_client.py` — Claude API client

## Models
- `src/models/schemas.py` — All Pydantic models

## Validators
- `src/validators/followup_gate2_validator.py` — Compliance validation
- `src/validators/followup_gate3_validator.py` — Business alignment
- `src/validators/gate1_validator.py` — Structural validation
