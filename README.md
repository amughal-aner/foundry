# foundry

A private, team-shared Claude Code **plugin marketplace**. Its one plugin, `foundry`, does two things:

- **Bootstraps** any repository into a configured Claude Code project: `CLAUDE.md`, permission
  rules, path-scoped rules, a format-on-edit hook and a project `verify` skill.
- Provides **on-demand specialists** for architecture, security, product/UX and code review.
  They load only when you use them.

Guardrails are enforced by hooks and permission `deny` rules, not by prose. v1 ships one stack
pack: **Python** (uv + ruff + pytest + pyright). See [docs/adding-a-stack-pack.md](docs/adding-a-stack-pack.md)
to add another.

## Requirements

- Claude Code **v2.1.286 or later** (`claude --version`)
- Python **3.9+** on `PATH` (the hooks are stdlib-only scripts)
- **Windows:** [Git for Windows](https://git-scm.com/downloads/win). Hooks run through Git Bash;
  without it they degrade to no-ops instead of guarding (see `docs/decisions.md`, D-001).
- For the Python pack: [uv](https://docs.astral.sh/uv/)
- Read access to this repository with working git credentials (`git clone` must succeed)

## Install

In any Claude Code session:

```
/plugin marketplace add amughal-aner/foundry
/plugin install foundry@foundry
```

Then run `/reload-plugins` or start a new session. Check it with `/plugin` (foundry should be listed
as enabled).

### Make a repo prompt teammates to install foundry

`/foundry:bootstrap` adds this to the project's `.claude/settings.json` for you (once
`marketplace_source` is set in `plugins/foundry/foundry.config.json`). For a repo you don't
bootstrap, add it by hand and commit it:

```json
{
  "extraKnownMarketplaces": {
    "foundry": { "source": { "source": "github", "repo": "amughal-aner/foundry" } }
  },
  "enabledPlugins": { "foundry@foundry": true }
}
```

When a teammate opens the repo and trusts the folder, Claude Code offers to add the marketplace and
install the plugin. The same thing from a shell:
`claude plugin marketplace add amughal-aner/foundry --scope project`.

## The daily loop

| Step | Command | What happens |
|---|---|---|
| 1. Bootstrap (once per repo) | `/foundry:bootstrap` | Detects the stack, asks ≤ 4 questions, shows every file and diff, writes only after you approve. Re-running changes nothing. |
| 2. Plan | `/foundry:plan-feature` | Interview → reads the code → `docs/plans/<slug>.md` with a verify step per step. Stops for approval. |
| 3. Build | (normal work) | Edits to `.py` files are ruff-fixed and formatted; remaining lint issues are fed back to Claude. |
| 4. Review | `/foundry:review-diff` | Code review of the current diff, plus a security pass when auth, input, SQL, crypto or deps change. |
| 5. Verify | `/verify` | Runs format-check, lint, typecheck and tests; reports only failures. Claude also runs it before committing. |
| 6. Commit | `/foundry:commit` | Runs `verify`, writes a Conventional Commit message from the diff, commits. |

`/verify` is a **project** skill written by bootstrap (a plugin skill can't trigger Claude Code's
verify-before-commit behavior). In a bootstrapped repo it replaces the bundled `/verify`.

## Skills and agents

| Skill | Invocation | Does | Writes |
|---|---|---|---|
| `bootstrap` | manual | Configure a repo for Claude Code | `CLAUDE.md`, `.claude/**`, `docs/{plans,adr}/` |
| `plan-feature` | manual | Interview + ordered implementation plan | `docs/plans/<slug>.md` |
| `system-design` | auto or `/foundry:system-design` | Frame a decision, `architect` weighs ≥ 2 options | `docs/adr/NNNN-<slug>.md` |
| `threat-model` | auto or `/foundry:threat-model` | STRIDE model via `security-auditor` | `docs/security/threat-model-<scope>.md` |
| `product-brief` | auto or `/foundry:product-brief` | Users, flows, edge states, acceptance criteria | `docs/product/<slug>-brief.md` |
| `review-diff` | auto or `/foundry:review-diff` | Review the current diff | nothing (reply only) |
| `audit` | manual | All four specialists in parallel. **Costly; asks first.** | `docs/audit/<date>.md` |
| `commit` | manual | verify → message → commit | a git commit |

| Agent | Model | Tools | Focus |
|---|---|---|---|
| `architect` | opus | Read, Grep, Glob | boundaries, data flow, coupling, failure modes, trade-offs |
| `security-auditor` | opus | Read, Grep, Glob | OWASP Top 10, authn/authz, injection, secrets, deps; STRIDE |
| `product-designer` | sonnet | Read, Grep, Glob | flows, empty/error/loading states, copy, accessibility |
| `code-reviewer` | sonnet | + Bash, PowerShell | the current diff and its direct callers |
| `test-runner` | haiku | + Bash, PowerShell | runs the test command; returns only failures |

All agents are read-only and answer in one shared report format (Summary, Findings, Open questions,
Not checked) of ≤ 400 words.

**Always-on guards** (plugin hooks, every session): block edits to `.env*` (not `.env.example`),
`secrets/**`, keys and `.git/`; block `rm -rf` on roots, force-pushes, pushes to `main`/`master`,
`git reset --hard origin/…`, `git clean -fdx`, `curl … | sh` and reading `.env` from the shell. These
are best effort; the permission `deny` rules bootstrap writes, and the sandbox, are the real boundary.

## Token budget philosophy

Every always-loaded line is paid by every teammate on every turn, so foundry keeps them few:

- **Measured overhead: 743 tokens per session** (budget 2,000; `evals/results/2026-11-09-overhead.md`).
- Descriptions are ≤ 200 characters. Side-effect skills (`bootstrap`, `plan-feature`, `audit`,
  `commit`) set `disable-model-invocation`, so they cost nothing until typed.
- Generated `CLAUDE.md` files are ≤ 80 lines. Language rules live in path-scoped `.claude/rules/`
  that load only when matching files are touched.
- Subagents save *main-thread* context but cost tokens in total. Only `/foundry:audit` runs them in
  parallel, and it warns first.
- Specialist skills are evaluated against a no-plugin baseline (`plugins/foundry/evals/`,
  results in `evals/results/`).

## Updating

- **Teammates:** `/plugin marketplace update foundry`, then `/plugin update foundry@foundry` (or
  `claude plugin update foundry@foundry`), then `/reload-plugins`.
- **Maintainers:** bump `version` in `plugins/foundry/.claude-plugin/plugin.json` (only there, not
  in `marketplace.json`), add a `CHANGELOG.md` entry, and run the checks below before merging.
  Bootstrapped repos keep their generated files; re-run `/foundry:bootstrap` to pick up template
  changes (it shows a diff first).

## Uninstalling

```
/plugin uninstall foundry@foundry
/plugin marketplace remove foundry
```

Files bootstrap wrote into a project (`CLAUDE.md`, `.claude/settings.json`, `.claude/rules/`,
`.claude/hooks/`, `.claude/skills/verify/`) belong to that project. Delete or keep them there. Also
remove the `extraKnownMarketplaces` / `enabledPlugins` entries, or teammates will be prompted again.

## Developing foundry

```
uv sync
uv run pytest                                   # hook, script and constraint tests
uv run ruff check . && uv run pyright
claude plugin validate ./plugins/foundry        # the plugin
claude plugin validate .                        # the marketplace
claude --plugin-dir ./plugins/foundry           # try local changes in a session
```

CI (`.github/workflows/ci.yml`) runs the tests on Linux, macOS and Windows plus both validations on
every pull request. Design decisions and verified config schemas are in
[docs/decisions.md](docs/decisions.md); the original build plan is [docs/build-plan.md](docs/build-plan.md).
