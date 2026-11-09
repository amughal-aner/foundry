---
name: plan-feature
description: "Interview, read the code, and write an ordered implementation plan with a verify step per step to docs/plans/. Use when a change touches more than 2 files or needs agreement first."
disable-model-invocation: true
argument-hint: "[feature or change]"
allowed-tools: Read Grep Glob Edit(docs/plans/**)
---

# Plan a feature

Request: $ARGUMENTS

Don't change any code in this skill. The only file it writes is the plan.

## 1. Interview (one AskUserQuestion call, at most 4 questions)
Ask only what the request and CLAUDE.md don't already answer. Prefill the options:
1. **Outcome**: what the user or system can do afterwards (the definition of done).
2. **Constraints**: compatibility, performance, deadlines, things that must not change.
3. **Scope**: what's explicitly out of scope for this change.
4. **Risk tolerance**: one PR vs incremental steps behind a flag.

## 2. Read the code via Explore
Call the Agent tool with `subagent_type: "Explore"` (the built-in read-only explorer; not a fork)
and this brief:

```
Find everything needed to implement: <request + outcome>.
Report: the files and functions to change (file:line), existing patterns to follow, tests that
cover this area, and the commands to run them (from CLAUDE.md). Breadth: medium. ≤300 words.
```

If it's still running, say so in one line. **When the report arrives, continue with step 3.**
Read the 2-5 most important files yourself to confirm.

## 3. Write `docs/plans/<slug>.md`
Slug: kebab-case, at most 5 words. If the file exists, add `-2`.

```
# Plan: <title>
Date: <YYYY-MM-DD> · Status: Proposed

## Goal
<outcome / definition of done>

## Context
<relevant files (file:line) and patterns found>

## Steps
1. <change> — files: <paths>
   - Verify: <exact command or test, e.g. `uv run pytest -q tests/test_x.py::test_y`>
2. ...
<Start with a failing test where a bug or behavior is involved. Each step leaves the build
green. At most 10 steps; split bigger work into phases.>

## Risks
- <risk> — mitigation: <...>

## Out of scope
## Open questions
```

## 4. Stop for approval
Reply in at most 10 lines: the plan path, the step titles, and the open questions. Then **stop**:
don't start implementing until the user approves (e.g. "go", or "go with step 1").
