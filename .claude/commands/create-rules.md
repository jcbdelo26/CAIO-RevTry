Analyze the current codebase and generate a `CLAUDE.md` file at the project root with accurate, project-specific guidance.

---

## Phase 1 — DISCOVER

Identify the project type and read core configuration:

```bash
# Check project type indicators
ls -la
cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || cat Cargo.toml 2>/dev/null
cat tsconfig.json 2>/dev/null
cat .env.example 2>/dev/null
```

Determine:
- Project type (Next.js app, API service, library, CLI tool, monorepo, etc.)
- Package manager (npm, pnpm, bun, yarn, uv, cargo)
- Runtime/language (TypeScript, Python, Rust, etc.)

---

## Phase 2 — ANALYZE

Gather deep understanding of the codebase:

1. **Directory structure** — Run `git ls-files | head -100` and identify the folder organization pattern
2. **Tech stack** — Read `package.json` dependencies, identify frameworks, ORMs, test runners
3. **Entry points** — Find `src/index.ts`, `app/page.tsx`, `main.py`, etc.
4. **Key patterns** — Read 3–5 representative source files to identify:
   - Naming conventions (camelCase, snake_case, kebab-case, PascalCase)
   - Error handling approach
   - How types/interfaces are defined
   - How tests are structured
5. **Commands** — Identify actual dev, build, test, lint commands from `package.json` scripts or `Makefile`

---

## Phase 3 — GENERATE

Write `CLAUDE.md` at the project root using this structure. Keep it **concise and scannable** — this file is read on every session. Focus on patterns that aren't self-evident:

```markdown
# CLAUDE.md

## Project Overview
{One paragraph: what this project is and its purpose}

## Tech Stack
| Technology | Purpose |
|------------|---------|
| {tech} | {purpose} |

## Commands
```bash
# Development
{actual-dev-command}

# Build
{actual-build-command}

# Test
{actual-test-command}

# Lint / Type check
{actual-lint-command}
```

## Project Structure
```
{root}/
├── {dir}/     # {description}
```

## Architecture
{How the code is organized, data flow, key abstractions}

## Code Patterns
### Naming
- {convention}
### Error Handling
- {pattern}
### Testing
- {where tests live, what framework, what to test}

## Key Files
| File | Purpose |
|------|---------|
| `{path}` | {description} |

## On-Demand Context
| Topic | File |
|-------|------|
| Product requirements | `.claude/PRD.md` |
| Implementation plans | `.agents/plans/` |

## Notes
- {important gotcha or constraint}
```

---

## Phase 4 — OUTPUT

Report:
- Project type identified
- Tech stack summary
- Key patterns discovered
- File written to: `CLAUDE.md`
- Next step: Review and refine any sections that need more specificity
