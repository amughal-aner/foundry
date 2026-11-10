# Foundry: build plan

> **Audience:** Claude Code, building this on the user's machine.
> **What we're building:** a private, team-shared Claude Code **plugin marketplace** called `foundry`. It does two things:
> - bootstraps any new repository into a configured Claude Code project
> - provides on-demand specialists for system design, security, product/UX and code review
>
> v1 ships one stack pack: **Python** (uv + ruff + pytest + pyright).
> **Minimum Claude Code version:** v2.1.286.
> **Plan date:** 2026-11-09.

---

## 0. How to execute this plan (read first)

1. **Read the whole plan before starting.** Work through the phases in order (0 → 4).
2. **Track each phase with a task list.** At the start of each phase, create one from that phase's checklist and tick items off as you finish them.
3. **Stop at every Gate.** Each phase ends with one. At a Gate you:
   - run the listed checks
   - make a git commit (`feat(phaseN): ...`)
   - give a summary of 10 lines or fewer
   - **STOP and wait for the user to say "continue".**

   The one exception is Phase 0: continue straight into Phase 1 unless you found discrepancies.
4. **Never guess a config format.** Steps marked **(verify)** require you to confirm the exact schema in the official docs first, using WebFetch on `https://code.claude.com/docs/en/<page>.md` or the `claude-code-guide` subagent. If the docs differ from this plan:
   - follow the docs
   - log the difference in `docs/decisions.md`
   - mention it at the next Gate
5. **Treat every always-loaded line as a recurring cost.** It's paid by every teammate on every turn. Keep descriptions, CLAUDE.md templates and agent prompts tight.
6. **Stay inside the repo.** The repo root is the directory containing this `plan.md`. You may *read* `~/.claude/` to check for name clashes. Don't:
   - install the plugin user-wide
   - push to any remote
   - install system packages

   without asking the user first.
7. **Prefer scripts for deterministic work.** Merging JSON, detecting stacks and running evals should be small Python scripts (stdlib only) with tests, not LLM edits.

---

## 1. Goals and non-goals

**Goals**
- `/foundry:bootstrap` turns any repo into a configured Claude Code project: CLAUDE.md, permissions, path-scoped rules, a format hook and a `verify` skill.
- Specialists for **architecture, security, product/UX and code review** that load only when used.
- Guardrails enforced by **hooks and permission rules**, not by prose.
- **Measured, not assumed:**
  - every specialist skill is evaluated against a no-plugin baseline
  - the always-on token overhead is measured

**Non-goals for v1**
- Other coding agents (Codex, Cursor, …)
- Stacks other than Python. The pack format must still make adding one a copy-and-edit job.
- MCP servers
- CI, unless the user opts in at Phase 4

---

## 2. Design principles (hard constraints)

These come from checking the official docs. Don't violate them without logging a decision.

1. **Always-on budget: ≤ 2,000 tokens added by the plugin per session.** Phase 3 measures this.
2. **Every skill/agent `description` is ≤ 200 characters.** It leads with what it does, then "Use when …". The description is the trigger.
3. **Side-effect skills set `disable-model-invocation: true`.** This applies to bootstrap, plan-feature, audit and commit. Their descriptions then cost no context until someone types the command.
4. **Specialist subagents are read-only.** They use `tools: Read, Grep, Glob`, plus `Bash` only where §5.1 says. Each returns a report of ≤ 400 words in the shared format (§5.2).
5. **Must-hold rules are hooks or permission `deny` rules.** CLAUDE.md is advice only.
6. **Project-specific config is written into the project by bootstrap.** It does not ship in the plugin. Two reasons:
   - a *plugin* skill named `verify` does not trigger Claude Code's run-verify-before-commit behavior; only a project or personal skill does
   - project settings must be committed to the repo
