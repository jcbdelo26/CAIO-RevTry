# /plan-task — Task Decomposition

Given a goal (from argument or recent conversation):

## Complexity Gate

Before beginning, classify the task:

**ROUTINE** (skip contract): warm pipeline runs, known bug fixes, configuration changes, operations you've done before in this project, small isolated changes with clear scope.

**NOVEL** (trigger contract): new features, unfamiliar integrations, cross-cutting changes, unclear requirements, tasks where the "right approach" is not obvious, tasks that could destabilize existing behavior.

If ROUTINE → proceed directly to planning.
If NOVEL → complete the Prompt Contract flow below before planning.

## Prompt Contract Flow (NOVEL tasks only)

### Step 1: Reverse Prompting
Generate clarifying questions specific to THIS task's implicit assumptions, decision points, and failure modes. Do NOT use a fixed list of questions. Target ambiguities that, if unresolved, would produce a wrong plan. Ask them. Wait for answers before proceeding.

### Step 2: Prompt Contract
Once clarifications are resolved, formalize into this contract before writing the plan:

**Goal:** [What we're building and why — the outcome, not the implementation]
**Constraints:** [Hard limits: forbidden approaches, safety rules, scope boundaries]
**Format:** [Output shape: file conventions, interfaces, expected structure]
**Failure:** [What failure looks like, how to detect it, rollback plan]

The plan must be consistent with all four contract sections.

STEP 1: If goal is ambiguous -> ask 3-5 clarifying questions (multiple choice preferred).
STEP 2: Identify which specialist agent handles this.
STEP 3: Apply INCLUSION TEST to vault files:
  For each candidate vault file ask: "If the agent doesn't have this, will it make a wrong decision?"
  YES = include. NO = exclude. MAXIMUM 5 files in context package.
STEP 4: Write task spec using the zero-ambiguity template (all 9 sections — see revtry/agents/orchestrator/task_spec_template.md), including normalized `Operation Intents`, `Notification Policy`, and `Required Phase Gates`.
  If the task includes any GHL contact write, the spec MUST also declare `contactWriteFieldAllowlist`, `tagMutationPolicy=add_only`, and `unsafeFieldTouchPolicy=block_and_escalate`.
STEP 5: Review: does any field allow the agent to infer or assume? Fix before saving.
STEP 6: Read revtry/guardrails/hard_blocks.md and lint the task spec's `Operation Intents` against prohibited operations.
  If a prohibited intent is present -> STOP. Do NOT save the spec. Escalate the blocked request to Chris.
STEP 7: Generate `taskId` in the format `TASK-YYYYMMDD-HHmmssfff-RAND4` and save to revtry/registry/tasks/TASK-[YYYYMMDD-HHmmssfff-RAND4].md
STEP 8: Do NOT claim an active lock here. `/execute` owns revtry/registry/active.md at run time.

SELF-VALIDATE before saving:
- [ ] All 9 task spec sections populated (no blanks, no "TBD")
- [ ] Goal statement is binary (testable yes/no)
- [ ] Context package <=5 vault files with inclusion rationale for each
- [ ] `Operation Intents` are normalized and complete for the requested work
- [ ] All validation criteria are binary pass/fail (no "approximately" or "seems correct")
- [ ] MAY/MAY NOT scope boundaries explicitly defined
- [ ] `Notification Policy` is one of: `required`, `best_effort`, `not_applicable`
- [ ] `Required Phase Gates` explicitly lists every prerequisite gate needed at execution time
- [ ] Any GHL contact write declares `contactWriteFieldAllowlist`, `tagMutationPolicy=add_only`, and `unsafeFieldTouchPolicy=block_and_escalate`
- [ ] Failure protocol includes max 3 retry rule
- [ ] Output schema is exact JSON with field types
- [ ] Hard-block lint passed before saving the task spec

FEEDBACK LOOP: After task completes, /metabolize updates this command if spec patterns cause recurring failures.
