# /metabolize — Outcome Processing

Auto-called by /validate on PASS. Call manually after failure diagnosis.

PERMISSION SCOPE: /metabolize writes to vault/feedback/ files on PASS. For `task_type = capability_audit`, PASS additionally allows writes to `revtry/vault/integrations/ghl.md` only. When invoked by /validate (Quality Guard session), it inherits Orchestrator-level write access for those paths only. On FAIL diagnosis, /metabolize may additionally update any vault file, agent config, or skill file as a system-evolution action — this elevated write scope is logged in memory/learnings.md with the specific file changed and rationale. Quality Guard cannot write to vault/ outside of /metabolize execution.

READ: revtry/registry/tasks/[task-id].md + validation verdict

IF PASS:
1. Identify what made this successful (which vault files most useful?)
2. Log to vault/feedback/agent_learnings.md:
   {taskId, agent, pattern, whatWorked, vaultFilesUsed, date}
3. If outreach task -> update vault/feedback/campaign_performance.md
4. If `task_type = capability_audit` -> update `revtry/vault/integrations/ghl.md` with:
   - verified existing tools
   - required Phase 0A tools and any remaining gaps
   - parameter support and pagination notes
   - the named `Phase 0 Triage Criteria` section as `Status: DRAFT` unless explicit human approval metadata is already present
5. Update revtry/memory/operations_log.md
6. Registry transitions happen in /validate, not here

IF FAIL:
Diagnose root cause using this hierarchy:
  a. Vault file wrong/outdated? -> update vault file + log change
  b. Task spec ambiguous? -> update task spec template
  c. Agent went out of scope? -> update agent config.md
  d. Context package too broad? -> narrow inclusion criteria
  e. Skill definition incomplete? -> update the skill file
Log to revtry/registry/failures.md:
  {taskId, attemptNumber, failureReason, rootCauseCategory, fixApplied, date}
After 3rd attempt on same task -> write to revtry/registry/escalations.md

SYSTEM EVOLUTION RULE: If the same root cause category appears in 3 different tasks ->
  update the relevant system file (vault, agent config, or skill) + log in memory/learnings.md

GUARD-004 FEEDBACK (if FEEDBACK_LOOP_POLICY_ENABLED=true):
If rejection_note contains an opener pattern matching >=2 rejections -> add to banned openers in vault/playbook/signatures.md

SELF-VALIDATE: `rootCause` identified (not "unknown"). Fix logged with specific action taken.

## Candidate Rule Generation

After processing each task outcome, evaluate whether a reusable rule can be extracted.

**Format for candidates:**
```
CANDIDATE Rule N — Category: [Never/Always/Prefer] [do X] because [Y] (from Task-[ID])
```

**Categories:**
- Never: hard avoid (caused failures, bugs, or rework)
- Always: reliably worked and should be repeated
- Prefer: worked well in context, use as default unless reason not to

**Rules:**
1. Write candidates to `revtry/memory/candidate_rules.md` — NEVER write directly to `revtry/memory/learnings.md`
2. A candidate becomes a learning only when the human explicitly promotes it
3. Maximum 50 active candidates. When the file exceeds 50, consolidate by merging redundant candidates before adding new ones
4. Every 20 promotions, review `learnings.md` for contradictions and consolidate

**What makes a good candidate:**
- Specific enough to apply to a real future decision (not "be careful" or "think first")
- Grounded in something that actually happened (reference the Task-ID)
- Falsifiable: you could imagine a situation where it wouldn't apply

**What NOT to add:**
- Obvious best practices already in CLAUDE.md or vault
- Vague observations without a clear action
- Rules that contradict existing learnings without flagging the conflict
