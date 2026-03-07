---
name: e2e-test
description: Orchestrate end-to-end test creation and execution for a feature. Use this skill when a plan specifies E2E tests, when asked to "write E2E tests for X", or when validating a completed feature against its acceptance criteria.
user-invocable: true
argument-hint: [feature-name or test-description]
allowed-tools: Bash, Read, Write, Glob
---

# E2E Test Orchestration Skill

This skill guides the full lifecycle of E2E test creation: identifying what to test, writing the test scripts, making them executable, and running them against a live dev server.

---

## When to Use This Skill

- After completing a feature implementation (validate acceptance criteria)
- When a plan file specifies E2E test scripts to create
- When asked to "add E2E coverage" for an existing feature
- As part of the validation phase before committing

---

## Step 1 — Identify Test Scenarios

From the feature description or plan, extract:
1. **Happy path**: The primary successful user journey
2. **Error paths**: Invalid input, unauthorized access, not found states
3. **Boundary conditions**: Empty states, maximum input lengths, etc.

Organize into a test matrix:
```
| Scenario | Path | Actions | Expected Outcome |
|----------|------|---------|-----------------|
| {name}   | /{route} | {steps} | {what to assert} |
```

---

## Step 2 — Check Prerequisites

```bash
# Verify agent-browser is installed
agent-browser --version || echo "Run: agent-browser install"

# Verify dev server is running
curl -s http://localhost:{PORT}/health || curl -s http://localhost:{PORT}/ | head -5
```

If the dev server isn't running: `npm run dev` (or equivalent) and wait for it to be ready.

---

## Step 3 — Set Up Test Directory

```bash
mkdir -p tests/e2e/screenshots
```

Check for existing test scripts:
```bash
ls tests/e2e/*.sh 2>/dev/null
```

---

## Step 4 — Write Test Script

Create `tests/e2e/{feature-name}.sh` following the agent-browser skill's template.

Each script must:
- Use `set -e` (fail fast)
- Print progress messages for each test case
- Call `agent-browser screenshot` after key state changes
- Track pass/fail counts
- Exit with code 1 if any test fails

For the content of each test step, use the agent-browser CLI commands:
```bash
agent-browser open <url>
agent-browser find label "<label>" fill "<value>"
agent-browser find role button click --name "<name>"
agent-browser wait --url "**<pattern>"
agent-browser find text "<expected>"
agent-browser screenshot <path>
```

---

## Step 5 — Make Executable and Run

```bash
chmod +x tests/e2e/{feature-name}.sh
bash tests/e2e/{feature-name}.sh
```

---

## Step 6 — Update Master Runner

If `tests/e2e/run-all.sh` exists, add the new test:
```bash
run_test "tests/e2e/{feature-name}.sh"
```

If it doesn't exist, create it (see agent-browser skill for template).

---

## Step 7 — Report Results

After running, output:
```
## E2E Test Results — {Feature Name}

**Scripts created**: tests/e2e/{feature-name}.sh
**Test cases**: {N} scenarios
**Screenshots**: tests/e2e/screenshots/

**Results**:
✅ {scenario 1}
✅ {scenario 2}
❌ {scenario 3} — {failure reason and fix applied}

**Final status**: {PASS / FAIL}
```

If any tests fail: diagnose the failure, fix either the test or the implementation, re-run, and confirm all pass before reporting success.

---

## Package.json Integration

Ensure `test:e2e` script exists in `package.json`:
```json
{
  "scripts": {
    "test:e2e": "bash tests/e2e/run-all.sh"
  }
}
```

Run with: `npm run test:e2e`
