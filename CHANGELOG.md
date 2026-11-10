# Changelog

All notable changes to the foundry plugin. Versions follow [SemVer](https://semver.org/); the
version lives only in `plugins/foundry/.claude-plugin/plugin.json`.

## 0.1.0 (2026-11-10)

First team release.

### Added
- **Marketplace** `foundry` (repo root) with one plugin, `foundry`.
- **`/foundry:bootstrap`**: detects the stack, interviews (≤ 4 questions), shows every file and
  diff, then writes `CLAUDE.md` (≤ 80 lines), merged `.claude/settings.json`, path-scoped rules,
  a format-on-edit hook and a project `verify` skill. Idempotent: a second run changes nothing.
  Adds `extraKnownMarketplaces` / `enabledPlugins` when `foundry.config.json` has a
  `marketplace_source`.
- **Python stack pack**: uv + ruff + pytest + pyright, with poetry / hatch / pip / mypy / black /
  flake8 detection.
- **Guard hooks** (always on): `protect_paths` (`.env*`, `secrets/**`, keys, `.git/`),
  `guard_bash` (destructive `rm`, force/main pushes, hard resets, `git clean -fdx`, `curl | sh`,
  shell reads of `.env`; Bash and PowerShell forms), and `notify` (terminal notifications).
- **Specialist subagents** (read-only): `architect`, `security-auditor`, `product-designer`,
  `code-reviewer`, `test-runner`.
- **Skills**: `plan-feature`, `system-design`, `threat-model`, `product-brief`, `review-diff`,
  `audit`, `commit`.
- **Evals**: a `claude plugin eval` suite (12 cases) generated from the fixture's answer key, and an
  always-on overhead measurement script.
- GitHub Actions CI: tests on Linux, macOS and Windows (Python 3.9 and 3.12) and
  `claude plugin validate` for the plugin and the marketplace.

### Measured
- Always-on overhead: **743 tokens** per session (budget 2,000).
- `threat-model` meets the eval bar (recall = baseline, cost ≤ 1.12× baseline).

### Known limitations
- `system-design` and `product-brief` evals were not run (stopped to save subscription usage, D-021).
- `review-diff` evals need Bash in an OS sandbox, so they run only on macOS, Linux or WSL2 (D-019).
- On Windows, hooks need Git for Windows (Git Bash); without it they degrade to no-ops (D-001).