7. **`@imports` don't save context.** Imported files load with their parent. To save tokens, use path-scoped `.claude/rules/` and skills instead.
8. **Plugin subagents ignore `hooks`, `mcpServers` and `permissionMode`.** Don't use those fields in `plugins/foundry/agents/*.md`.
9. **Keep each SKILL.md ≤ 150 lines.** Move detail into sibling reference files that the skill links to.
10. **Everything the plugin needs at runtime lives inside `plugins/foundry/`.** That includes packs, templates and scripts, because installed plugins are copied to a cache. Reference these files with `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`.
11. **Bootstrap is idempotent.** It never overwrites a file without showing a diff and getting approval.
12. **Subagents cost tokens in total; they only save main-thread context.** Use them for heavy reading. Parallelize only in `/audit`, and warn about the cost there.

---

## 3. Target repository layout

```
foundry/                                   # repo root (this directory)
├── (plan.md moved to docs/build-plan.md in Phase 4)
├── README.md
├── CHANGELOG.md
├── pyproject.toml                         # dev tooling for the repo itself (pytest, ruff, pyright)
├── .claude-plugin/
│   └── marketplace.json                   # the repo IS the team marketplace  (verify)
├── plugins/foundry/
│   ├── .claude-plugin/plugin.json         # (verify)
│   ├── foundry.config.json                # marketplace source etc., filled in Phase 4
│   ├── skills/
│   │   ├── bootstrap/
│   │   │   ├── SKILL.md
│   │   │   ├── reference.md               # interview questions, file-by-file spec
│   │   │   └── scripts/
│   │   │       ├── detect_stack.py
│   │   │       └── merge_settings.py
│   │   ├── plan-feature/SKILL.md
│   │   ├── system-design/SKILL.md
│   │   ├── threat-model/SKILL.md
│   │   ├── product-brief/SKILL.md
│   │   ├── review-diff/SKILL.md
│   │   ├── audit/SKILL.md
│   │   └── commit/SKILL.md
│   ├── agents/
│   │   ├── architect.md
│   │   ├── security-auditor.md
│   │   ├── product-designer.md
│   │   ├── code-reviewer.md
│   │   └── test-runner.md
│   ├── hooks/
│   │   ├── hooks.json                     # (verify)
│   │   └── scripts/
│   │       ├── protect_paths.py
│   │       ├── guard_bash.py
│   │       └── notify.py
│   ├── packs/
│   │   └── python/
│   │       ├── pack.json                  # detection + default commands
│   │       ├── claude-md.fragment.md      # stack section for CLAUDE.md
│   │       ├── settings.json              # permissions + PostToolUse format hook
│   │       ├── rules/python.md
│   │       ├── rules/testing.md
│   │       ├── hooks/ruff_on_edit.py
│   │       └── skills/verify/SKILL.md
│   └── templates/
│       └── CLAUDE.md.tmpl
├── fixtures/
│   └── sample-py-app/                     # pilot + eval target with seeded issues
├── evals/
│   ├── answer-keys/sample-py-app.md       # seeded issues, kept OUTSIDE the fixture
│   ├── cases/                             # one file per case
│   ├── run_evals.py                       # fallback runner (see Phase 3)
│   └── results/
├── tests/                                 # pytest for hooks and scripts
└── docs/
    ├── decisions.md
    └── adding-a-stack-pack.md
```

---

## Phase 0: Preflight

- [ ] Run `claude --version`. If it's below **2.1.286**, stop and tell the user.
- [ ] Check for `git`, `python3` (≥ 3.10) and `uv`. Report anything missing, but don't install it.
- [ ] Ask the user in one question which OSes the team uses. If Windows is included, record in `docs/decisions.md` how the hook commands invoke Python (for example `py -3` vs `python3`), and make §1.2 handle it.
- [ ] **(verify)** Read these docs pages and write the exact schemas you will use into `docs/decisions.md`, under **"Verified schemas"**:
  - `plugins/create.md` and `plugins/components.md`: `plugin.json`, the component folders, `${CLAUDE_PLUGIN_ROOT}`, and whether plugin *default settings* may carry `permissions.deny`
  - `plugins/create-marketplace.md`: `marketplace.json`
  - `skills.md`: frontmatter, string substitutions, `allowed-tools`
  - `sub-agents.md`: frontmatter, and which fields plugin agents ignore
  - `hooks.md`: plugin `hooks/hooks.json` shape, exit-code behavior per event, how `PostToolUse` feeds text back to Claude
  - `plugin-evals.md`: the eval suite format, and whether the feature is available (it may be early access)
  - `plugins/org.md`: `extraKnownMarketplaces` and `enabledPlugins` in project settings
