# CLAUDE.md — RevTry (Revenue Operations Sentry)

This file guides all development work inside `E:\Greenfield Coding Workflow\Project-RevTry\`.

---

## Project Overview

RevTry is a Revenue Operations Sentry for ChiefAIOfficer.com. It discovers leads via Apollo, enriches them through a waterfall, scores them against an ICP model, drafts personalized outreach, validates drafts through a 3-gate system, and surfaces them on a FastAPI approval dashboard for human review before any send.

---

## Workspace Layout

All development code lives here. Operational docs (vault, registry, agent configs) live in the runtime workspace and are referenced via environment variables.

```
Project-RevTry/
├── CLAUDE.md                    # This file
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Template with all required vars
├── .claude/
│   ├── PRD.md                   # Product Requirements Document
│   └── commands/                # Scaffold slash commands
├── .agents/
│   └── plans/                   # Phase implementation plans
└── src/
    ├── pyproject.toml           # Project config + dependencies
    ├── requirements.txt         # Flat dependency list
    ├── models/
    │   └── schemas.py           # 18 Pydantic v2 models (all agent I/O)
    ├── utils/
    │   ├── vault_loader.py      # Parse vault .md files → typed data
    │   ├── exclusion_checker.py # Domain/email blocklist checker
    │   └── trace_logger.py      # JSON trace logging
    ├── integrations/
    │   ├── apollo_client.py     # Apollo.io async HTTP client
    │   ├── bettercontact_client.py  # Deferred — kept for reactivation
    │   ├── clay_client.py       # Deferred — kept for reactivation
    │   └── waterfall.py         # Apollo-only enrichment waterfall
    ├── agents/
    │   ├── recon_agent.py       # Lead discovery via Apollo search
    │   ├── enrichment_agent.py  # Waterfall enrichment orchestrator
    │   ├── segmentation_agent.py # ICP scoring + tier assignment
    │   └── campaign_craft_agent.py # Draft generation with angles
    ├── validators/
    │   ├── gate1_validator.py   # Structural validation (6 checks)
    │   ├── gate2_validator.py   # Compliance validation (10 checks)
    │   ├── gate3_validator.py   # Business alignment (7 checks)
    │   └── guards.py            # GUARD-001 through GUARD-005
    ├── dashboard/
    │   ├── app.py               # FastAPI approval dashboard
    │   ├── storage.py           # File-based draft storage
    │   └── templates/           # Jinja2 HTML templates
    ├── pipeline/
    │   ├── runner.py            # E2E pipeline orchestrator
    │   └── feedback_processor.py # Rejection feedback handler
    └── tests/
        └── (tests co-located here)
```

### Runtime Workspace (Read-Only Reference)

Vault and registry docs at `e:/CAIO RevOps Claw/revtry/`:

```
revtry/
├── vault/
│   ├── integrations/            # API configs (apollo.md, etc.)
│   ├── compliance/              # exclusions.md, signatures.md
│   ├── scoring/                 # scoring_rules.md, tier_definitions.md
│   └── product/                 # proof_points.md, cta_library.md
├── registry/                    # Task registry, locks, phase gates
└── agents/                      # Agent config .md files
```

Connected via `.env`:
```
VAULT_DIR=e:/CAIO RevOps Claw/revtry/vault
REGISTRY_DIR=e:/CAIO RevOps Claw/revtry/registry
```

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | All application code |
| Pydantic v2 | Data models + validation |
| httpx | Async HTTP client (Apollo API) |
| FastAPI + Jinja2 | Approval dashboard |
| python-dotenv | Environment variable loading |
| Apollo.io API | Lead discovery + enrichment (primary) |
| GoHighLevel (GHL) | CRM source of truth |

---

## Environment Variables

See `.env.example` for all required variables. Critical ones:

| Variable | Required | Purpose |
|----------|----------|---------|
| `GHL_API_KEY` | Yes | GoHighLevel API access |
| `GHL_LOCATION_ID` | Yes | GHL location identifier |
| `APOLLO_API_KEY` | Yes | Apollo.io lead data |
| `VAULT_DIR` | Yes | Path to vault markdown files |
| `REGISTRY_DIR` | Yes | Path to task registry |

---

## Architecture

### Pipeline Flow

```
Recon → Enrichment → GUARD-003 filter → Segmentation → DQ filter → Campaign Craft → Gates 1-3 → Dashboard
```

### ICP Scoring

6 components (max base 100): Company Size (20), Title (25), Industry (20), Revenue (15), Tech Signal (10), Engagement (10). Base score multiplied by industry multiplier (0.8x-1.5x). Tiers: T1 >= 80, T2 >= 60, T3 >= 40, DQ < 40.

### Enrichment

Apollo-only for Phase 1. BetterContact and Clay are deferred (code exists, not active in waterfall). Deferred providers always return `SKIPPED` status in `WaterfallTrace`.

### Validation

- **Gate 1** — Structural: valid JSON, required fields, types, no placeholders (6 checks)
- **Gate 2** — Compliance: subject length, exclamations, ALL-CAPS, banned openers, CAN-SPAM, booking link (10 checks)
- **Gate 3** — Business alignment: ICP math, angle-tier match, specificity, proof points (7 checks)
- **Guards** — GUARD-001 (rejection count), GUARD-002 (duplicate hash), GUARD-003 (enrichment score < 70), GUARD-004 (banned openers), GUARD-005 (generic density)

---

## Development Commands

```bash
# Validate syntax (all 28 files)
find src -name "*.py" -exec python -m py_compile {} +

