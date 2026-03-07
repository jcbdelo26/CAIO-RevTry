Load comprehensive codebase context before beginning any implementation work.

Run this command at the start of every new session, or whenever you need to re-orient to the current project state.

---

## Step 1 — Analyze Project Structure

```bash
git ls-files | grep -v "node_modules\|.next\|dist\|__pycache__" | head -150
```

Identify:
- Top-level folder organization
- Which directories contain the core application logic
- Config files at the root

---

## Step 2 — Read Core Documentation

Read these files in order (skip any that don't exist):

1. `.claude/PRD.md` — What we're building and why
2. `CLAUDE.md` — Project-specific conventions and patterns
3. `README.md` — Setup and usage instructions
4. `.agents/plans/` — List all existing plan files; read the most recent one

---

## Step 3 — Identify Key Files

Based on the project type, read the entry points and core modules:

**Next.js / React:**
- `src/app/layout.tsx` or `app/layout.tsx`
- `src/lib/db/schema.ts` (database schema)
- `src/lib/auth/` (auth setup)
- `src/app/api/` (API routes — list files)

**Node.js API:**
- `src/index.ts` or `src/main.ts`
- `src/routes/` or `src/controllers/`
- Database schema/models

**Python:**
- `app/main.py`
- `app/models/` or `models.py`
- `app/routes/` or `app/api/`

Read 2–3 representative files from each area to understand the coding patterns.

---

## Step 4 — Understand Current State

```bash
git log --oneline -10       # Recent commits
git status                   # Uncommitted changes
git branch --show-current   # Current branch
```

---

## Deliverable — Context Summary

Output a structured summary:

```
## Project: {name}
**Purpose**: {one-sentence description}
**Status**: {current phase / what's built / what's next}
**Branch**: {current git branch}

## Architecture
{How the code is organized — 3–5 bullet points}

## Tech Stack
| Layer | Technology |
|-------|-----------|
| {layer} | {tech} |

## Core Conventions
- Naming: {pattern}
- Error handling: {pattern}
- Testing: {where tests live, what runner}

## Current State
- Last commit: {message}
- Uncommitted changes: {count} files
- Active plan: {plan filename if exists}

## Ready to implement: {Y/N}
{If N, what needs to be done first}
```