- [ ] Run `git init` and create a `.gitignore` (Python, `.venv/`, `evals/results/*.jsonl`, `.claude/settings.local.json`, `CLAUDE.local.md`).
- [ ] Create a root `pyproject.toml` with dev deps (pytest, ruff, pyright), then run `uv sync`.

**Gate 0:** `docs/decisions.md` contains the verified schemas, and every conflict with this plan is listed. Continue to Phase 1 automatically if there are no conflicts.

---

## Phase 1 (M1): skeleton, guard hooks, Python pack, bootstrap

### 1.1 Manifests **(verify shapes against Gate 0 notes)**

`.claude-plugin/marketplace.json` should look roughly like this:
```json
{
  "name": "foundry",
  "owner": { "name": "<team name — ask the user>" },
  "plugins": [
    { "name": "foundry", "source": "./plugins/foundry",
      "description": "Project bootstrap + on-demand architecture, security, product and review specialists." }
  ]
}
```

`plugins/foundry/.claude-plugin/plugin.json` needs `name: "foundry"`, `version: "0.1.0"`, a description and an author.

### 1.2 Guard hooks (stack-agnostic, ship in the plugin)

**General rules for the hook scripts**
- Python stdlib only.
- Read the hook JSON from stdin.
- Block by exiting **2** with a one-line reason on stderr, prefixed `foundry:`.
- Exit 0 otherwise.
- On any internal error, exit 0. A broken guard must not brick sessions. Log the error to stderr instead.

**`protect_paths.py`** (PreToolUse, matcher `Edit|Write|NotebookEdit`)

Blocks `tool_input.file_path` when it matches any of:
- `.env` or `.env.*` (but not `.env.example` or `.env.sample`)
- `secrets/**`
- `*.pem`, `*.key` or `id_rsa*`
- anything inside `.git/`

Normalize backslashes before matching.

**`guard_bash.py`** (PreToolUse, matcher `Bash`)

Blocks `tool_input.command` when it contains any of these (keep the list short, as data at the top of the file):
- `rm -rf` (or `-fr`) targeting `/`, `~`, `$HOME`, `.`, `..` or `*`
- `git push` with `--force` or `-f` (but allow `--force-with-lease`)
- `git push` targeting `main` or `master` directly
- `git reset --hard` combined with `origin/`
- `git clean -fdx`
- `curl … | sh` or `wget … | sh`
- reading `.env` files via `cat`, `less`, `head` or `tail`

Document in the file header that this is **best effort**. Permission `deny` rules and the sandbox are the real boundary.

**`notify.py`** (Notification)
- macOS: `osascript`
- Linux: `notify-send`, only if it's on PATH
- Windows: PowerShell MessageBox
- Always exit 0.

**`hooks/hooks.json`** registers all three. Commands use `"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.py"` with the interpreter decided in Phase 0. Set a timeout of ≤ 10s for each.

**Tests**
- Add `tests/test_protect_paths.py` and `tests/test_guard_bash.py`. Each feeds sample JSON on stdin and asserts exit codes, covering at least 8 blocked cases and 8 allowed cases.
- Include tricky cases: `.env.example`, `src/env.py`, `git push --force-with-lease`, `echo "rm -rf /"` inside a string. Decide and document the behavior for that last one.

### 1.3 Python pack (`plugins/foundry/packs/python/`)

**`pack.json`**
```json
{
  "name": "python",
  "detect": ["pyproject.toml", "uv.lock", "requirements.txt", "requirements-dev.txt", "setup.py", "setup.cfg"],
  "defaults": {
    "install": "uv sync",
    "test": "uv run pytest -q",
    "test_one": "uv run pytest -q path/to/test_file.py::test_name",
    "lint": "uv run ruff check .",
    "format": "uv run ruff format .",
    "typecheck": "uv run pyright"
  },
  "detect_overrides": "If the project uses poetry/pip/hatch/tox/mypy instead, bootstrap uses those commands."
}
```

