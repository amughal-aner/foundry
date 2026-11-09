from __future__ import annotations

import json
import shutil

import pytest
from apply_bootstrap import BootstrapError, command_prefix, load_answers, main, plan
from conftest import FIXTURE, PLUGIN

ANSWERS = {
    "name": "sample-app",
    "summary": "Internal project tracker; finance uses its monthly usage reports. Python 3.10+, "
    "SQLite, stdlib only.",
    "pack": "python",
    "conventions": ["Service logic lives in api.py; the CLI stays thin."],
    "gotchas": ["Reports read the SQLite file directly."],
    "sensitive": ["auth", "secrets"],
}


@pytest.fixture
def project(tmp_path):
    dest = tmp_path / "proj"
    shutil.copytree(FIXTURE, dest, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.db"))
    (dest / ".claude").mkdir()
    (dest / ".claude" / "foundry.json").write_text(json.dumps(ANSWERS), encoding="utf-8")
    return dest


def run(project, *extra):
    return main(["--target", str(project), *extra])


def actions(project):
    answers = load_answers(project / ".claude" / "foundry.json", PLUGIN / "packs")
    items, notes = plan(project, answers)
    return {i.path: i.action for i in items}, notes


def test_dry_run_writes_nothing(project, capsys):
    before = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))
    assert run(project, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "create     CLAUDE.md" in out
    assert "replaces Claude Code's bundled" in out  # P-3 warning
    after = sorted(p.relative_to(project).as_posix() for p in project.rglob("*"))
    assert after == before


def test_apply_creates_expected_files(project):
    assert run(project) == 0
    for rel in [
        "CLAUDE.md",
        ".claude/settings.json",
        ".claude/rules/python.md",
        ".claude/rules/testing.md",
        ".claude/hooks/ruff_on_edit.py",
        ".claude/hooks/py",
        ".claude/skills/verify/SKILL.md",
        "docs/plans/.gitkeep",
        "docs/adr/.gitkeep",
    ]:
        assert (project / rel).exists(), rel
    claude_md = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude_md.count("\n") <= 80
    assert "# Project: sample-app" in claude_md
    assert "`uv run pytest -q`" in claude_md
    assert "## Security notes" in claude_md
    assert "{{" not in claude_md
    verify = (project / ".claude/skills/verify/SKILL.md").read_text(encoding="utf-8")
    assert "`uv run ruff format --check .`" in verify
    assert "allowed-tools: Bash(uv run ruff *)" in verify
    assert "disable-model-invocation" not in verify
    settings = json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))
    assert "Read(./.env)" in settings["permissions"]["deny"]
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Edit|Write"
    gitignore = (project / ".gitignore").read_text(encoding="utf-8")
    assert "CLAUDE.local.md" in gitignore and ".claude/settings.local.json" in gitignore


def test_second_run_changes_nothing(project):
    assert run(project) == 0
    snapshot = {p: p.read_bytes() for p in project.rglob("*") if p.is_file()}
    found, _ = actions(project)
    assert set(found.values()) == {"unchanged"}, found
    assert run(project) == 0
    assert {p: p.read_bytes() for p in project.rglob("*") if p.is_file()} == snapshot


def test_existing_file_is_not_overwritten_without_approval(project):
    (project / "CLAUDE.md").write_text("# Hand-written\n", encoding="utf-8")
    found, notes = actions(project)
    assert found["CLAUDE.md"] == "update"
    assert any("--approve" in n for n in notes)
    assert run(project) == 0
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == "# Hand-written\n"
    assert run(project, "--approve", "CLAUDE.md") == 0
    assert (project / "CLAUDE.md").read_text(encoding="utf-8").startswith("<!-- Generated")


def test_existing_settings_are_merged_not_replaced(project):
    settings = project / ".claude" / "settings.json"
    settings.write_text(
        json.dumps({"model": "opus", "permissions": {"allow": ["Bash(make *)"]}}), encoding="utf-8"
    )
    assert run(project) == 0
    merged = json.loads(settings.read_text(encoding="utf-8"))
    assert merged["model"] == "opus"
    assert merged["permissions"]["allow"][0] == "Bash(make *)"


def test_existing_gitignore_gets_appended(project):
    (project / ".gitignore").write_text(".venv/\nCLAUDE.local.md", encoding="utf-8")
    assert run(project) == 0
    assert (project / ".gitignore").read_text(encoding="utf-8") == (
        ".venv/\nCLAUDE.local.md\n.claude/settings.local.json\n"
    )


def test_no_pack_writes_generic_files_only(tmp_path):
    (tmp_path / ".claude").mkdir()
    answers = {
        "name": "web",
        "summary": "A static site.",
        "pack": None,
        "commands": {"test": "npm test"},
    }
    (tmp_path / ".claude" / "foundry.json").write_text(json.dumps(answers), encoding="utf-8")
    assert main(["--target", str(tmp_path)]) == 0
    assert (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".claude" / "rules").exists()
    assert not (tmp_path / ".claude" / "skills").exists()
    settings = json.loads((tmp_path / ".claude/settings.json").read_text(encoding="utf-8"))
    assert "hooks" not in settings
    assert "Bash(rm -rf *)" in settings["permissions"]["deny"]
    assert "Test all: `npm test`" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")


def test_non_uv_runner_drops_uv_rules(project):
    commands = {
        "install": "poetry install",
        "test": "poetry run pytest -q",
        "test_one": "poetry run pytest -q x.py::t",
        "lint": "poetry run ruff check .",
        "format": "poetry run ruff format .",
        "format_check": "poetry run ruff format --check .",
        "typecheck": "poetry run pyright",
    }
    answers = dict(ANSWERS, commands=commands)
    (project / ".claude" / "foundry.json").write_text(json.dumps(answers), encoding="utf-8")
    assert run(project) == 0
    allow = json.loads((project / ".claude/settings.json").read_text(encoding="utf-8"))[
        "permissions"
    ]["allow"]
    assert not any("(uv " in r for r in allow)
    assert "Bash(poetry run pytest *)" in allow and "Bash(poetry install *)" in allow


def test_oversized_claude_md_is_refused(project):
    answers = dict(ANSWERS, gotchas=[f"gotcha {i}" for i in range(80)])
    (project / ".claude" / "foundry.json").write_text(json.dumps(answers), encoding="utf-8")
    with pytest.raises(BootstrapError, match="80"):
        plan(project, load_answers(project / ".claude" / "foundry.json", PLUGIN / "packs"))


def test_missing_required_answer_is_refused(project):
    (project / ".claude" / "foundry.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")
    assert run(project, "--dry-run") == 1


@pytest.mark.parametrize(
    ("cmd", "prefix"),
    [
        ("uv run pytest -q", "uv run pytest"),
        ("uv sync", "uv sync"),
        ("python -m pip install -r r.txt", "python -m pip"),
        ("pytest -q", "pytest"),
        ("make test", "make test"),
    ],
)
def test_command_prefix(cmd, prefix):
    assert command_prefix(cmd) == prefix
