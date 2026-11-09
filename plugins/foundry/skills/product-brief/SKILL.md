---
name: product-brief
description: "Product/UX brief for a feature via the product-designer subagent: users, flows, edge and error states, acceptance criteria, copy. Use when scoping or reviewing a user-facing feature."
argument-hint: "[feature or surface]"
allowed-tools: Read Grep Glob Edit(docs/product/**)
---

# Product brief

Feature or surface: $ARGUMENTS (if empty, ask the user in one question).

## 1. Gather context (main thread)
- From CLAUDE.md and the README: the product, its users, and terminology.
- Find the surfaces involved: CLI parser and commands, routes, templates, user-facing messages.
  List the paths.
- If it's a new feature: the problem, who has it, and what success looks like. Ask the user for
  anything missing (at most 2 questions, one AskUserQuestion call).
- Slug: kebab-case feature name, at most 5 words.

## 2. Delegate to the product designer
Call the Agent tool with `subagent_type: "foundry:product-designer"`. It must be that named
specialist, **not a fork**. The prompt is this self-contained brief:

```
Goal: <review the existing surface | shape the new feature> — <feature>
Users and job to be done: <...>
Context: <product summary, terminology (from CLAUDE.md/README)>
Scope paths: <list of user-facing code>
Constraints: <platform, accessibility needs, deadlines>
Deliver: your standard report; include acceptance criteria as `AC:` findings.
```

If the report isn't back yet, say so in one line. **When it arrives, continue with step 3.**

## 3. Write `docs/product/<slug>-brief.md`

```
# Product brief: <feature>
Date: <YYYY-MM-DD> · Status: Draft

## Problem
## Users and jobs to be done
## Flows
1. <happy path, numbered steps>
<variants: first-time use, power user, failure>

## States
| State | What the user sees | Notes |
|---|---|---|
| Empty | | |
| Loading / slow | | |
| Error | | |
| Success | | |
| Destructive action | | confirmation / undo |

## Acceptance criteria
- Given <context>, when <action>, then <observable result>.

## UX copy
| Where | Current | Proposed |
|---|---|---|

## Findings
<the designer's findings, verbatim, ordered by severity>

## Open questions
```

Keep it under 120 lines. Every acceptance criterion must be testable.

## 4. Reply
In at most 10 lines: the path, the top 3 UX risks, and the open questions.