# Run import chain check
cd src && python -c "
from models.schemas import *
from utils.vault_loader import *
from utils.exclusion_checker import *
from utils.trace_logger import *
from integrations.apollo_client import *
from integrations.waterfall import *
from agents.recon_agent import *
from agents.enrichment_agent import *
from agents.segmentation_agent import *
from agents.campaign_craft_agent import *
from validators.gate1_validator import *
from validators.gate2_validator import *
from validators.gate3_validator import *
from validators.guards import *
from dashboard.storage import *
from pipeline.feedback_processor import *
from pipeline.runner import *
print('All imports OK')
"

# Start approval dashboard
cd src && uvicorn dashboard.app:app --reload --port 8000

# Run tests
cd src && python -m pytest tests/
```

---

## Code Patterns

- **Pydantic v2** with `model_config = ConfigDict(populate_by_name=True)` and camelCase aliases
- **Vault loading** via `vault_loader.py` — parses markdown tables into typed dataclasses
- **Async HTTP** via httpx with timeout (30s), retry (2x on 5xx), rate limit handling (429)
- **File-based storage** for drafts at `outputs/drafts/*.json`
- **Trace logging** — every agent produces a JSON trace file

---

## Agent Communication Rules

1. **Recommended Next Steps** — At the end of every completed phase, session, or milestone, always output a numbered list of recommended next steps for the user. Never end a session without telling the user what comes next.

2. **Non-Technical Navigational Guides** — When the user must take action on external platforms (obtaining API keys, configuring integrations, account setup), present a step-by-step guide written for a non-technical PTO. Include exact URLs, precise UI navigation ("click the gear icon top-right"), what to copy/paste, and expected outcomes at each step.

3. **Ask Before Assuming** — Use AskUserQuestion proactively when facing architecture choices, scope decisions, provider selection, or any ambiguity that affects the product. Do not guess — ask.

---

## Anti-Patterns

- Do not fabricate, estimate, or mock data (anti-mocking rule)
- Do not pass leads with `enrichment_score < 70` to Campaign Craft (GUARD-003)
- Do not pass leads with `email = null` to outreach
- Do not use BetterContact or Clay providers (deferred)
- Do not commit `.env` files with real API keys
- Do not end a phase or session without presenting recommended next steps
- Do not assume user decisions — ask via AskUserQuestion when in doubt

---

## Current Status

**Phase 1 complete**: 28 Python files, ~3,300 lines. All modules compile and import.

**Enrichment**: Apollo-only (BetterContact deferred — no subscription; Clay deferred — webhook/table model).

**Next**: Populate remaining vault stubs (`proof_points.md`, `cta_library.md`), write tests, end-to-end validation with live API keys.
