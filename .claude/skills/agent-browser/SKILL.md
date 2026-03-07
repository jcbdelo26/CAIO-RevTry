---
name: agent-browser
description: Run E2E browser automation tests using the Vercel Agent Browser CLI. Use this skill when writing or executing end-to-end tests for web applications, automating user journeys, or verifying UI behavior in a real browser.
user-invocable: true
argument-hint: [test-script-path or scenario-description]
allowed-tools: Bash, Read, Write, Glob
---

# Agent Browser — E2E Testing Skill

The Vercel Agent Browser CLI (`agent-browser`) is a headless browser automation tool designed to work natively with Claude Code. Unlike Playwright or Cypress, it uses CLI commands chained in bash scripts — no test framework files required.

---

## Prerequisites

```bash
# Install once per machine
agent-browser install

# Verify installation
agent-browser --version
```

The dev server must be running before executing any E2E tests.

---

## CLI Command Reference

### Navigation
```bash
agent-browser open <url>
# Example: agent-browser open http://localhost:3000/login
```

### Snapshot (Get Interactive Element References)
```bash
agent-browser snapshot -i
# Returns: list of interactive elements with refs (@e1, @e2, etc.)
# Use refs in subsequent commands
```

### Fill Input
```bash
agent-browser find label "<label-text>" fill "<value>"
# Example: agent-browser find label "Email" fill "user@example.com"
```

### Click Element
```bash
agent-browser find role button click --name "<button-text>"
# Example: agent-browser find role button click --name "Sign In"
```

### Wait for Navigation
```bash
agent-browser wait --url "**<pattern>"
# Example: agent-browser wait --url "**/dashboard"
```

### Screenshot
```bash
agent-browser screenshot <output-path>
# Example: agent-browser screenshot tests/e2e/screenshots/login-success.png
```

### Assert Text
```bash
agent-browser find text "<expected-text>"
# Fails if text not found on page
```

---

## Writing E2E Test Scripts

Each test is a bash script in `tests/e2e/`. Filename convention: `{feature}.sh`

### Template
```bash
#!/bin/bash
set -e  # Exit on any error

BASE_URL="${BASE_URL:-http://localhost:3000}"
PASS=0
FAIL=0

echo "=== E2E Test: {Feature Name} ==="

# Test 1 — {Scenario Name}
echo "Test 1: {what is being tested}"
agent-browser open "$BASE_URL/{path}"
agent-browser find label "{Field}" fill "{value}"
agent-browser find role button click --name "{Button}"
agent-browser wait --url "**/{expected-path}"
agent-browser find text "{expected-text}"
agent-browser screenshot "tests/e2e/screenshots/{test-name}.png"
echo "✅ Test 1 passed"
PASS=$((PASS + 1))

# Test 2 — {Scenario Name}
echo "Test 2: {what is being tested}"
# ...
PASS=$((PASS + 1))

# Summary
echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
  exit 1
fi
```

### Make executable
```bash
chmod +x tests/e2e/{name}.sh
```

---

## Standard Test Scripts to Create

For any web application, create these scripts:

| Script | Scenario |
|--------|---------|
| `tests/e2e/auth.sh` | Sign up, log in, log out |
| `tests/e2e/crud.sh` | Create, read, update, delete core entities |
| `tests/e2e/navigation.sh` | Key page routes load without errors |
| `tests/e2e/run-all.sh` | Master runner that calls all scripts |

### Master runner template (`tests/e2e/run-all.sh`):
```bash
#!/bin/bash
set -e

PASS=0
FAIL=0

run_test() {
  local script=$1
  echo "Running: $script"
  if bash "$script"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "❌ FAILED: $script"
  fi
}

run_test "tests/e2e/auth.sh"
run_test "tests/e2e/crud.sh"
run_test "tests/e2e/navigation.sh"

echo ""
echo "=== E2E Suite Complete ==="
echo "Passed: $PASS | Failed: $FAIL"
[ $FAIL -eq 0 ] || exit 1
```

---

## Running Tests

```bash
# Single test
bash tests/e2e/auth.sh

# All tests
npm run test:e2e   # (configured in package.json)
# or
bash tests/e2e/run-all.sh
```

Add to `package.json`:
```json
{
  "scripts": {
    "test:e2e": "bash tests/e2e/run-all.sh"
  }
}
```

---

## Tips

- Always screenshot after key actions for debugging failures
- Use `set -e` in scripts so failures are caught immediately
- Test both happy path AND error paths (invalid input, unauthorized access)
- Run E2E tests last in the validation chain (after unit tests and build)
