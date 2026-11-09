# Decisions log

Source of truth for config formats is the official docs at `https://code.claude.com/docs/en/<page>.md`,
fetched raw on **2026-11-09** against **Claude Code 2.1.319**. Where the docs and `plan.md`
disagree, the docs win and the difference is listed under **Conflicts with plan.md**.

---

## Preflight (Phase 0)

| Check | Result |
|---|---|
| `claude --version` | 2.1.319 (≥ 2.1.286 required) ✔ |
| `git` | 2.54.0.windows.1 ✔ (≥ 2.31, needed by `claude plugin eval`) |
| `python3` | ✘ on this machine it is the Microsoft Store stub (`WindowsApps\python3.exe`), which doesn't run Python |
| `python` / `py -3` | Python 3.12.10 ✔ |
| `uv` | ✘ **not installed**, so `uv sync` is blocked until the user installs it |
| `claude plugin eval --help` | available ✔ (GA since v2.1.269; a server-side gate would only show on a real run) |
| `claude plugin details --help` | available ✔ |
| Name clashes in `~/.claude` | none (no `foundry` skills, agents or marketplaces) |
| Team OSes | **Windows + macOS** (user answer, 2026-11-09) |

---

## D-001: How hook commands invoke Python (Windows + macOS)

**Problem.** No single interpreter name works on both OSes. macOS has `python3` and usually no
`python`, while Windows has `python` / `py` and a `python3` that is often the Store stub. Exec-form
hooks (`command` + `args`) need one real executable name, so they can't solve this.

**Decision.** Hooks use **shell form** and call a tiny POSIX launcher, `py`, via `sh`:

```json
{ "type": "command",
  "command": "sh \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/py\" \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/guard_bash.py\"",
  "timeout": 10, "onFailure": "continue" }
```

- The launcher uses only `command -v` lookups, with no extra process spawn. On Windows
  (`uname` = MINGW/MSYS/CYGWIN) it tries `python`, `py`, `python3`, in that order; elsewhere
  `python3`, `python`. It then `exec`s the first one found. If none is found, it prints a
  `foundry:` warning to stderr and exits 0.
- The Python scripts check `sys.version_info >= (3, 10)` themselves and exit 0 if it's too old.
- We invoke it as `sh <path>`, so it needs no executable bit (git on Windows often drops it).
- Shell form on Windows runs in **Git Bash**. Teammates on Windows must have Git for Windows
  installed; README will say so. Without Git Bash, shell-form hooks run in PowerShell, `sh`
  isn't found, and `onFailure: "continue"` keeps the session usable (guards degrade to no-ops).
- `${CLAUDE_PLUGIN_ROOT}` is double-quoted per the docs (shell form). On Windows it's substituted
  with forward slashes.
- The project-side `ruff_on_edit.py` hook uses the same launcher. Bootstrap copies it to
  `.claude/hooks/py`, and the hook calls it via `"$CLAUDE_PROJECT_DIR"/.claude/hooks/py`.

---

## Verified schemas

### Plugin manifest: `plugins/foundry/.claude-plugin/plugin.json` (plugins/manifest-reference)
- Only `name` is required (kebab-case, and no `claude-`/`anthropic-` prefix). Validate **warns** when
  `version`, `description` or `author` is missing, so we set all of them.
- `author` = `{ "name": required, "email"?, "url"? }`. Also optional: `$schema`, `displayName`,
  `homepage` (must parse as a URL), `repository`, `license`, `keywords`.
- Unknown top-level keys are stripped (validate warns, `--strict` fails).
- **Only** `plugin.json` goes in `.claude-plugin/`. Components sit at the plugin root.
- Default component dirs: `skills/<name>/SKILL.md`, `agents/*.md` (recursive), `hooks/hooks.json`,
  `.mcp.json`. With no manifest keys for them, these are auto-discovered, so our manifest declares none.
- `--plugin-dir` must point at the plugin root (`plugins/foundry`), **not** the marketplace root.

```json
{ "name": "foundry", "version": "0.1.0",
  "description": "...", "author": { "name": "..." } }
```

### Plugin default settings (plugins/components → "Default settings")
- A plugin-root `settings.json` (or manifest `settings`) honors **only `agent` and
  `subagentStatusLine`**. Every other key, `permissions` included, **is dropped**.