**`rules/python.md`**: frontmatter `paths: ["**/*.py"]`, ≤ 25 lines. It covers:
- use uv for everything (never bare pip)
- type hints on public functions
- no bare `except`
- `pathlib` over `os.path`
- `logging` not `print` in library code
- validate external input at the boundary (pydantic if the project already uses it)
- no new dependencies without saying so

**`rules/testing.md`**: frontmatter `paths: ["tests/**", "**/test_*.py"]`, ≤ 20 lines. It covers:
- pytest
- one behavior per test
- fixtures over setup duplication
- no real network or real secrets
- write a failing test before fixing a bug

**`hooks/ruff_on_edit.py`** (installed into the project as `.claude/hooks/ruff_on_edit.py`)
- On PostToolUse `Edit|Write`, for `.py` files only, run `uv run ruff format <file>` and then `uv run ruff check --fix <file>`.
- If lint errors remain, feed a short summary back to Claude using the PostToolUse mechanism verified in Phase 0.
- Never block. Exit 0 if `uv` or `ruff` is missing.

**`settings.json`** (a fragment that gets merged into the project's `.claude/settings.json`):
- `permissions.allow`: `Bash(uv sync *)`, `Bash(uv run pytest *)`, `Bash(uv run ruff *)`, `Bash(uv run pyright *)`, `Bash(git status *)`, `Bash(git diff *)`, `Bash(git log *)`
- `permissions.deny`: `Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`, `Bash(git push --force *)`, `Bash(rm -rf *)`
- `hooks.PostToolUse`: matcher `Edit|Write` running `"$CLAUDE_PROJECT_DIR"/.claude/hooks/ruff_on_edit.py`, with the interpreter per Phase 0
- `$schema`: `https://json.schemastore.org/claude-code-settings.json`

**`skills/verify/SKILL.md`** (template, copied into the project as `.claude/skills/verify/SKILL.md`):
- It must **not** set `disable-model-invocation`, so Claude Code's before-commit behavior applies.
- Description: "Run this project's format, lint, type and test checks and report only failures. Use before committing or when asked to verify a change."
- `allowed-tools: Bash(uv run *)`
- The body runs the four commands from `pack.json` (bootstrap substitutes the detected ones) and reports failures grouped by tool, in ≤ 30 lines of output. It does **not** fix anything unless asked.

**`claude-md.fragment.md`**: the `## Commands` section with placeholders `{{install}}`, `{{test}}`, `{{test_one}}`, `{{lint}}`, `{{format}}`, `{{typecheck}}`.

### 1.4 `templates/CLAUDE.md.tmpl` (rendered output must be ≤ 80 lines)

Sections and nothing else:
- `# Project: {{name}}`: one paragraph covering what it is, who uses it, and the stack
- `## Commands`: from the pack fragment
- `## Conventions`: only those that differ from language defaults, from the interview
- `## Workflow`:
  - plan first when touching more than 2 files (`/foundry:plan-feature`)
  - write a failing test before fixing a bug
  - conventional commits
  - run `/verify` before committing
- `## Gotchas`: from the interview
- `## Security notes`: present only if the project handles PII, payments, auth or secrets

### 1.5 `bootstrap` skill

**Frontmatter**
- `name: bootstrap`
- `disable-model-invocation: true`
- `argument-hint: [project-path]`
- `allowed-tools: Read Glob Grep Bash(git status *) Bash(git rev-parse *)`, plus the two scripts via `${CLAUDE_SKILL_DIR}/scripts/*`
- Description ≤ 200 chars.

**Steps (SKILL.md body, ≤ 150 lines; detail goes in `reference.md`)**

1. **Inventory (read-only).**
   - Resolve the target dir (`$ARGUMENTS`, or the current dir).
   - Run `detect_stack.py`, which matches `packs/*/pack.json` `detect` lists and parses `pyproject.toml` for tool hints (poetry, hatch, mypy, …).
   - Read the README and any existing `CLAUDE.md` / `.claude/`.
   - If no pack matches, say so. Continue with a generic CLAUDE.md and the guard settings only.
2. **Interview.** Use AskUserQuestion with ≤ 4 questions, prefilled from the inventory:
   1. A one-line purpose and its users
   2. Confirm the detected commands
   3. Conventions and gotchas Claude can't infer
   4. Sensitivity: does it handle PII, payments, auth or secrets?
3. **Propose.** List every file to be created or changed. For existing files, show the diff (settings via `merge_settings.py --dry-run`). Wait for approval.
4. **Write:**
   - `CLAUDE.md`, rendered from the template
   - `.claude/settings.json`, via `merge_settings.py`. Its rules:
     - union `permissions.allow` and `permissions.deny`
     - append hooks without duplicating
     - never delete existing keys
     - keep the formatting stable
   - `.claude/rules/*.md` from the pack
   - `.claude/hooks/ruff_on_edit.py`, made executable
   - `.claude/skills/verify/SKILL.md`, with the commands substituted
   - `docs/plans/.gitkeep` and `docs/adr/.gitkeep`
   - append `CLAUDE.local.md` and `.claude/settings.local.json` to `.gitignore` if they're absent
   - if `foundry.config.json` has a `marketplace_source`, also add `extraKnownMarketplaces` and `enabledPlugins` to the project settings (shape from Phase 0)
5. **Report.** List what was written, then the next steps:
   - run `/verify` once
   - review `CLAUDE.md`
   - commit `.claude/` and `CLAUDE.md`

**Tests**
- `tests/test_merge_settings.py`: empty target, existing target, duplicate hooks, `--dry-run` output, idempotency (running twice gives identical files)
- `tests/test_detect_stack.py`

### 1.6 Fixture: `fixtures/sample-py-app/`

A small uv project using only the stdlib and `sqlite3`: `src/sample_app/{cli.py, api.py, db.py, auth.py, reports.py}` plus `tests/`, with `pytest` passing **except one test**.

Seed these issues, and record them **only** in `evals/answer-keys/sample-py-app.md`. Never put them in the fixture itself.
1. **Security:** a SQL query built with an f-string from user input (`db.py`)
2. **Security:** a hardcoded API key constant (`api.py`)
3. **Security:** a missing authorization check on a delete function (`api.py`)
4. **Bug:** an off-by-one in pagination (`reports.py`), with a failing test that shows it
5. **Design:** `reports.py` does I/O, formatting and business rules in one 150-line function, and `cli.py` imports from `db.py` directly, bypassing `api.py`
6. **Product/UX:** CLI error messages are raw exceptions, and there's no confirmation before a destructive command

### Gate 1
- **(verify)** `claude plugin validate ./plugins/foundry` passes, and so does `claude plugin validate .` (the marketplace).
- `uv run pytest` passes for `tests/`.
- **Manual checks for the user.** Print these exact commands for the user to run:
  1. `cp -r fixtures/sample-py-app /tmp/foundry-pilot && cd /tmp/foundry-pilot && git init && git add -A && git commit -m init`
  2. `claude --plugin-dir <repo>/plugins/foundry`, then `/foundry:bootstrap`
  3. Confirm that:
     - `CLAUDE.md` is ≤ 80 lines
     - `.claude/settings.json` is merged correctly
     - an edit to a `.py` file gets ruff-formatted
     - asking Claude to edit `.env` is blocked
     - `/verify` runs the checks
- Commit, summarize, and **stop**.

---

## Phase 2 (M2): specialists

### 2.1 Subagents (`plugins/foundry/agents/`)

Each body is ≤ 60 lines and contains:
- the role
- the procedure
- a checklist
- the report format (§5.2), inlined
- a reminder that the subagent **cannot edit files** and sees none of the parent conversation, so it should state assumptions in "Open questions"

No `hooks`, `mcpServers` or `permissionMode` fields (see principle 8).

| name | model | tools | focus |
|---|---|---|---|
| `architect` | opus | Read, Grep, Glob | module boundaries, data flow, coupling, scalability, failure modes, trade-offs between ≥ 2 options |
| `security-auditor` | opus | Read, Grep, Glob | OWASP Top 10, input validation, authn/authz, secrets, injection, deps, logging of sensitive data; STRIDE when asked |
| `product-designer` | sonnet | Read, Grep, Glob | user flows, empty/error/loading states, copy clarity, destructive-action safety, accessibility, acceptance criteria |
| `code-reviewer` | sonnet | Read, Grep, Glob, Bash | runs `git diff`, reads changed files and their direct callers; correctness, error handling, tests, readability |
| `test-runner` | haiku | Read, Grep, Glob, Bash | runs the project's test command from CLAUDE.md; returns failing tests with the minimal error, nothing else |

Descriptions are ≤ 200 chars. Add "Use proactively after code changes" to `code-reviewer` only.

### 2.2 Shared report format (inline it in every specialist agent)

```
## Summary
<≤3 lines>
## Findings
- [Critical|Warning|Suggestion] <title> — <file:line> — <why it matters> — Fix: <one line or ≤5-line snippet>
## Open questions
## Not checked
```

### 2.3 Skills

Each skill gathers context in the main thread first, because subagents see nothing. It then passes the specialist a self-contained brief: goal, scope paths, constraints, and relevant CLAUDE.md facts.

| skill | invocation | does | writes |
|---|---|---|---|
| `plan-feature` | manual | interview (≤ 4 Qs) → read code via Explore → plan with ordered steps, each with a verify step; risks; out of scope → **stop for approval** | `docs/plans/<slug>.md` |
| `system-design` | model-invocable | frame the decision + constraints → `architect` → ADR (Context, Decision, Alternatives considered, Consequences; status Proposed) | `docs/adr/NNNN-<slug>.md` |
| `threat-model` | model-invocable | scope → `security-auditor` in STRIDE mode → assets, entry points, trust boundaries, STRIDE table, findings, mitigations → offer `/foundry:plan-feature` for Criticals | `docs/security/threat-model-<scope>.md` |
| `product-brief` | model-invocable | `product-designer` → problem, users, jobs, flows, edge/empty/error states, acceptance criteria, UX copy | `docs/product/<slug>-brief.md` |
| `review-diff` | model-invocable | `code-reviewer` on the current diff; also `security-auditor` if the diff touches auth, input handling, crypto, SQL or dependencies | nothing (reply only) |
| `audit` | manual | **warn about token cost first**; optional scope arg (`/foundry:audit src/payments`); run `architect`, `security-auditor`, `product-designer` and `code-reviewer` (whole-repo mode) **in parallel**; dedupe and prioritize | `docs/audit/<YYYY-MM-DD>.md` |
| `commit` | manual | run the project `verify` skill if present → conventional commit message from the diff → commit. `allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *) Bash(git diff *)` | git commit |

Skill names are namespaced by the plugin (`/foundry:<name>`). Don't name any of them `code-review`, `verify` or `simplify`, so they don't get confused with the bundled skills.

### Gate 2
- `claude plugin validate` passes.
- **Manual pilot for the user** in `/tmp/foundry-pilot`: run each specialist skill once and check the findings against `evals/answer-keys/sample-py-app.md`. Expected hits:
  - `threat-model` finds issues 1–3
  - `review-diff` on a change to `reports.py` finds issue 4
  - `system-design` flags issue 5
  - `product-brief` flags issue 6
- Record the results in `evals/results/manual-pilot.md`.
- Commit, summarize, and **stop**.

---

## Phase 3 (M3): evals and token budget

### 3.1 Always-on overhead
In a temp copy of the fixture, run each of these 3 times:
- `claude -p "Reply with OK." --output-format json`
- the same command plus `--plugin-dir <repo>/plugins/foundry`

Overhead is the median difference in input tokens (count cache read + creation + input). Write the result to `evals/results/<date>-overhead.md`. **Target: ≤ 2,000 tokens.** If it's over, trim descriptions first.

### 3.2 Specialist evals
- **(verify)** If `claude plugin eval` is available for this account, write the suite in its documented format, with 3 cases per model-invocable skill. Use graders that check the answer-key hits and that the expected output file exists.
- **Otherwise, build the fallback** `evals/run_evals.py` (stdlib). It works like this:
  - Each `evals/cases/<id>.json` holds `prompt_with` (slash command), `prompt_baseline` (the same request in plain words), `expect_files`, `expect_hits` (regexes from the answer key) and `runs` (default 3).
  - For each run, copy the fixture into a fresh temp dir and run `claude -p "<prompt>" --output-format json --permission-mode acceptEdits`, once with `--plugin-dir` and once without.
  - Record pass/fail, answer-key recall, total tokens, cost and duration.
  - Write a markdown table to `evals/results/<date>-evals.md`.
- **Before running the full suite,** run one case, show the user its cost, extrapolate the cost of the full run, and **ask for approval**.

### 3.3 Pass bar (initial; adjust with the user)
- For each specialist skill, answer-key recall is ≥ the baseline's, and total tokens are ≤ 1.5× the baseline's.
- Fewer than 10% of runs fail to produce the expected output file.

### 3.4 Manual for the user
In an interactive session on the pilot repo, run:
- `/context`
- `/skill-doctor`
- `/doctor prompt-audit`

Paste the findings so they can be logged.

### Gate 3
- Results tables are committed.
- Every skill below the bar is either fixed or flagged with a reason.
- Commit, summarize, and **stop**.

---

## Phase 4 (M4): team rollout

- [ ] Ask the user for the Git remote (org/repo) and the team name. Fill in `foundry.config.json` → `marketplace_source`, and the marketplace `owner`.
- [ ] Write `README.md` (≤ 150 lines) with these sections:
  - what it is
  - install: `/plugin marketplace add <org>/<repo>` then `/plugin install foundry@foundry`
  - the daily loop: bootstrap → plan-feature → build → review-diff → verify → commit
  - skills and agents table
  - the token budget philosophy
  - updating
  - uninstalling
- [ ] Write `docs/adding-a-stack-pack.md`: copy `packs/python`, then edit `pack.json`, the rules, the settings fragment, the format hook and the verify template; add a detect test; run evals.
- [ ] Add a `CHANGELOG.md` with `0.1.0`, and move `plan.md` → `docs/build-plan.md`.
- [ ] **(verify)** Write a project-settings snippet for teammates (`extraKnownMarketplaces` + `enabledPlugins`), so cloning a bootstrapped repo prompts them to install foundry. Document it in the README.
- [ ] **Optional, only if the user says yes:** a GitHub Action that runs `claude plugin validate` and `uv run pytest` on PRs.
- [ ] **Ask before pushing.** Then push and tag `v0.1.0`.

### Gate 4
Print the fresh-machine install test for the user:
1. Add the marketplace and install
2. Clone or create a Python repo
3. Run `/foundry:bootstrap`
4. Run `/verify`
5. Run `/foundry:review-diff` on a small change

Summarize and stop.

---

## 4. Definition of done (v1)
- `claude plugin validate` passes for both the plugin and the marketplace. The hook and script tests pass.
- Bootstrap on the fixture produces:
  - a `CLAUDE.md` of ≤ 80 lines
  - correctly merged settings
  - a working format hook
  - a working `verify` skill

  Running bootstrap a second time changes nothing.
- The guard hooks block the documented cases and allow the documented safe cases.
- Always-on overhead is measured and ≤ 2,000 tokens.
- Every specialist skill meets the §3.3 bar, or has a logged exception.
- The README lets a teammate install and use foundry in under 10 minutes.

## 5. Out of scope and backlog (log ideas here, don't build them)
- More stack packs (TypeScript, Go, mobile)
- `memory: project` on `code-reviewer` / `security-auditor` (needs write tools; revisit after the pilot)
- MCP servers (GitHub, Sentry) scoped to specific agents
- AGENTS.md output for other coding agents
- CI review bot
