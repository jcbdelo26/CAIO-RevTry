# RevTry — Codex Review & Bulletproofing Handoff

**Date**: 2026-03-06
**Author**: Chris Daigle / Claude Code planning session
**Purpose**: Deep review and bulletproofing of the RevTry planning artifacts before Phase 0 execution begins
**Status**: Pre-execution — no files have been created in `e:/CAIO RevOps Claw/` yet (except legacy source files)

---

## YOUR ROLE AS CODEX

You are reviewing a complete agentic system plan before the first line of implementation begins. Your job is to:

1. **Read all artifacts listed below** — in the order given
2. **Identify every ambiguity, gap, contradiction, or unstated assumption** that would cause an implementing agent to pause, guess, or produce wrong output
3. **Verify all cross-references** — every file name, path, tool name, and section reference that is mentioned in one document must match what is specified elsewhere
4. **Validate implementation feasibility** — every task in the Phase 0 plan must be executable with Claude Code on Windows 11, using only the tools available (markdown files, Python MCP, bash commands)
5. **Produce a structured review report** organized by severity: BLOCKER → MAJOR → MINOR → SUGGESTION

Do not implement anything. Do not write any files. Read, analyze, and report only.

---

## WHAT WAS BUILT IN THIS PLANNING SESSION

This was a planning-only session that produced three primary artifacts for the RevTry project — a Revenue Operations agentic system for ChiefAIOfficer.com.

