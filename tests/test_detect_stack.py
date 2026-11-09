from __future__ import annotations

import json

import pytest
from conftest import FIXTURE, PACK_PY
from detect_stack import detect

DEFAULTS = json.loads((PACK_PY / "pack.json").read_text(encoding="utf-8"))["defaults"]


def make(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


def test_fixture_is_python_with_uv_defaults():
    result = detect(FIXTURE)
    assert result["pack"] == "python"
    assert "pyproject.toml" in result["matched_files"]
    assert result["commands"] == DEFAULTS
    assert result["existing"]["readme"] == "README.md"


def test_no_pack_matches_empty_repo(tmp_path):
    result = detect(make(tmp_path, {"index.js": "console.log(1)"}))
    assert result["pack"] is None
    assert result["commands"] == {}
    assert any("No stack pack matched" in n for n in result["notes"])


def test_poetry_project(tmp_path):
    result = detect(
        make(tmp_path, {"pyproject.toml": "[tool.poetry]\nname='x'\n", "poetry.lock": ""})
    )
    assert result["commands"]["install"] == "poetry install"
    assert result["commands"]["test"] == "poetry run pytest -q"


def test_mypy_replaces_pyright(tmp_path):
    result = detect(
        make(tmp_path, {"pyproject.toml": "[project]\nname='x'\n[tool.mypy]\nstrict=true\n"})
    )
    assert result["commands"]["typecheck"] == "uv run mypy ."
    assert "mypy" in result["tool_hints"]


def test_requirements_only_uses_pip(tmp_path):
    result = detect(
        make(tmp_path, {"requirements.txt": "requests\n", "requirements-dev.txt": "pytest\n"})
    )
    cmds = result["commands"]
    assert cmds["install"] == "python -m pip install -r requirements.txt -r requirements-dev.txt"
    assert cmds["lint"] == "python -m ruff check ."


def test_black_without_ruff_formats_with_black(tmp_path):
    result = detect(make(tmp_path, {"pyproject.toml": "[project]\nname='x'\n[tool.black]\n"}))
    assert result["commands"]["format"] == "uv run black ."
    assert result["commands"]["format_check"] == "uv run black --check ."


def test_tox_adds_note(tmp_path):
    result = detect(
        make(tmp_path, {"pyproject.toml": "[project]\nname='x'\n", "tox.ini": "[tox]\n"})
    )
    assert any("tox" in n for n in result["notes"])


@pytest.mark.parametrize("marker", ["setup.py", "setup.cfg", "uv.lock"])
def test_each_detect_file_matches(tmp_path, marker):
    assert detect(make(tmp_path, {marker: ""}))["pack"] == "python"


def test_existing_claude_config_is_reported(tmp_path):
    make(
        tmp_path,
        {
            "pyproject.toml": "",
            "CLAUDE.md": "# x",
            ".claude/settings.json": "{}",
            ".claude/rules/a.md": "",
            ".claude/skills/verify/SKILL.md": "",
        },
    )
    existing = detect(tmp_path)["existing"]
    assert existing["CLAUDE.md"] and existing["settings.json"]
    assert existing["rules"] == ["a.md"]
    assert existing["skills"] == ["verify"]
