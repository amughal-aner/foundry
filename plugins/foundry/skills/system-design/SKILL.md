---
name: system-design
description: "Frame a design decision, get the architect subagent's analysis of 2+ options, and write an ADR to docs/adr/. Use when choosing an architecture or library, or how to restructure code."
argument-hint: "[decision to make]"
allowed-tools: Read Grep Glob Edit(docs/adr/**)
---

# System design → ADR

Decision to make: $ARGUMENTS (if empty, ask the user for it in one question).

## 1. Frame it (main thread)
- Restate the decision in one sentence, plus the forces behind it: what's driving the change, and
  the constraints (performance, team size, deadlines, compatibility, cost).
- Take the stack, commands and conventions from CLAUDE.md.
- Find the code in scope with Glob/Grep. List 3-10 paths that matter.
- If a constraint that would change the answer is unknown, ask the user before delegating
  (one question at most).

## 2. Delegate to the architect
Call the Agent tool with `subagent_type: "foundry:architect"`. It must be that named specialist,
**not a fork**. The prompt is this self-contained brief (the subagent sees nothing else):

```
Goal: <the decision, one sentence>
Context: <what the system does, who uses it, stack (from CLAUDE.md)>
Scope paths: <list>
Constraints: <list>
Project conventions: <relevant CLAUDE.md lines>
Deliver: your standard report, with at least 2 options as `[Suggestion] Option X` findings;
mark the recommended one.
```

The architect may run in the background. If its report isn't back yet, tell the user in one
line that it's running. **When the report arrives, continue with step 3.**

## 3. Write the ADR
- Number: Glob `docs/adr/*.md`, take the highest `NNNN-` prefix + 1 (start at `0001`). Slug =
  kebab-case title, at most 6 words.
- Write `docs/adr/NNNN-<slug>.md`:

```
# NNNN. <Title>

- Status: Proposed
- Date: <today, YYYY-MM-DD>

## Context
<forces and constraints; cite file:line findings from the report that motivate the decision>

## Decision
<the recommended option, stated as "We will ...">

## Alternatives considered
- <Option>: <trade-offs; why not chosen>

## Consequences
- Positive: ...
- Negative / risks: ...
- Follow-ups: <concrete next steps; offer /foundry:plan-feature for larger ones>
```

- Keep it under 80 lines. Carry the architect's Open questions into Consequences as follow-ups.

## 4. Reply
In at most 10 lines: the ADR path, the decision, the top 2 risks, and the open questions that need
the user. Don't paste the whole ADR.
