Create a comprehensive, implementation-ready feature plan and save it to `.agents/plans/{kebab-case-feature-name}.md`.

The goal is a plan so complete that another developer (or agent) can implement the feature successfully on the first attempt without additional research or clarification.

---

## Phase 1 — Feature Understanding

Extract from the request:
- **Core problem**: What user pain does this solve?
- **User stories**: Write 1–3 stories in "As a {user}, I want {action} so that {benefit}" format
- **Acceptance criteria**: What does "done" look like? (measurable, not vague)
- **Scope boundary**: What is explicitly NOT part of this feature?

---

## Phase 2 — Codebase Intelligence

Before proposing any solution, deeply understand the existing codebase:

1. **Project structure** — `git ls-files | grep -v node_modules` to see all tracked files
2. **Existing patterns** — Find similar features already implemented; read them and document the exact pattern to follow (with `file:line` references)
3. **Entry points** — Identify where this feature plugs in (routes, components, services, DB schema)
4. **Dependencies** — What packages are already available? Check `package.json`
5. **Types & interfaces** — Find existing types this feature will interact with
6. **Tests** — How are tests structured? Read an existing test file as a template
7. **API conventions** — If adding an API route, read an existing route for the exact pattern

Document every finding with specific file paths and line numbers.

---

## Phase 3 — External Research

Identify what you need to know that isn't in the codebase:
- New library APIs (fetch the documentation URL if needed)
- Framework-specific patterns (e.g., Next.js Server Actions, React Server Components)
- Database query patterns for the ORM in use
- Security considerations for this type of feature

Document: library name, version in use, relevant API calls, any gotchas.

---

## Phase 4 — Strategic Thinking

Before writing the plan:
- **Architecture fit**: Does the proposed approach match the existing patterns? If deviating, explain why
- **Edge cases**: List at least 3 edge cases and how each will be handled
- **Data model impact**: Will schema changes be needed? If so, plan the migration
- **Error states**: What can go wrong? How does the UI/API communicate failures?
- **Performance**: Any N+1 query risks, expensive computations, or caching needs?

---

## Phase 5 — Generate Plan

Write the plan to `.agents/plans/{descriptive-kebab-name}.md` with this exact structure:

```markdown
# Feature Plan — {Feature Name}

## Feature Description
{2–3 sentence description}

## User Stories
- **US-1**: As a {user}, I want {action} so that {benefit}

## Problem / Solution
**Problem**: {current pain point}
**Solution**: {how this feature solves it}

## Feature Metadata
- **Complexity**: Low / Medium / High
- **Estimated tasks**: {N}
- **New files**: {N}
- **Modified files**: {N}
- **Schema changes**: Yes / No

## Context References
<!-- Specific file:line pointers for patterns to follow -->
| Pattern | Reference |
|---------|-----------|
| {pattern name} | `{file}:{line}` |

## Architecture Decisions
- {decision and rationale}

## Implementation Tasks
<!-- Ordered by dependency — each task must be completable before the next starts -->

### Task 1 — {Name}
**File**: `{path}`
**Action**: {exactly what to do}
**Pattern to follow**: `{file}:{line}`
**Validation**: `{command to verify this task is correct}`

### Task 2 — {Name}
[same structure]

...

## Testing Strategy

### Unit Tests
- **File**: `{test file path}`
- **Cases**: {what to test}
- **Run**: `{command}`

### E2E Tests
- **Script**: `tests/e2e/{name}.sh`
- **Scenario**: {user journey to automate}

## Validation Commands
```bash
# Run in this exact order
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Acceptance Criteria
- [ ] {measurable criterion}
- [ ] All validation commands pass with zero errors
- [ ] No regressions in existing tests
```

---

## Quality Gate

Before saving the plan, verify:
- [ ] Every task has a specific file path (no vague "create a component" tasks)
- [ ] Every task references existing patterns from the codebase (with file:line)
- [ ] Tasks are ordered so each depends only on previously completed work
- [ ] All edge cases are addressed in specific tasks
- [ ] Validation commands are real, runnable commands (not placeholders)
- [ ] Acceptance criteria are measurable

A plan passes quality review when: another developer could implement it without asking any clarifying questions.
