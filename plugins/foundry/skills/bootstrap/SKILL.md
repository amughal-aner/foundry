---
name: bootstrap
description: "Set up a repo for Claude Code: CLAUDE.md, permissions, path-scoped rules, a format hook and a verify skill. Use when starting Claude Code in a new or unconfigured repository."
disable-model-invocation: true
argument-hint: "[project-path]"
allowed-tools: Read Glob Grep Bash(git status *) Bash(git rev-parse *) PowerShell(git status *) PowerShell(git rev-parse *) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*) Bash(python ${CLAUDE_SKILL_DIR}/scripts/*) PowerShell(python ${CLAUDE_SKILL_DIR}/scripts/*)
---

# Bootstrap a project for Claude Code

Turn the target repository into a configured Claude Code project. Never overwrite a file the user
hasn't approved. All writes go through `apply_bootstrap.py`, which is idempotent.

**Running the scripts.** Use `python3` on macOS/Linux and `python` on Windows (PowerShell or Git
Bash), exactly as written below. Don't quote the script path unless it contains spaces.
- Inventory: `python3 ${CLAUDE_SKILL_DIR}/scripts/detect_stack.py <target>`
- Plan: `python3 ${CLAUDE_SKILL_DIR}/scripts/apply_bootstrap.py --target <target> --dry-run`
- Apply: `python3 ${CLAUDE_SKILL_DIR}/scripts/apply_bootstrap.py --target <target> [--approve <rel-path> ...]`

For the answers schema, interview wording and the file-by-file spec, read
[reference.md](reference.md) before step 2.

## 1. Inventory (read-only)

1. Target dir = `$ARGUMENTS` if given, else the current directory. Confirm it's a git repo with
   `git rev-parse --show-toplevel`. If it isn't, say so, but continue.
2. Run `detect_stack.py <target>` and keep its JSON (`pack`, `commands`, `tool_hints`, `notes`,
   `existing`).
3. Read the README (`existing.readme`), any existing `CLAUDE.md`, `.claude/settings.json`,
   `.claude/rules/*` and `.claude/foundry.json` (answers from an earlier bootstrap run).
4. If `pack` is null, tell the user no stack pack matched. Continue with a generic CLAUDE.md and the
   guard settings only (no rules, hook or verify skill).

## 2. Interview

Ask **one** AskUserQuestion call with **at most 4 questions**, each prefilled from the inventory
(and from `.claude/foundry.json` if it exists). See reference.md §Interview for the exact questions:

1. Purpose and users (one line)
2. Confirm the detected commands. Show them in an option preview.
3. Conventions and gotchas that Claude can't infer from the code
4. Sensitivity: PII, payments, auth or secrets, none (multi-select)

Fold anything useful from an existing CLAUDE.md into conventions and gotchas, so nothing is lost.

## 3. Propose (no project files written yet)

1. Write the answers to `<target>/.claude/foundry.json` (schema in reference.md). It's the only
   file written before approval: the plan is computed from it, and re-runs reuse it.
2. Run `apply_bootstrap.py --target <target> --dry-run`.
3. Show the user the full plan: every file with its action (`create`, `merge`, `append`,
   `update`, `unchanged`) and every diff, exactly as printed. Relay each `Notes:` line, including the
   note that a project `verify` skill replaces the bundled `/verify` in this repo.
4. For every `update` (an existing file that differs), ask whether to overwrite it. Default is no.
5. **Stop and wait for approval.** If the user wants changes, edit `.claude/foundry.json` and
   rerun the dry run. Don't hand-edit the planned files.

## 4. Write

Run `apply_bootstrap.py --target <target>`, adding `--approve <rel-path>` for each approved
overwrite. It writes:

- `CLAUDE.md` rendered from the template (the script refuses anything over 80 lines)
- `.claude/settings.json`: an additive merge of guard denies, pack permissions, the format
  hook and (if configured) the team marketplace
- `.claude/rules/*.md`, `.claude/hooks/ruff_on_edit.py`, `.claude/hooks/py` (from the pack)
- `.claude/skills/verify/SKILL.md` with the confirmed commands substituted
- `docs/plans/.gitkeep`, `docs/adr/.gitkeep`
- `.gitignore` additions: `CLAUDE.local.md`, `.claude/settings.local.json`

If the script exits non-zero, show its message, fix the answers file and rerun the dry run.

## 5. Report

List what was written, skipped or unchanged, in at most 15 lines. Then give the next steps:

1. Run `/verify` once to check that the commands work.
2. Review `CLAUDE.md` and trim anything Claude could infer from the code.
3. Commit `.claude/` and `CLAUDE.md`. `.claude/settings.local.json` stays personal.

Running `/foundry:bootstrap` again on the same answers should report everything `unchanged`.