### Existing Source Material (PRESERVED — do not modify)
| File | Location | Description |
|------|----------|-------------|
| Source PRD (v1.0) | `E:\CAIO RevOps Claw\RevTry_PRD.md` | 66KB original Codex handoff document |
| Legacy GEMINI.md | `E:\CAIO RevOps Claw\GEMINI.md` | Core system prompt from previous architecture |
| Legacy vault files | `E:\CAIO RevOps Claw\vault\` | 7 existing files with business rules content |
| GHL MCP server | `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py` | 31KB production-ready Python MCP server |

### Planning Artifacts Created (READ THESE FOR REVIEW)
| File | Location | Description |
|------|----------|-------------|
| **Bulletproofed PRD v2.0** | `e:\Greenfield Coding Workflow\Project-RevTry\.claude\PRD.md` | ~80KB refined PRD with all workflow standard sections |
| **Project CLAUDE.md** | `e:\Greenfield Coding Workflow\Project-RevTry\CLAUDE.md` | Agent guidance file for this project |
| **Phase 0 Plan** | `e:\Greenfield Coding Workflow\Project-RevTry\.agents\plans\phase-0-foundation-ghl-triage.md` | 19-task implementation plan |

---

## REVIEW TASK 1: READ THE PRD

**File**: `e:\Greenfield Coding Workflow\Project-RevTry\.claude\PRD.md`

This is the master document. Read all 20 sections:

| Section | Title | Review Focus |
|---------|-------|-------------|
| §0 | Critical Read-First | Dependency preflight — is every step actionable and complete? |
| §1 | Project Overview | |
| §1A | Mission | |
| §1B | Target Users | |
| §2 | Tech Stack | Are all technologies actually needed in Phase 0? Are versions specified where needed? |
| §3 | User Stories | Are all stories testable with acceptance criteria? |
| §4 | Data Models | Are all fields complete? Are FK relationships sound? Are nullable fields explicitly marked? |
| §5 | System Architecture | Is the PIV Loop implementable with Claude Code only? Does maker-checker separation work with Claude Code sessions? |
| §6 | Implementation Phases | Are Phase 0 ACs binary and measurable? |
| §7 | Out of Scope | Are scope boundaries tight enough to prevent scope creep? |
| §8 | Success Criteria | Are all criteria binary? |
| §9 | Risks | Are there risks missing from this table? |
| §10 | File Structure | Does the tree match what's built in Phase 0 plan tasks? |
| §11 | File Specifications | Are the 6 slash commands internally consistent with each other? |
| §12 | Vault File Specs | Do all vault files follow the 7 Laws? Are all compliance lists complete? |
| §13 | Agent Specifications | Does the permission matrix prevent all unauthorized actions? |
| §14 | Guardrail Specs | Are all rules binary? Is every guardrail enforceable without human interpretation? |
| §15 | Task Spec Template | Does the template generate specs that the /execute command can run without gaps? |
| §16 | Registry Initialization | Do table schemas support all runtime operations? |
| §17 | Phase 0 Sequence | Does it match the Phase 0 plan tasks? |
| §18 | Phase 0 Verification | Are all 23 checks actually verifiable? |
| §19 | Team & Approval Flows | Are approval flows unambiguous? |
| §20 | Phase Roadmap | Are phases independent of each other? |

---

## REVIEW TASK 2: READ THE PHASE 0 PLAN

**File**: `e:\Greenfield Coding Workflow\Project-RevTry\.agents\plans\phase-0-foundation-ghl-triage.md`

This is a 19-task implementation plan. For each task verify:

1. **Dependency order**: Does each task depend only on tasks that precede it?
2. **Completeness**: Does the task specify EXACTLY what to write (content, not just "create this file")?
3. **Path accuracy**: Do all file paths match the PRD §10 file structure exactly?
4. **Windows compatibility**: Are bash commands valid on Windows 11 with bash shell?
5. **Validation**: Is the task's validation command runnable immediately after the task?

**Specific checks for Phase 0 plan:**

| Task | Specific Review Questions |
|------|--------------------------|
| Task 3 | The `pip install aiohttp mcp python-dotenv` command — is `mcp` the correct package name for the Model Context Protocol Python library? What is the actual PyPI package name? |
| Task 4 | The `/execute` command includes "generate session_id as {agent}-{YYYYMMDD}-{HHMM}-{random4hex}" — is {random4hex} generated by the agent or by the system? How does Claude Code generate random hex? |
| Task 8 | The `ghl.md` VERIFIED TOOLS section is left as a placeholder for live discovery — but the Phase 0 plan has Task 15 running the audit via sub-agent. Does live tool discovery actually happen in Task 15, or is it a separate step? |
| Task 14 | The GHL audit output schema includes `icp_field_readiness: "READY|FALLBACK_REQUIRED"` — what is the exact decision rule for choosing READY vs FALLBACK_REQUIRED? |
| Task 15 | "Run Pipeline Ops as a sub-agent using Claude Code's built-in Agent tool" — does Claude Code have a built-in Agent tool? Verify this is accurate. |
| Task 16 | The validate step updates `vault/integrations/ghl.md` VERIFIED TOOLS section with live discovery results — but the `/validate` command (as specified in PRD §11.3) does NOT write to vault files. Is there a missing step between validate and updating the vault? |
| Tasks 18-19 | The triage task requires Chris to open "a NEW Claude Code session" — how exactly does this work in Claude Code? Is a new window, a new conversation, or something else? |

---

## REVIEW TASK 3: CROSS-REFERENCE VERIFICATION

Check every cross-reference between documents. Look for:

### A. Tool Name Consistency
The GHL MCP server (`server.py`) was verified to have **15 tools** in production. The PRD §12.7 lists **14 tools**. Identify:
- Which tool is missing from the PRD list?
- Does this missing tool matter for Phase 0?
- Does the "verify live" instruction adequately handle this discrepancy?

### B. File Path Consistency
The Phase 0 plan creates files at `e:/CAIO RevOps Claw/revtry/...`. The PRD §10 specifies the same paths. Verify every path in the plan tasks matches §10 exactly. Flag any mismatches.

### C. Slash Command Cross-References
The 6 slash commands reference each other and reference vault/registry files. Verify:
- `/prime` reads 6 specific files — do all 6 files get created before any agent runs `/prime`?
- `/execute` checks `failures.md` attempt count before running — does `failures.md` schema (PRD §16) support this query?
- `/validate` sends Slack notification on PASS — does this require additional Python code or is it a Claude Code MCP call?
- `/metabolize` is "auto-called by /validate" — how exactly does `/validate` invoke `/metabolize` in Claude Code?

### D. Retry Counter Logic
PRD §5 (Architecture) says "Ralph Loop V2: max 3 attempts." PRD §15 (Task Spec Template §7) says "max 3 retry attempts tracked in registry/failures.md by task_id." The Phase 0 plan Task 14 (triage task spec) says "max 3 retry attempts."

Verify: The failures.md schema has an "Attempt #" column. Does the `/execute` command's Step 2 actually check this column correctly? Trace the exact logic:
1. First run: failures.md has 0 entries for task_id → proceed
2. First failure: 1 entry added → attempt count = 1
3. Second run: 1 entry found → attempt count is 1, max is 3, proceed
4. Third run: 2 entries found → proceed
5. Fourth run: 3 entries found → STOP and escalate

Is this logic explicit in the `/execute` command as written in PRD §11.3?

### E. session_id Generation
PRD §4 (Data Models) defines: `{agent}-{YYYYMMDD}-{HHMM}-{random4hex}`. Example: `pipeline-ops-20260306-0930-a4f2`.

The `/execute` command (PRD §11.3) says: "generate session_id as {agent}-{YYYYMMDD}-{HHMM}-{random4hex}."

Verify: Claude Code has no built-in random hex generator. Can Claude (as an LLM) reliably generate sufficiently random 4-hex values? Is this specification robust enough?

---

## REVIEW TASK 4: ARCHITECTURAL SOUNDNESS

### A. Maker-Checker in Practice
The PRD mandates that "the session that creates output CANNOT validate it." In Claude Code:
- Opening a new conversation window = new session ✅
- The `/execute` command says "This command runs in a FRESH Claude Code session"
- The `/validate` command says "MUST run in a DIFFERENT fresh session"

**Question**: Is there a technical enforcement mechanism for this, or is it purely honor-system? What happens if Chris runs `/execute` and then immediately runs `/validate` in the same window? Does the `session_id` in `active.md` provide any enforcement?

### B. Sub-Agent Isolation
PRD §13.1 says: "Research tasks (read-only) → Sub-agents using built-in Agent tool."

The Phase 0 GHL audit runs as a sub-agent. But:
- Does a sub-agent spawned by Claude Code's Agent tool inherit the parent session's MCP server connections (GHL)?
- If the parent session has GHL MCP loaded, does the sub-agent also have access to GHL tools?
- If NOT, the GHL audit sub-agent cannot call GHL tools — this is a Phase 0 blocker.

### C. PIV Loop Timing
The PIV Loop: Plan → Implement → Validate → Metabolize

For Phase 0 triage, this involves:
1. Chris writes task spec (Plan) — same session as /prime
2. Chris opens NEW session, runs /execute (Implement)
3. Chris opens ANOTHER new session, runs /validate (Validate)
4. /validate auto-calls /metabolize (Metabolize)

**Question**: How does /validate "auto-call" /metabolize? Does the /validate command file literally say "then run /metabolize" and Claude executes it in the same session? Or does it write a marker file? The mechanics of this need to be explicit.

### D. Slack Integration
The PRD specifies Slack notifications via `SLACK_WEBHOOK_URL`. The /validate command says "Send Slack notification" on PASS.

**Question**: In the Claude Code execution environment (a markdown-file-based agent system with no application code), HOW does the Slack webhook get called? Options:
- Claude Code makes an HTTP POST to the webhook URL (using bash or a Python one-liner)
- There's a separate Slack MCP server configured
- It's a manual step documented as "then post to Slack"

This mechanism is NOT specified anywhere in the PRD or plan. Identify this as a gap.

---

## REVIEW TASK 5: VAULT COMPLETENESS FOR PHASE 0

The Phase 0 GHL triage task has a context package of 3 vault files:
1. `revtry/vault/integrations/ghl.md`
2. `revtry/vault/compliance/exclusions.md`
3. `revtry/agents/pipeline-ops/config.md`

For the triage output to be useful, Pipeline Ops must:
- Know which contacts to prioritize → needs triage criteria (written post-audit)
- Know which contacts to exclude → needs exclusions.md ✅
- Know which GHL tools to call → needs ghl.md ✅

**Questions:**
1. Where are triage criteria written? PRD says "Chris + Dani review audit → define criteria → write to vault/integrations/ghl.md." Is there a specific section in ghl.md designated for triage criteria? If not, where exactly does the agent read the criteria from?
2. The Phase 0 triage fallback model (GHL-native priority using dateLastActivity, open opportunity, tags) — is this written in pipeline-ops/config.md or in ghl.md? Which file does the agent read to know the fallback logic?

---

## REVIEW TASK 6: WINDOWS/ENVIRONMENT COMPATIBILITY

The validation commands in the Phase 0 plan use bash syntax (loops, `wc -l`, etc.) intended to run on Windows 11 with bash shell. Verify each command:

```bash
# Task 2 validation
wc -l "e:/CAIO RevOps Claw/CLAUDE.md"
# Is wc -l available in Windows bash? Or does it need: (Get-Content "..." | Measure-Object -Line).Lines
```

```bash
# Task 3 validation
python -m py_compile "D:/Agent Swarm Orchestration/.../server.py" && echo "syntax OK"
# Valid ✅ — python is available
```

```bash
# Task 9 validation — loop syntax
for f in "path1" "path2"; do ls -la "$f" && echo "OK: $f" || echo "MISSING: $f"; done
# Is bash for-loop syntax valid in the Windows bash environment? Verify.
```

```bash
# Task 11 — no-placeholder check
grep -rl "TODO\|TBD\|placeholder\|{fill" "e:/CAIO RevOps Claw/revtry/vault/"
# grep -r with pipe in pattern — valid? What's the Windows bash behavior?
```

---

## REVIEW TASK 7: IDENTIFY MISSING FILES/GAPS

The PRD §10 file structure lists every file that must exist. Compare it against:
1. The Phase 0 plan tasks — is every file from §10 created by at least one task?
2. Any file referenced in agent configs, vault specs, or guardrails that ISN'T in the §10 tree

**Known potential gap**: PRD §10 lists `revtry/guardrails/escalation.md` but PRD §14 only specifies `escalation.md` briefly. Is there a full spec for this file?

**Check these specific files** — do they have content specs in the PRD?
- `revtry/agents/orchestrator/context_assembly.md`
- `revtry/vault/icp/target_companies.md`
- `revtry/guardrails/escalation.md`
- `revtry/vault/integrations/instantly.md`, `heyreach.md`, `apollo.md` (listed as Phase 1 stubs)

---

## REVIEW TASK 8: PHASE 0 VERIFICATION TABLE AUDIT

PRD §18 has 23 verification checks. For each check, verify:
- Is the check binary (pass/fail)?
- Is the check actually testable without manual interpretation?
- Is there a corresponding implementation step in the Phase 0 plan?

Specific checks to scrutinize:

| Check | Question |
|-------|----------|
| "Isolation verified — Pipeline Ops session shows NO access to playbook vault files" | How is this tested? Does someone manually check, or is there an automated assertion? |
| "Maker-checker verified — Session creating candidate ≠ session running /validate" | How is this verified? Is session_id in active.md sufficient proof? |
| "One-shot verified — Pipeline Ops produces triage output from single task spec, no mid-task clarification needed" | How is "no mid-task clarification" verified after the fact? |
| "Retry counter — Attempt #3 on same task_id triggers escalation, not a 4th run" | This requires deliberately triggering 3 failures. Is there a test procedure for this? |

---

## WHAT TO PRODUCE: REVIEW REPORT FORMAT

Structure your output as:

```
# RevTry Plan Review Report — Codex Assessment

