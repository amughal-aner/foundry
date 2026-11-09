from __future__ import annotations

import json

from conftest import PACK_PY
from merge_settings import main, merge, merge_text

FRAGMENT = json.loads((PACK_PY / "settings.json").read_text(encoding="utf-8"))


def test_empty_target_gets_fragment_verbatim():
    text, conflicts = merge_text(None, [FRAGMENT])
    assert json.loads(text) == FRAGMENT
    assert conflicts == []
    assert text.endswith("\n")


def test_existing_target_keeps_keys_and_unions_lists():
    existing = {
        "model": "sonnet",
        "permissions": {"allow": ["Bash(make *)", "Bash(git status *)"], "deny": ["Read(./x)"]},
        "env": {"FOO": "1"},
    }
    merged, conflicts = merge(existing, FRAGMENT)
    assert merged["model"] == "sonnet"
    assert merged["env"] == {"FOO": "1"}
    allow = merged["permissions"]["allow"]
    assert allow[:2] == ["Bash(make *)", "Bash(git status *)"]  # existing order first
    assert allow.count("Bash(git status *)") == 1
    assert "Bash(uv run pytest *)" in allow
    assert "Read(./x)" in merged["permissions"]["deny"]
    assert "Read(./.env)" in merged["permissions"]["deny"]
    assert conflicts == []
    assert existing["permissions"]["allow"] == [
        "Bash(make *)",
        "Bash(git status *)",
    ]  # input untouched


def test_scalar_conflict_keeps_existing_and_reports():
    merged, conflicts = merge({"$schema": "custom"}, {"$schema": "other"})
    assert merged["$schema"] == "custom"
    assert len(conflicts) == 1


def test_duplicate_hooks_are_not_added_twice():
    once, _ = merge({}, FRAGMENT)
    twice, _ = merge(once, FRAGMENT)
    groups = twice["hooks"]["PostToolUse"]
    assert len(groups) == 1
    assert len(groups[0]["hooks"]) == 1


def test_new_handler_joins_existing_group_with_same_matcher():
    existing = {
        "hooks": {
            "PostToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "prettier"}]}
            ]
        }
    }
    merged, _ = merge(existing, FRAGMENT)
    handlers = merged["hooks"]["PostToolUse"][0]["hooks"]
    assert [h["command"] for h in handlers][0] == "prettier"
    assert len(handlers) == 2


def test_idempotent_text_is_byte_identical():
    first, _ = merge_text(None, [FRAGMENT])
    second, _ = merge_text(first, [FRAGMENT])
    assert second == first


def test_unchanged_file_keeps_its_formatting():
    custom = '{\n    "permissions": {\n        "allow": ["Bash(uv sync *)"]\n    }\n}\n'
    text, _ = merge_text(custom, [{"permissions": {"allow": ["Bash(uv sync *)"]}}])
    assert text == custom


def test_changed_file_reuses_existing_indent():
    custom = '{\n    "model": "opus"\n}\n'
    text, _ = merge_text(custom, [{"env": {"A": "1"}}])
    assert '\n    "env": {' in text


def test_dry_run_prints_diff_and_writes_nothing(tmp_path, capsys):
    target = tmp_path / ".claude" / "settings.json"
    frag = tmp_path / "frag.json"
    frag.write_text(json.dumps(FRAGMENT), encoding="utf-8")
    assert main([str(target), str(frag), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("--- a/")
    assert '+    "allow": [' in out
    assert not target.exists()


def test_cli_write_then_rerun_reports_no_changes(tmp_path, capsys):
    target = tmp_path / ".claude" / "settings.json"
    frag = tmp_path / "frag.json"
    frag.write_text(json.dumps(FRAGMENT), encoding="utf-8")
    assert main([str(target), str(frag)]) == 0
    first = target.read_bytes()
    capsys.readouterr()
    assert main([str(target), str(frag)]) == 0
    assert capsys.readouterr().out.strip() == "no changes"
    assert target.read_bytes() == first


def test_invalid_existing_json_is_refused(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text("{ not json", encoding="utf-8")
    frag = tmp_path / "frag.json"
    frag.write_text("{}", encoding="utf-8")
    assert main([str(target), str(frag)]) == 1
    assert target.read_text(encoding="utf-8") == "{ not json"
