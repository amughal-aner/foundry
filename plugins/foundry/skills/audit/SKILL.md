---
name: audit
description: "Whole-repo or scoped audit: architect, security, product and code-review subagents in parallel, merged into docs/audit/. Use when doing a periodic health check; costly, asks first."
disable-model-invocation: true
argument-hint: "[scope-path]"
allowed-tools: Read Grep Glob Edit(docs/audit/**)
---

# Audit

Scope: $ARGUMENTS (empty means the whole repository).

## 0. Warn about cost first
Before reading anything, ask with AskUserQuestion: "An audit runs 4 specialist subagents in
parallel (two on Opus). Each reads a large part of `<scope>`, so the total token cost is several
times that of a normal review. Proceed?" Options: "Proceed (Recommended for a release or periodic
check)", "Narrow the scope" (ask for a path), "Cancel". Stop unless the user picks Proceed or
gives a narrower scope.

## 1. Gather context once (main thread)
- From CLAUDE.md and the README: purpose, users, stack, commands, conventions, Security notes.
- Glob the scope: the top-level layout, the main packages, entry points and test dirs. Pick 5-15
  key paths.
- Write **one shared context block** that every brief includes:
```
Project: <name> — <one-line purpose>; users: <...>; stack: <...>
Scope: <paths>   Key files: <list>
Conventions: <relevant CLAUDE.md lines>   Sensitivity: <PII/payments/auth/secrets or none>
Mode: whole-repo audit (no diff). Report at most 400 words.
```

## 2. Delegate: four specialists **in parallel**
Send all four Agent calls **in a single message**, each with the shared block plus its focus line.
Use the named `subagent_type`, **never forks**:

| subagent_type | Focus line |
|---|---|
| `foundry:architect` | Module boundaries, layering, coupling, oversized functions, failure modes; 2 options for the worst problem. |
| `foundry:security-auditor` | OWASP Top 10 across all entry points; authz consistency; secrets; deps. |
| `foundry:product-designer` | Every user-facing surface: errors, destructive actions, empty states, copy. |
| `foundry:code-reviewer` | Whole-repo mode: correctness hotspots, error handling, test gaps. |

Tell the user in one line that 4 specialists are running. **When all four reports have
arrived, continue with step 3.** If one fails, continue with the rest and list it under
Not checked.

## 3. Merge and prioritize
- Dedupe across reports: the same `file:line` or the same root cause becomes one finding. Keep the
  highest severity and tag every area that raised it, e.g. `(security, review)`.
- Rank: Critical, then Warning, then Suggestion. Within each, rank by blast radius (user data,
  money, availability), then by fix effort (cheap first).
- **Top priorities**: at most 5 items. Each has a one-line fix direction and a suggested
  `/foundry:plan-feature` prompt.

## 4. Write `docs/audit/<YYYY-MM-DD>.md`
```
# Audit <YYYY-MM-DD> — <scope>
## Summary            (≤5 lines: overall health, counts per severity)
## Top priorities     (≤5)
## Findings
### Security
### Architecture
### Product / UX
### Code quality
## Open questions
## Not checked
```
If that file already exists, append `-2`, `-3`, ... to the name.

## 5. Reply
In at most 12 lines: the path, the counts, and the top priorities.
