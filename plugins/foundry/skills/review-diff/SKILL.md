---
name: review-diff
description: "Review the current git diff with the code-reviewer subagent, plus security-auditor when auth, input, crypto, SQL or deps change. Use when asked to review changes before a commit or PR."
argument-hint: "[base-branch or commit range]"
allowed-tools: Read Grep Glob Bash(git status *) Bash(git diff *) Bash(git log *) PowerShell(git status *) PowerShell(git diff *) PowerShell(git log *)
---

# Review the current diff

Range: $ARGUMENTS. Empty means uncommitted changes. A branch name `B` means `git diff B...HEAD`.
`A..B` means that range.

## 1. Gather (main thread, read-only)
1. Run `git status --short` and `git diff --stat` (plus `git diff --cached --stat`, or the range form).
   If there's nothing to review, say so and stop.
2. List the changed files and skim the diff hunks (`git diff` / the range) so you can write a
   precise brief. Note the intent of the change if the user or recent commits (`git log -5
   --oneline`) state it.
3. **Security trigger.** Also run the security auditor if any changed path or hunk involves:
   auth/login/session/token/password/permission checks; request, CLI or file input parsing; crypto,
   hashing or random tokens; SQL or query building; dependency manifests or lockfiles
   (`pyproject.toml`, `requirements*.txt`, `uv.lock`, `package.json`, ...).

## 2. Delegate (in parallel when both run)
Send the Agent calls **in one message**. Each `subagent_type` names the specialist; **not a fork**.

`subagent_type: "foundry:code-reviewer"`, prompt:
```
Goal: review this change. Intent: <one line, or "unknown">.
Diff range: <exact git diff arguments>
Changed files: <list>
Project facts: <stack, test command, conventions from CLAUDE.md>
```

`subagent_type: "foundry:security-auditor"` (only if triggered), prompt:
```
Goal: security review of this change only. Trigger: <which rule fired>.
Diff range: <exact git diff arguments>   Changed files: <list>
Context: <what the code does; sensitivity from CLAUDE.md Security notes>
```

If the reports aren't back yet, say in one line which specialists are running. **When all have
arrived, continue with step 3.**

## 3. Reply (no files written)
Merge the reports into one, in the shared format:

```
## Summary
<≤3 lines: safe to merge? biggest risk>
## Findings
- [Critical|Warning|Suggestion] <title> — <file:line> — <why> — Fix: <...>
## Open questions
## Not checked
```

- Dedupe findings with the same `file:line` or root cause and keep the higher severity. Order by
  severity, then file.
- Tag security-auditor findings with `(security)`.
- Don't fix anything unless the user asks. Offer to fix the Critical findings.
