from __future__ import annotations

import shutil
import subprocess

import pytest
from conftest import HOOK_SCRIPTS

SCRIPT = HOOK_SCRIPTS / "protect_paths.py"
PROJECT = "/home/dev/proj"

BLOCKED = [
    f"{PROJECT}/.env",
    f"{PROJECT}/.env.local",
    f"{PROJECT}/.env.production",
    f"{PROJECT}/config/.ENV",  # case-insensitive filesystems
    f"{PROJECT}/secrets/db.txt",
    f"{PROJECT}/deploy/secrets/nested/token.json",
    f"{PROJECT}/certs/server.pem",
    f"{PROJECT}/certs/server.key",
    "/home/dev/.ssh/id_rsa",
    "/home/dev/.ssh/id_rsa.pub",
    f"{PROJECT}/.git/config",
    f"{PROJECT}/.git/hooks/pre-commit",
    r"C:\work\proj\.env",  # Windows paths arrive with backslashes
    r"C:\work\proj\.git\HEAD",
]

ALLOWED = [
    f"{PROJECT}/.env.example",
    f"{PROJECT}/.env.sample",
    f"{PROJECT}/src/env.py",
    f"{PROJECT}/src/environment.py",
    f"{PROJECT}/.envrc",
    f"{PROJECT}/docs/secrets-management.md",
    f"{PROJECT}/src/keyboard.py",
    f"{PROJECT}/.gitignore",
    f"{PROJECT}/.github/workflows/ci.yml",
    r"C:\work\proj\src\app.py",
]


def payload(path: str, tool: str = "Edit") -> dict:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {key: path}}


@pytest.mark.parametrize("path", BLOCKED)
def test_blocks_protected_paths(hook, path):
    result = hook(SCRIPT, payload(path))
    assert result.returncode == 2, result.stderr
    assert result.stderr.startswith("foundry:")
    assert len(result.stderr.strip().splitlines()) == 1


@pytest.mark.parametrize("path", ALLOWED)
def test_allows_ordinary_paths(hook, path):
    result = hook(SCRIPT, payload(path))
    assert result.returncode == 0, result.stderr


def test_notebook_edit_uses_notebook_path(hook):
    assert hook(SCRIPT, payload(f"{PROJECT}/secrets/a.ipynb", "NotebookEdit")).returncode == 2
    assert hook(SCRIPT, payload(f"{PROJECT}/nb/a.ipynb", "NotebookEdit")).returncode == 0


def test_project_named_secrets_is_not_blocked_when_inside_project():
    from protect_paths import block_reason

    root = "/home/dev/secrets"  # the project itself lives in a dir called "secrets"
    assert block_reason(f"{root}/src/app.py", root) is None
    assert block_reason(f"{root}/secrets/x", root) == "secrets directory"


@pytest.mark.parametrize("bad", ["not json", "{}", '{"tool_input": {"file_path": 5}}'])
def test_bad_input_fails_open(hook, bad):
    assert hook(SCRIPT, bad).returncode == 0


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX sh (Git Bash on Windows)")
def test_launcher_runs_hook_end_to_end():
    import json

    result = subprocess.run(
        ["sh", str(HOOK_SCRIPTS / "py"), str(SCRIPT)],
        input=json.dumps(payload(f"{PROJECT}/.env")),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 2, result.stderr
    assert "foundry: blocked edit" in result.stderr
