Execute an implementation plan from a plan file.

Usage: `execute [path-to-plan]`

If no path is provided, look for the most recent plan in `.agents/plans/`.

---

## Execution Process

### Phase 1 — Understand the Plan

Read the ENTIRE plan file carefully before writing a single line of code:
- Identify all tasks and their dependencies
- Note the validation commands for each step
- Understand the testing strategy
- Flag any ambiguities before starting

If anything is unclear, ask for clarification NOW — not mid-implementation.

---

### Phase 2 — Implement Tasks in Order

Execute tasks sequentially, following the dependency order in the plan:

For each task:
1. Navigate to the specified file(s)
2. Implement exactly what the plan specifies
3. After each file change: verify syntax compiles and imports resolve
4. Do NOT skip steps, reorder tasks, or add unrequested functionality

Follow the patterns and conventions documented in the plan. If the plan references a file:line pattern to follow, read that reference before implementing.

---

### Phase 3 — Run Tests

After implementation tasks are complete:
1. Create all test files specified in the plan
2. Implement each test case including edge cases
3. Run tests: if any fail, fix the implementation before continuing

---

### Phase 4 — Validate

Run every validation command from the plan **in exact order**:

```bash
# Typical validation sequence (use commands from the plan, not these examples)
npm run lint          # Fix any lint errors before proceeding
npx tsc --noEmit      # Fix all type errors before proceeding
npm run test:run      # All tests must pass
npm run build         # Build must succeed with no warnings
```

For each failing command: fix the issue, re-run the command, confirm it passes before moving to the next.

---

### Phase 5 — Final Verification

Before signaling completion, confirm:
- [ ] Every task in the plan is implemented
- [ ] All validation commands pass with zero errors
- [ ] No code conventions were violated
- [ ] No unrequested features were added
- [ ] All new files are in the locations specified by the plan

---

### Completion Report

Output a summary:
```
## Execution Complete

**Plan**: {plan filename}
**Tasks completed**: {N}/{N}
**Tests added**: {count} unit, {count} E2E
**Validation**: lint ✅ | tsc ✅ | tests ✅ | build ✅

**Deviations from plan** (if any):
- {deviation and reason}

Ready to commit with: /commit
```
