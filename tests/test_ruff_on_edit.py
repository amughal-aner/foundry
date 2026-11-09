from __future__ import annotations

import json
import os
import shutil

import pytest
from conftest import PACK_PY
from ruff_on_edit import summarize

SCRIPT = PACK_PY / "hooks" / "ruff_on_edit.py"


def payload(path: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": path},
    }


def test_non_python_file_is_ignored(hook, tmp_path):
    result = hook(SCRIPT, payload(str(tmp_path / "README.md")))
    assert result.returncode == 0 and result.stdout == ""


def test_missing_runner_exits_zero_silently(hook, tmp_path):
    env = dict(os.environ, PATH="", CLAUDE_PROJECT_DIR=str(tmp_path))
    result = hook(SCRIPT, payload(str(tmp_path / "a.py")), env=env)
    assert result.returncode == 0 and result.stdout == ""


@pytest.mark.parametrize("bad", ["not json", "{}"])
def test_bad_input_never_blocks(hook, bad):
    assert hook(SCRIPT, bad).returncode == 0


def test_summary_truncates_and_counts():
    out = "\n".join(f"a.py:{i}:1: F401 unused import" for i in range(1, 14)) + "\nFound 13 errors."
    msg = summarize("src/a.py", out)
    assert msg is not None
    assert msg.startswith("ruff: 13 issue(s) remain in src/a.py")
    assert "(+3 more)" in msg


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_formats_file_and_reports_remaining_lint(hook, tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "t"\nversion = "0"\nrequires-python = ">=3.10"\n'
        '[dependency-groups]\ndev = ["ruff"]\n[tool.uv]\npackage = false\n',
        encoding="utf-8",
    )
    src = tmp_path / "a.py"
    src.write_text("import os\nx=1\ndef f(): return undefined_name\n", encoding="utf-8")
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path))
    result = hook(SCRIPT, payload(str(src)), env=env)
    assert result.returncode == 0
    assert "x = 1" in src.read_text(encoding="utf-8")  # formatted
    assert "import os" not in src.read_text(encoding="utf-8")  # F401 auto-fixed
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "F821" in context  # undefined name can't be auto-fixed
