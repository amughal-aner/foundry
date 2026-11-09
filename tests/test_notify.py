from __future__ import annotations

import json

from conftest import HOOK_SCRIPTS

SCRIPT = HOOK_SCRIPTS / "notify.py"


def test_emits_osc9_terminal_sequence(hook):
    result = hook(SCRIPT, {"message": "Claude needs your permission", "title": "Permission"})
    assert result.returncode == 0
    seq = json.loads(result.stdout)["terminalSequence"]
    assert seq == "\x1b]9;Permission: Claude needs your permission\x07"


def test_strips_control_characters(hook):
    result = hook(SCRIPT, {"message": "a\x1b]0;evil\x07b\nc"})
    seq = json.loads(result.stdout)["terminalSequence"]
    body = seq[len("\x1b]9;") : -1]
    assert all(ch >= " " for ch in body)


def test_bad_input_still_exits_zero(hook):
    result = hook(SCRIPT, "not json")
    assert result.returncode == 0
    assert "terminalSequence" in result.stdout
