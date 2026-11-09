"""Enforce plan.md §2 design principles on the shipped plugin files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import PACK_PY, PLUGIN

SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
AGENTS = sorted((PLUGIN / "agents").glob("**/*.md")) if (PLUGIN / "agents").exists() else []
SIDE_EFFECT_SKILLS = {"bootstrap", "plan-feature", "audit", "commit"}
FORBIDDEN_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode", "initialPrompt"}
RESERVED_SKILL_NAMES = {"code-review", "verify", "simplify"}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path}: frontmatter must open on line 1"
    block = text.split("---\n", 2)[1]
    fields = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            value = m.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[m.group(1)] = value
    return fields


def ids(paths):
    return [p.relative_to(PLUGIN).as_posix() for p in paths]


@pytest.mark.parametrize("path", SKILLS + AGENTS, ids=ids(SKILLS + AGENTS))
def test_description_is_short_and_has_use_when(path):
    desc = frontmatter(path).get("description", "")
    assert 0 < len(desc) <= 200, f"{len(desc)} chars"
    assert "Use when" in desc or "use when" in desc or "Use proactively" in desc
    assert "<" not in desc and ">" not in desc


@pytest.mark.parametrize("path", SKILLS, ids=ids(SKILLS))
def test_skill_md_at_most_150_lines(path):
    assert path.read_text(encoding="utf-8").count("\n") <= 150


@pytest.mark.parametrize("path", SKILLS, ids=ids(SKILLS))
def test_side_effect_skills_disable_model_invocation(path):
    fm = frontmatter(path)
    name = fm.get("name", path.parent.name)
    assert name not in RESERVED_SKILL_NAMES
    if name in SIDE_EFFECT_SKILLS:
        assert fm.get("disable-model-invocation") == "true"


@pytest.mark.parametrize("path", AGENTS, ids=ids(AGENTS))
def test_agents_avoid_ignored_fields(path):
    assert not FORBIDDEN_AGENT_FIELDS & set(frontmatter(path))


def test_verify_template_stays_model_invocable():
    fm = frontmatter(PACK_PY / "skills" / "verify" / "SKILL.md")
    assert fm["name"] == "verify"
    assert "disable-model-invocation" not in fm
    assert len(fm["description"]) <= 200


@pytest.mark.parametrize(("rule", "limit"), [("python.md", 25), ("testing.md", 20)])
def test_rule_files_are_short_and_path_scoped(rule, limit):
    path = PACK_PY / "rules" / rule
    assert path.read_text(encoding="utf-8").count("\n") <= limit
    assert "paths" in frontmatter(path)


def test_hooks_json_uses_launcher_timeouts_and_fail_open():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for event, groups in hooks.items():
        for group in groups:
            for handler in group["hooks"]:
                assert handler["timeout"] <= 10
                assert '"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/py"' in handler["command"]
                if event == "PreToolUse":
                    assert handler["onFailure"] == "continue"


def test_shell_scripts_have_lf_line_endings():
    for script in [PLUGIN / "hooks" / "scripts" / "py"]:
        assert b"\r\n" not in script.read_bytes()
