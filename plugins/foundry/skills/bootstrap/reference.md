# Bootstrap reference

## Answers file: `<target>/.claude/foundry.json`

```json
{
  "name": "billing-api",
  "summary": "One paragraph: what it is, who uses it, the stack.",
  "pack": "python",
  "commands": {
    "install": "uv sync",
    "test": "uv run pytest -q",
    "test_one": "uv run pytest -q path/to/test_file.py::test_name",
    "lint": "uv run ruff check .",
    "format": "uv run ruff format .",
    "format_check": "uv run ruff format --check .",
    "typecheck": "uv run pyright"
  },
  "conventions": ["Only conventions that differ from language defaults"],
  "gotchas": ["Things Claude can't infer: flaky test X, service Y must be running, ..."],
  "sensitive": ["PII", "auth"],
  "security_notes": ["Optional extra project-specific security bullets"]
}
```

- `name` and `summary` are required. `pack` is a pack name from `detect_stack` or `null`.
- With a pack, any missing command key falls back to the pack default. `format_check` is the
  non-mutating form used by `/verify` (for ruff: `ruff format --check .`; for black: `black --check .`).
- `sensitive` empty or absent: no "Security notes" section. Otherwise the section lists the
  categories, `security_notes`, and two standard bullets.
- Keep `conventions` and `gotchas` short: the rendered CLAUDE.md must stay at or under 80 lines.
  Prefer zero bullets to filler.

## Interview (one AskUserQuestion call, max 4 questions)

Prefill every option from the inventory. Put the recommended option first, with "(Recommended)".

1. **Purpose** (header "Purpose"): "In one line, what is <name> and who uses it?". Options: a
   summary drafted from the README; "Internal tool"; "Library". "Other" lets them type it.
2. **Commands** (header "Commands"): "Use these commands for install/test/lint/format/types?".
   Option 1, "Use detected (Recommended)", with a `preview` listing every command. Option 2, "I'll
   edit them", then ask for the corrections in a follow-up message.
3. **Conventions and gotchas** (header "Gotchas", multiSelect): offer 2-3 candidates found while
   reading (e.g. "Tests need a running Postgres", "Generated files in src/gen/ must not be
   edited"), plus "None". The user can add more via "Other".
4. **Sensitivity** (header "Sensitive", multiSelect): "PII", "Payments", "Auth or secrets",
   "None" (4 options is the maximum). Map the answer to `sensitive`: "None" means `[]`.

## Commands override rules (`detect_stack.py`)

| Signal | Runner / tool |
|---|---|
| `uv.lock` or `[tool.uv]`, or a plain `pyproject.toml` | uv (`uv sync`, `uv run …`) |
| `poetry.lock` or `[tool.poetry]` | poetry (`poetry install`, `poetry run …`) |
| `[tool.hatch]` or `hatch.toml` | hatch (`hatch env create`, `hatch run …`) |
| only `requirements*.txt` / `setup.py` / `setup.cfg` | pip (`python -m pip install -r …`, `python -m …`) |
| `[tool.mypy]`, `mypy.ini`, `.mypy.ini` | `mypy .` instead of `pyright` |
| `[tool.black]` without `[tool.ruff]` | `black .` / `black --check .` for format |
| `.flake8` or `[tool.flake8]` | `flake8 .` for lint |
| `tox.ini` | note only (commands still run a single env) |

## Files written (`apply_bootstrap.py`)

| File | Source | Action rules |
|---|---|---|
| `CLAUDE.md` | `templates/CLAUDE.md.tmpl` + pack `claude-md.fragment.md` | create / update (approval) |
| `.claude/settings.json` | `templates/settings.base.json` + pack `settings.json` + marketplace keys | create / merge (additive) |
| `.claude/rules/*.md` | pack `rules/` | create / update (approval) |
| `.claude/hooks/ruff_on_edit.py`, `.claude/hooks/py` | pack `hooks/` + plugin launcher | create / update (approval); chmod 755 off Windows |
| `.claude/skills/verify/SKILL.md` | pack `skills/verify/SKILL.md` with commands | create / update (approval) |
| `docs/plans/.gitkeep`, `docs/adr/.gitkeep` | empty | create |
| `.gitignore` | `CLAUDE.local.md`, `.claude/settings.local.json` | create / append missing lines |

Settings merge (`merge_settings.py`): lists are unioned, hooks are de-duplicated by
type + command + args, existing keys are never removed, and scalar conflicts keep the existing value
and are reported. Permission `allow` rules for the detected runner are added (Bash and PowerShell
forms). Rules for `uv` are dropped when the project doesn't use uv.

Marketplace: when `foundry.config.json` has `marketplace_source`, the merge also adds
`extraKnownMarketplaces.<name>.source` and `enabledPlugins["foundry@<name>"]: true`, so cloning a
bootstrapped repo prompts teammates to install foundry.

## Why the verify skill is a project skill

Claude Code only adds its "run verify before committing" instruction for a model-invocable skill
named `verify` that loads from the project, personal or additional-directory location, never from
a plugin. A project `verify` skill also replaces the bundled `/verify` (app launch) in that repo,
which is why the dry run prints a note about it.
