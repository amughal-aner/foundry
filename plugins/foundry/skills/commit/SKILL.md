---
name: commit
description: "Run the project's verify skill, write a Conventional Commit message from the diff, and commit. Use when a change is ready to commit."
disable-model-invocation: true
argument-hint: "[optional message hint]"
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *) Bash(git diff *) PowerShell(git add *) PowerShell(git commit *) PowerShell(git status *) PowerShell(git diff *)
---

# Commit

Hint from the user: $ARGUMENTS

## 1. Check state
- `git status --short`. If there's nothing to commit, say so and stop.
- If nothing is staged, stage the modified tracked files with `git add -u`. List untracked
  files and ask which to include. Never stage `.env*`, keys, `secrets/`, or
  `.claude/settings.local.json`.

## 2. Verify
- If the project has a `verify` skill (`.claude/skills/verify/SKILL.md`), run it with the Skill
  tool (`verify`) and wait for its result.
- If any check fails: show the failures, **don't commit**, and offer to fix them. Docs-only or
  test-only changes may skip verify; say that you skipped it.
- If there's no verify skill, say so in one line and continue.

## 3. Write the message
Read `git diff --cached`. Write a Conventional Commit:

```
<type>(<optional scope>): <imperative summary, ≤72 chars, no period>

<body: why the change was made and anything a reviewer must know; wrap at 72>
```

- type ∈ feat, fix, docs, refactor, test, perf, build, ci, chore. Add a `!` and a
  `BREAKING CHANGE:` footer for breaking changes.
- Scope = the main package or directory touched, when that's obvious.
- Use the user's hint if given. Add any co-author or attribution lines the session requires.

## 4. Commit
- `git commit -m "<subject>" -m "<body>"`.
- Never use `--no-verify`, `--amend` or `push`. If a git hook fails, show its output and stop.
- Reply in 3 lines or fewer: the short hash, the subject, and the files changed.
