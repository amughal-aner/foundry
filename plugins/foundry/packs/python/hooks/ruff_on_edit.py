#!/usr/bin/env python3
"""foundry PostToolUse hook (Python pack): ruff-format and auto-fix each edited .py file.

Installed into a project as .claude/hooks/ruff_on_edit.py by /foundry:bootstrap.
- Runs `ruff check --fix <file>` then `ruff format <file>` (ruff's recommended order: fixes can
  leave gaps that only the formatter cleans up), via uv (uv.lock or pyproject.toml), poetry
  (poetry.lock) or a ruff on PATH. If issues remain, one more `ruff check` gets line numbers
  that match the formatted file.
- If lint errors remain, it tells Claude through PostToolUse `additionalContext` (exit 0, one JSON
  object on stdout).
- Never blocks. Exits 0 silently when the file isn't .py, or the runner or ruff is missing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 20
MAX_LINES = 10


def runner_prefix(project: Path) -> list[str] | None:
    if shutil.which("uv") and (
        (project / "uv.lock").exists() or (project / "pyproject.toml").exists()
    ):
        return ["uv", "run", "-q"]
    if shutil.which("poetry") and (project / "poetry.lock").exists():
        return ["poetry", "run"]
    if shutil.which("ruff"):
        return []
    return None


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return None


def summarize(rel: str, output: str) -> str | None:
    lines = [ln for ln in output.splitlines() if ln.strip() and not ln.startswith("Found ")]
    if not lines:
        return None
    shown = lines[:MAX_LINES]
    more = f"\n(+{len(lines) - MAX_LINES} more)" if len(lines) > MAX_LINES else ""
    return (
        f"ruff: {len(lines)} issue(s) remain in {rel} after auto-fix:\n" + "\n".join(shown) + more
    )


def main() -> int:
    if sys.version_info < (3, 9):  # noqa: UP036 - macOS CLT python3 is 3.9; older: fail open
        return 0
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path")
    if not isinstance(path, str) or not path.lower().endswith(".py"):
        return 0
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    prefix = runner_prefix(project)
    if prefix is None:
        return 0
    check_cmd = [*prefix, "ruff", "check", "--quiet", "--output-format", "concise", path]
    fixed = _run([*check_cmd[:-1], "--fix", path], project)
    if fixed is None or fixed.returncode not in (0, 1):  # runner or ruff unavailable
        return 0
    _run([*prefix, "ruff", "format", "--quiet", path], project)
    if fixed.returncode == 0:  # clean after auto-fix
        return 0
    check = _run(check_cmd, project)
    if check is None or check.returncode != 1:
        return 0
    try:
        rel = Path(path).resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        rel = path
    message = summarize(rel, check.stdout)
    if message:
        out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a formatter hook must never break a session
        print(f"foundry: ruff_on_edit internal error: {exc}", file=sys.stderr)
        sys.exit(0)