## Executive Summary
[2-3 sentences: overall readiness, biggest risks, recommendation]

## BLOCKER Issues
[Items that WILL cause Phase 0 to fail if not resolved before execution]
### BLOCKER-1: [Title]
- **File**: [which file]
- **Issue**: [exact problem]
- **Impact**: [what fails]
- **Fix**: [exact change needed]

## MAJOR Issues
[Items that create significant ambiguity or rework risk]
### MAJOR-1: [Title]
[same format]

## MINOR Issues
[Small gaps that won't block execution but should be cleaned up]
### MINOR-1: [Title]
[same format]

## SUGGESTIONS
[Optional improvements that would strengthen the system]

## Cross-Reference Errors
[Exact mismatches found between documents]
| Source | Referenced | Actual | Impact |
|--------|-----------|--------|--------|

## Verification Table Audit
[For each of the 23 checks: TESTABLE | NEEDS CLARIFICATION | NOT TESTABLE]

## Overall Assessment
[READY TO EXECUTE | READY WITH MINOR FIXES | NEEDS REWORK BEFORE EXECUTION]
```

---

## KNOWN ISSUES — RESOLVED

All 7 pre-identified issues were resolved during planning before this handoff was sent. Codex should verify each fix is present in the referenced PRD sections.

| Issue | Status | Resolution |
|-------|--------|-----------|
| GHL manifest.json lists fewer tools than server.py | **RESOLVED** | PRD §0 already specifies: "treat live discovery as ONLY source of truth." Manifest inconsistency is a known acknowledged risk. |
| GHL MCP server may have 15 tools (not 14) | **RESOLVED — no change needed** | Confirmed: server.py TOOLS array (lines 493–685) has exactly **14 tools**. PRD §12.7 matches server.py exactly. The "15 tools" figure was a planning session counting error. §12.7 now notes: "14 tools confirmed via live server.py inspection." |
| How does `/validate` invoke `/metabolize`? | **RESOLVED — PRD clarified** | Native Claude Code slash command composition. validate.md IF PASS block says "Run /metabolize (invoke as slash command in this same session)." No external mechanism needed — Claude reads the instruction and invokes the command. PRD §11.3 validate.md updated. |
| Slack notification mechanism (HTTP call vs MCP) | **RESOLVED — PRD updated** | bash `curl` command added to validate.md IF PASS block with `$SLACK_WEBHOOK_URL` guard. Graceful degradation if env var not set. See PRD §11.3 validate.md. |
| session_id random4hex — how generated by LLM | **RESOLVED — PRD updated** | Generation instruction added to execute.md lock claim step: "select 4 characters at random from [0-9a-f] (e.g., a4f2, b9c3, 0d7e). For session uniqueness only — not security." See PRD §11.3 execute.md. |
| Sub-agent access to parent session's GHL MCP | **RESOLVED — confirmed + PRD updated** | Confirmed: Claude Code sub-agents spawned via the built-in Agent tool inherit the parent session's MCP server connections. All 14 GHL tools available to sub-agents. Write operations must still use separate top-level sessions per maker-checker policy. Note added to PRD §5 Architecture. |
| Windows bash compatibility of validation commands | **RESOLVED — no change needed** | Confirmed: environment uses Windows 11 + bash shell. `wc -l`, `grep -r`, bash for-loops, `python -m py_compile`, `ls -la` are all valid in Git Bash on Windows 11. Phase 0 plan validation commands require no changes. |

---

## FILE READING ORDER

To do this review efficiently, read in this order:

1. **This document** (you're reading it now)
2. `e:\Greenfield Coding Workflow\Project-RevTry\.claude\PRD.md` — master spec (~80KB)
3. `e:\Greenfield Coding Workflow\Project-RevTry\.agents\plans\phase-0-foundation-ghl-triage.md` — implementation plan
4. `e:\Greenfield Coding Workflow\Project-RevTry\CLAUDE.md` — agent guidance file
5. `E:\CAIO RevOps Claw\RevTry_PRD.md` — original source PRD v1.0 (for comparison and any content not carried forward)

**Optionally read for context:**
- `D:\Agent Swarm Orchestration\chiefaiofficer-alpha-swarm\mcp-servers\ghl-mcp\server.py` — GHL MCP server (verify tool list and dependencies)
- `E:\CAIO RevOps Claw\vault\icp\scoring_rules.md` — original scoring rules (verify migration accuracy)
- `E:\CAIO RevOps Claw\vault\product\product_context.md` — original product context (verify split migration plan)

---

## SUCCESS CRITERIA FOR THIS REVIEW

The review is complete when:
- [ ] Every BLOCKER issue has a specific fix written
- [ ] Cross-reference table is fully populated (all mismatches identified)
- [ ] The 7 "Known Issues to Validate" above have been confirmed resolved or escalated
- [ ] Verification Table Audit is complete for all 23 checks
- [ ] Overall Assessment verdict is rendered
- [ ] A revised/patched version of any BLOCKER-level task in the Phase 0 plan is provided

---

*This handoff document was generated during the RevTry planning session on 2026-03-06.*
*Planning artifacts are located in: `e:\Greenfield Coding Workflow\Project-RevTry\`*
*Execution will happen in: `e:\CAIO RevOps Claw\` (no files created there yet except legacy sources)*