- ⇒ Plugin default settings **cannot** carry `permissions.deny`. Deny rules must be written into
  each project's `.claude/settings.json` by bootstrap (as plan.md already intends).

### Path variables (plugins/components, skills)
- `${CLAUDE_PLUGIN_ROOT}`: install dir (versioned cache; don't write there). `${CLAUDE_PLUGIN_DATA}`:
  persistent dir. `${CLAUDE_PROJECT_DIR}`: project root.
- These are substituted in skill/agent content, in hook commands, and in **Bash rules inside a skill's
  `allowed-tools`**, and exported as env vars to hook processes.
- `${CLAUDE_SKILL_DIR}` = the skill's own directory (skills only).

### Marketplace: `.claude-plugin/marketplace.json` (plugins/marketplace-reference)
- Required: `name` (letters/digits/`.`/`_`/`-`, not reserved; `foundry` is fine), `owner`
  (`{name, email?, url?}`), `plugins[]`. Validate warns when top-level `description` is missing.
- Entry: `name` + `source` required. A relative `source` must start with `./` and resolves from the
  marketplace root (the dir containing `.claude-plugin/`). It can't contain `..`, and backslashes are refused.
- Don't set `version` on both the entry and `plugin.json` (validate warns; `plugin.json` wins).

```json
{ "name": "foundry", "owner": { "name": "<team>" }, "description": "...",
  "plugins": [ { "name": "foundry", "source": "./plugins/foundry", "description": "..." } ] }
```

### Skills: `SKILL.md` frontmatter (skills → Frontmatter reference)
- Must open with `---` on line 1. All fields are optional. Unknown fields are ignored silently.
- Fields we use: `name`, `description`, `argument-hint`, `disable-model-invocation`,
  `allowed-tools` (space/comma string or YAML list), `when_to_use` (avoid it: it counts toward the
  listing), `context: fork` + `agent`, `paths`.
- The description listing cap is 1,536 chars (description + when_to_use); our own cap is 200.
  Avoid `<`/`>` in descriptions (shown as `&lt;`).
- `disable-model-invocation: true` ⇒ the description is **not** in context (zero always-on cost) and
  the skill can't be preloaded into subagents.
- `allowed-tools` pre-approves listed tools **for the invoking turn only**. It doesn't restrict tools.
  Example: `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)`.
- Substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, `$name` (via `arguments`),
  `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`,
  `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`. Dynamic context: `` !`cmd` ``.
- Plugin skill command = `/<plugin>:<dir or name>`.
- **Run-verify-before-commit** (v2.1.286+): applies when a model-invocable skill named `verify`
  or `simplify` loads from the personal, project or additional-dir location. Plugin skills, bundled
  skills and synced skills **don't count**, and `disable-model-invocation: true` disables it. This
  confirms plan principle 6.

### Subagents: `agents/*.md` frontmatter (sub-agents, plugins/components)
- Required: `name` (no `:`; ≤ 256 chars) and `description`. camelCase field names.
- Fields: `tools` (comma string or list), `disallowedTools`, `model` (`sonnet|opus|haiku|fable|inherit|<id>`),
  `effort`, `maxTurns`, `skills`, `memory`, `background`, `omitClaudeMd`, `isolation: worktree`,
  `color`, `autoCompactWindow`, `experimental.cacheTtl`.
- **Plugin agents ignore `permissionMode`, `hooks`, `mcpServers` and `initialPrompt`.**
- Scoped name is `foundry:<name>`. A subagent sees no parent conversation, but **does** load the
  CLAUDE.md hierarchy and a git status snapshot (unless `omitClaudeMd: true`).
- `AskUserQuestion` is never available to subagents.

### Hooks: `plugins/foundry/hooks/hooks.json` (hooks, plugins/components)
- Shape: same as the settings `hooks` object, under a top-level `"hooks"` key. An optional top-level
  `"description"` is allowed.

```json
{ "description": "...",
  "hooks": { "<Event>": [ { "matcher": "Edit|Write",
      "hooks": [ { "type": "command", "command": "...", "timeout": 10, "onFailure": "continue" } ] } ] } }
```

- Matcher: letters/digits/`_`/`-`/space/`,`/`|` ⇒ an exact list (`Edit|Write`). Any other char ⇒
  an unanchored JS regex.
- Command handler fields: `command`, `args` (exec form, no shell), `shell` (`bash|powershell`),
  `timeout` (**seconds**, default 600), `async`, `asyncRewake`, `onFailure` (`continue|block`,
  v2.1.295+), `if` (one permission rule, tool events only), `statusMessage`.
- Shell form runs `sh -c` on macOS/Linux and **Git Bash on Windows (PowerShell if Git Bash is missing)**.
- Exit codes: `0` = success (stdout JSON applies). `2` = blocking error, with **stderr** as the reason.
  Other = non-blocking error (the action proceeds). Exception: on **Windows without Git Bash**, a
  failed shell-form PreToolUse hook **blocks**, unless `onFailure` is set.
- Exit 2 per event: `PreToolUse` blocks the call. `PostToolUse` can't block; stderr is shown to
  Claude. `Notification` ignores exit code and stderr.
- PreToolUse input: `tool_name`, `tool_input`, `tool_use_id`. File tools' `tool_input.file_path` is
  **always absolute**, with **backslashes on Windows** (normalize with `.replace("\\", "/")` and
  match segments, not `^`). NotebookEdit uses `tool_input.notebook_path`. Bash and PowerShell use
  `tool_input.command`.
- **PostToolUse feedback to Claude** (for `ruff_on_edit.py`): exit 0 and print exactly one JSON object:
  `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<summary>"}}`.
  It's injected as a system reminder next to the tool result. Cap is 10,000 chars. Nothing is blocked.
- Notification input: `message`, `title?`, `notification_type`. No decision control. Desktop
  notifications should use the JSON `terminalSequence` field (OSC 9: Windows Terminal/iTerm2/WezTerm,
  OSC 777: Ghostty/Warp/urxvt), because hooks have no `/dev/tty`.
- Plugin hooks fire whenever the plugin is enabled, including inside subagents.

### Permission rules (permissions)
- `Bash(cmd *)` matches subcommands across `&&`, `;`, `|` and `$()`. It doesn't stop `/bin/rm` or
  `sh -c '...'`, so it's best effort; the sandbox is the boundary.
- `PowerShell(...)` rules have the same shape, and aliases are canonicalized (`rm` → `Remove-Item`).
- `Read(path)` deny also blocks Edit/Write on that path, and covers `cat/head/tail/sed` in Bash. It
  does **not** cover NotebookEdit (add `Edit(...)`).
- Gitignore-style paths: `./x` = cwd-relative, a bare name matches at any depth, `!pattern` negates
  earlier `path`/`./path` rules in the same file. So `Read(!./.env.example)` can re-allow the example file.

### Path-scoped rules: `.claude/rules/*.md` (memory)
- `paths` is the only frontmatter field read (YAML list or comma string). The rule loads when
  Claude reads or writes a matching file.
- Block-level HTML comments in CLAUDE.md are stripped before injection, so they're free maintainer notes.

### Project settings for teammates (plugins/org → "Require plugins per repository")

```json
{ "extraKnownMarketplaces": {
    "foundry": { "source": { "source": "github", "repo": "<org>/<repo>" } } },
  "enabledPlugins": { "foundry@foundry": true } }
```

- The key must equal the marketplace `name`. `extraKnownMarketplaces` applies only after the folder
  is trusted. A relative-path plugin (ours) then installs from the marketplace copy.
- A non-GitHub host uses `{ "source": "git", "url": "...", "ref": "main" }`.

### Plugin evals: `claude plugin eval` (plugin-evals)
- Suite dir: `<plugin root>/evals/`, or `experimental.evals` / `--eval-dir`, which must be a
  **relative path under the plugin root with no `..`**.
- One case per directory: `prompt.md` (frontmatter `max_turns`, `timeout_seconds`, `allowed_tools`,
  `runs`, `model`, `tags`, `env`) + `graders/<name>.md`. Optional `case.yaml`
  (`schema_version: "1.1"`, `name`, `context.scaffold_script|add_dirs|history_file`).
- Graders: `regex` (`pattern`, `flags`, `match`, `target`: `last_message|trace|files|{source: file, path}`),
  `tool_used`, `tool_order`, `file_exists` (`path` glob), `llm`, `baseline`. No custom-code graders.
- Every run starts in an **empty** workspace. The fixture must be seeded by a bash `scaffold_script`,
  which runs only with `--scaffold`. Project `.claude/` and `CLAUDE.md` are never loaded in a run.
- The baseline arm (no plugin) runs by default. `tool_used: Skill` graders are excluded from Δ.
- Granting `Bash`/`PowerShell` needs an OS sandbox. **Native Windows has none**, so shell-granting
  cases must run on macOS or WSL2.
- Cost: cases × runs × 2 arms (+ judge calls). `--max-cost-usd` sets a hard ceiling.

### Validation and cost tools (plugins/cli-reference, plugins/measure)
- `claude plugin validate <dir> [--strict] [--json]`: exit 0 = pass (warnings allowed), 1 = fail.
  On a dir with both manifests (v2.1.289+), it validates the marketplace **and** the plugin, but a
  marketplace run doesn't open plugin component files in other dirs, so validate both paths.
- `claude --plugin-dir plugins/foundry plugin details foundry` prints the **always-on token estimate**
  (names + descriptions of skills/agents). This is a free cross-check for the Phase 3 `claude -p` measurement.

---

## Conflicts with plan.md (docs win)

| # | plan.md says | Docs say | Resolution |
|---|---|---|---|
| C-1 | `guard_bash.py` matcher `Bash`; deny rules `Bash(...)` only | On Windows the **PowerShell tool is primary**, and without Git Bash the Bash tool doesn't exist. A `Bash`-only hook never fires there | Matcher `Bash\|PowerShell`. The guard also checks PowerShell forms (`Remove-Item -Recurse -Force` on roots, `Get-Content`/`gc`/`type` on `.env`). The settings fragment adds the matching `PowerShell(...)` deny rules |
| C-2 | Plugin agents ignore `hooks`, `mcpServers`, `permissionMode` | They also ignore **`initialPrompt`** | Don't use it either |
| C-3 | Eval suite in repo-root `evals/cases/` | The `claude plugin eval` suite must sit **under the plugin root** (no `..`) | Suite goes in `plugins/foundry/evals/`. The answer key stays at repo-root `evals/answer-keys/`, and its regexes are inlined into graders (graders are hidden from the agent). The fallback runner stays at `evals/run_evals.py` if needed |
| C-4 | Eval runs copy the fixture into a temp dir | Runs start empty; seeding needs a bash `scaffold_script` + `--scaffold`. Bash-granting cases can't run on native Windows | Each case gets a `scaffold.sh` that copies `fixtures/sample-py-app`. Cases that need Bash (`review-diff`) run on macOS or WSL2; flagged at Gate 3 |
| C-5 | Windows hooks invoke Python via `py -3` or `python3` | Neither works on both OSes; exec form needs a single real `.exe` | D-001 shell-form launcher |
| C-6 | Guards "exit 0 on internal error" | On Windows without Git Bash, a failing PreToolUse hook **blocks** unless `onFailure` is set | Set `"onFailure": "continue"` on every foundry hook |
| C-7 | Marketplace example has no top-level `description` | Validate warns when it's missing | Add one |

## Deviations from plan.md (not doc conflicts; **approved by user 2026-11-09**)

| # | Decision | Why |
|---|---|---|
| P-1 | `notify.py` on Windows: emit a `terminalSequence` OSC 9 notification instead of a PowerShell MessageBox. macOS: `osascript display notification` + OSC 9. Linux: `notify-send` if on PATH | A MessageBox is modal: it would block the hook until clicked or killed at the 10 s timeout. The docs recommend `terminalSequence` for desktop notifications |
| P-2 | Settings fragment adds `Read(!./.env.example)` and `Read(!./.env.sample)` after `Read(./.env.*)` | Otherwise the deny blocks reading the safe example files, which contradicts `protect_paths` |
| P-3 | Bootstrap warns that a project `verify` skill **replaces the bundled `/verify`** (app launch + drive) in that repo | The docs confirm the replacement. That's the plan's intent (pre-commit checks), but it changes what `/verify` means for teammates |

## Resolved items
- **uv**: wasn't installed. With the user's approval, it was installed per-user via the official installer
  (uv 0.13.7 in `~/.local/bin`, which isn't yet on the PATH of already-open shells). `uv sync` passes.
- **Git identity**: none was configured. A repo-local `user.name`/`user.email` was set for this repo only.
- **Line endings**: git converts LF to CRLF on this machine, which would break `sh` scripts on macOS.
  `.gitattributes` forces LF for all text files.

## Backlog (log only, don't build)
- See plan.md §5.
