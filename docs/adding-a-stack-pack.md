# Adding a stack pack

A stack pack teaches `/foundry:bootstrap` how to configure one kind of project: how to detect it,
which commands to put in `CLAUDE.md` and `/verify`, which permissions to allow, which path-scoped
rules to install, and which format-on-edit hook to run. v1 ships `packs/python`. Adding a stack
(TypeScript as the running example) is a copy-and-edit job, plus two small code touches if the
stack's commands vary per project.

Packs cost **no always-on tokens**: they're data files that bootstrap reads, not skills or agents.

## 1. Copy the Python pack

```
cp -r plugins/foundry/packs/python plugins/foundry/packs/typescript
rm -rf plugins/foundry/packs/typescript/hooks/__pycache__
```

Bootstrap discovers every `packs/*/pack.json`. Packs are tried in **alphabetical order of their
directory name** and the first one with a matching `detect` file wins, so make detect lists specific
(a Python repo may also have a `package.json` for docs tooling).

## 2. Edit `pack.json`

```json
{
  "name": "typescript",
  "detect": ["tsconfig.json", "pnpm-lock.yaml", "package-lock.json"],
  "defaults": {
    "install": "pnpm install",
    "test": "pnpm test",
    "test_one": "pnpm vitest run path/to/file.test.ts -t \"name\"",
    "lint": "pnpm eslint .",
    "format": "pnpm prettier --write .",
    "format_check": "pnpm prettier --check .",
    "typecheck": "pnpm tsc --noEmit"
  },
  "detect_overrides": "npm/yarn/bun projects use their own runner."
}
```

- `name` must equal the directory name.
- Keep all seven command keys. `/verify` runs `format_check`, `lint`, `typecheck` and `test`
  (never `format`, because verify must not modify files). The interview lets the user correct them.

## 3. Edit the rules (`rules/*.md`)

Replace `python.md` / `testing.md` with stack rules. Each file:

- starts with frontmatter whose only field is `paths` (e.g. `paths: ["**/*.ts", "**/*.tsx"]`)
- is ≤ 25 lines and lists only what differs from the language's defaults

They load only when Claude touches a matching file, so they're cheap; keep them short anyway.
Update the line limits in `tests/test_plugin_constraints.py` (it parametrizes over the Python rule
file names).

## 4. Edit the settings fragment (`settings.json`)

This is merged into the project's `.claude/settings.json` (lists unioned, hooks de-duplicated,
existing keys kept).

- `permissions.allow`: the runner commands, **each with a `PowerShell(...)` twin** of every
  `Bash(...)` rule (Windows teammates; decision C-1). Bootstrap also adds rules derived from the
  confirmed commands, so this list is the floor, not the whole set.
- `permissions.deny`: keep the `.env` / secrets / force-push / `rm -rf` rules. The base template
  (`templates/settings.base.json`) adds the always-on guards; don't duplicate it.
- `hooks.PostToolUse`: point the command at your hook file via the launcher, exactly as the Python
  fragment does: `sh "${CLAUDE_PROJECT_DIR}/.claude/hooks/py" "${CLAUDE_PROJECT_DIR}/.claude/hooks/<hook>.py"`.
  Keep `"onFailure": "continue"` and a timeout ≤ 30 s.

## 5. Replace the format hook (`hooks/`)

Every file in the pack's `hooks/` directory is copied into the project's `.claude/hooks/`, and the
`py` launcher is copied alongside. Rename `ruff_on_edit.py` (e.g. `prettier_on_edit.py`) and keep
its contract:

- stdlib-only Python ≥ 3.9; read the PostToolUse JSON from stdin
- act only on the stack's file extensions; run fix, then format
- report remaining problems with one JSON object on stdout:
  `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<summary>"}}`,
  capped at about 10 issues as `ruff_on_edit.py` does (`MAX_LINES`)
- **never block**: exit 0 always, including when the tool (`pnpm`, `prettier`) is missing

Copy `tests/test_ruff_on_edit.py` to cover it: ignored file types, an empty `PATH` (tool missing),
and a real fix-then-report run.

## 6. Edit the CLAUDE.md fragment and the verify template

- `claude-md.fragment.md`: the `## Commands` section, using the placeholders `{{install}}`,
  `{{test}}`, `{{test_one}}`, `{{lint}}`, `{{format}}`, `{{typecheck}}`. Keep it to the command
  list; the rendered `CLAUDE.md` must stay ≤ 80 lines.
- `skills/verify/SKILL.md`: usually only the wording changes. Keep `name: verify`, keep
  `allowed-tools: {{allowed_tools}}`, and **don't** add `disable-model-invocation` (it would turn off
  Claude Code's verify-before-commit behavior).

## 7. Code touches (only if needed)

Two places in the bootstrap scripts know about Python specifically:

- `skills/bootstrap/scripts/detect_stack.py` → `OVERRIDES`: register a function when commands depend
  on what the repo uses (npm vs pnpm vs yarn, jest vs vitest). Without one, `defaults` are used as-is.
- `skills/bootstrap/scripts/apply_bootstrap.py` → `RUNNERS`, `KNOWN_TOOLS`, `SAFE_INSTALL_PREFIXES`:
  how a command is cut into a permission prefix (`uv run pytest` → `Bash(uv run pytest *)`). Add
  `("pnpm", "exec")`, `("npx", ...)`, `"pnpm install"` and similar so the derived allow rules are
  tight rather than two-word prefixes.

## 8. Add a detect test

In `tests/test_detect_stack.py`, add at least:

- a repo with the stack's marker files → `pack == "typescript"` and the expected commands
- each override branch (e.g. `yarn.lock` → yarn commands)
- a Python-only repo still detects `python` (pack ordering didn't steal it)

Then run the whole suite: `uv run pytest`.

## 9. Validate, pilot and evaluate

```
uv run pytest
claude plugin validate ./plugins/foundry && claude plugin validate .
```

- **Pilot:** in a throwaway copy of a real project of that stack, run
  `claude --plugin-dir <repo>/plugins/foundry`, then `/foundry:bootstrap`. Check that `CLAUDE.md` is
  ≤ 80 lines, settings merged, an edit gets formatted, `/verify` runs the checks, and a second
  bootstrap run changes nothing.
- **Evals:** the specialist suite in `plugins/foundry/evals/` is generated by `evals/build_suite.py`
  from the Python fixture. For a new stack, add a small fixture under `fixtures/` with seeded issues,
  an answer key under `evals/answer-keys/` (never inside the fixture), and cases in `build_suite.py`.
  Run one case first and check its cost before running the rest (`--max-cost-usd`).
- Log any choice that deviates from the Python pack in `docs/decisions.md`, and add a
  `CHANGELOG.md` entry.
