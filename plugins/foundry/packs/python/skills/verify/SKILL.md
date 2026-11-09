---
name: verify
description: Run this project's format, lint, type and test checks and report only failures. Use before committing or when asked to verify a change.
allowed-tools: {{allowed_tools}}
---

# Verify

Run these from the project root, in this order. Run all four even if an earlier one fails:

1. Format: `{{format_check}}`
2. Lint: `{{lint}}`
3. Types: `{{typecheck}}`
4. Tests: `{{test}}`

Report in at most 30 lines:

- All pass: reply with the single line `verify: all checks passed`.
- Otherwise group failures by tool (`## format`, `## lint`, `## types`, `## tests`), showing
  `file:line` and the message. For tests, show the failing test ids and the shortest useful error.
  Leave out passing tools and progress noise. If a tool has more than 8 failures, show 8 and
  say how many more.

Don't fix anything unless the user asks. If a command itself fails to run (missing tool or
env), say so as its own line and continue with the rest.
