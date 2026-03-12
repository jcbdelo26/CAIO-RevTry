# /validate — Manual Validation

USAGE: /validate [output-path] [task-spec-path]

This command MUST run in a DIFFERENT fresh session from the one that created the candidate output.

---

**CRITICAL RULE:** You must evaluate this output with zero knowledge of HOW it was produced. Judge ONLY what was produced against the gate criteria. Do NOT ask about or consider the maker's reasoning, approach, or implementation strategy. The process is irrelevant — only the output quality matters.

---

0. Verify both provided file paths exist. If either is missing, report the exact missing path and STOP.
1. Read task spec validation criteria from [task-spec-path]
2. Read candidate output from [output-path]
3. Read `active.md` or `completed.md` record for the task and generate `validatorSessionId` in PowerShell:

```powershell
$suffix = -join ((65..90) + (97..122) | Get-Random -Count 4 | % {[char]$_})
$validatorSessionId = "{0}-{1}-{2}" -f "quality-guard", (Get-Date -Format 'yyyyMMdd-HHmmssfff'), $suffix
```

4. Compare `validatorSessionId` to `makerSessionId`. If they match, FAIL immediately. Maker-checker is policy-enforced with recorded evidence.
5. For each gate, load the gate file PLUS any vault files explicitly referenced inside that gate
6. Run Gate 1 (revtry/guardrails/gate1_structural.md)
7. If Gate 1 PASS -> run Gate 2 (revtry/guardrails/gate2_compliance.md)
8. If Gate 2 PASS -> run Gate 3 (revtry/guardrails/gate3_alignment.md)
9. Before rendering any pass/fail verdict, produce an **evidence packet** for each item validated:

```
- CRM facts referenced: which specific contact/conversation data points appear in the output
- Playbook angle used: which vault strategy/angle does the output reflect (if applicable)
- Conversation triggers matched: which signals from the conversation thread drove this output
- Missing evidence: any claims in the output not supported by the available facts
```

An output that "sounds right" but has no CRM facts referenced or conversation triggers matched MUST FAIL even if it reads well. Fill out the evidence packet fully before proceeding to verdict.

10. Output verdict:

{
  "verdict": "PASS|FAIL",
  "gateResults": {"gate1": "PASS|FAIL", "gate2": "PASS|FAIL", "gate3": "PASS|FAIL"},
  "failureReason": "string|null",
  "violations": ["specific violation 1"],
  "recommendation": "PROCEED|RERUN|ESCALATE",
  "notificationStatus": "SENT|SKIPPED_OPTIONAL|FAILED|NOT_APPLICABLE"
}

IF PASS:
- Resolve notification handling from the task spec's `Notification Policy`:
  - `not_applicable` -> final `notificationStatus = NOT_APPLICABLE`
  - `best_effort` + missing `SLACK_WEBHOOK_URL` -> final `notificationStatus = SKIPPED_OPTIONAL`
  - `required` + missing `SLACK_WEBHOOK_URL` -> FAIL validation
- If policy requires or permits a webhook send and `SLACK_WEBHOOK_URL` is set, attempt Slack delivery with retry (3 attempts, exponential backoff: 1s, 3s, 9s) using PowerShell:
  ```powershell
  if ($env:SLACK_WEBHOOK_URL) {
    $body = @{
      taskId = "[TASK-ID]"
      agent = "[agent]"
      summary = @{ count = 0; top_3 = @() }
      timestamp = (Get-Date).ToString("o")
      outputPath = "revtry/outputs/[TASK-ID]_output.md"
    } | ConvertTo-Json -Depth 5
    Invoke-RestMethod -Method Post -Uri $env:SLACK_WEBHOOK_URL -ContentType 'application/json' -Body $body | Out-Null
  }
  ```
  For triage tasks, build the JSON body from the validated candidate payload already loaded in memory so it includes `count` and `top3` without depending on a not-yet-promoted file.
- Finalize `notificationStatus` after the send attempt (after all retries exhausted):
  - successful send -> `SENT`
  - any send failure + `required` -> FAIL validation
  - any send failure + `best_effort` -> `FAILED` (task may still PASS)
- Promote candidate file: COPY `_candidate.md` to `revtry/outputs/[TASK-ID]_output.md` (do NOT rename). Delete `_candidate.md` only AFTER `completed.md` is updated successfully.
- Update `revtry/registry/active.md` -> move task to `revtry/registry/completed.md`, recording `makerSessionId`, `validatorSessionId`, `notificationPolicy`, and final `notificationStatus`
- Delete `revtry/registry/locks/[TASK-ID].lock` after the completed row is written successfully.
- Do NOT update vault capability docs directly in `/validate`
- Run /metabolize (invoke as a slash command in this same session)

IF FAIL:
- Do NOT patch the candidate output manually
- Log to `revtry/registry/failures.md`: `attemptNumber` + `gateFailed` + `specificReason` + `rootCauseHypothesis`
- Update active.md status to FAILED_VALIDATION
- Delete `revtry/registry/locks/[TASK-ID].lock` so a later corrected attempt can claim a fresh lock

SELF-VALIDATE:
- All applicable gates ran in sequence
- All gate dependency files referenced by the guardrails were loaded
- `makerSessionId` and `validatorSessionId` are both recorded and are different
- `notificationStatus` is recorded and matches the task spec policy
- `notificationPolicy` is preserved in `completed.md`
- Violations are specific (not generic "failed")
