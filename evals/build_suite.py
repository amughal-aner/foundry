#!/usr/bin/env python3
"""Generate the `claude plugin eval` suite under plugins/foundry/evals/ (build-plan.md §3.2). Stdlib.

Usage:
    python evals/build_suite.py          # (re)write every case directory
    python evals/build_suite.py --check  # exit 1 if the checked-in suite is out of date

The answer-key patterns come from evals/answer-keys/sample-py-app.md (the "Hit patterns" block),
so the key stays the single source of truth. Each case:
  prompt.md        plain-language request (identical in both arms) naming the exact output path
  case.yaml        schema 1.1 + scaffold_script
  scaffold.sh      copies fixtures/sample-py-app into the empty workspace and commits it
  graders/*.md     file_exists + one regex per expected issue + a skill-fired indicator
Run with: claude plugin eval plugins/foundry --scaffold --allow-tools Write Edit [--tag ...]
(cases tagged needs-bash also need "Bash(git *)" and an OS sandbox: macOS/Linux/WSL2).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUITE = REPO / "plugins" / "foundry" / "evals"
ANSWER_KEY = REPO / "evals" / "answer-keys" / "sample-py-app.md"
NO_QUESTIONS = "There is no user to answer questions: make reasonable assumptions and state them."
SKILL_MATCH = '"skill"\\s*:\\s*"(?:[\\w-]+:)?{skill}"'  # docs: plugin-evals "skill-fired" grader

# (case id, skill, output path or None for reply-only, expected issue ids, prompt, extra scaffold)
CASES: list[tuple[str, str, str | None, list[str], str, str]] = [
    (
        "sd-reporting",
        "system-design",
        "docs/adr/0001-reporting-structure.md",
        ["5a", "5b"],
        "The reporting code in this repo has become hard to change. Analyze the design and write an "
        "architecture decision record at docs/adr/0001-reporting-structure.md recommending how to "
        "restructure it.",
        "",
    ),
    (
        "sd-boundaries",
        "system-design",
        "docs/adr/0001-module-boundaries.md",
        ["5b", "5a"],
        "Decide how the modules in src/sample_app should depend on each other going forward, and "
        "record the decision as an ADR at docs/adr/0001-module-boundaries.md.",
        "",
    ),
    (
        "sd-extensibility",
        "system-design",
        "docs/adr/0001-reporting-extensibility.md",
        ["5a"],
        "We want to add a second report format and a nightly job that pushes usage to billing. "
        "Write an ADR at docs/adr/0001-reporting-extensibility.md on how to structure the code for "
        "that.",
        "",
    ),
    (
        "tm-repo",
        "threat-model",
        "docs/security/threat-model-repo.md",
        ["1", "2", "3"],
        "Do a threat model of this repository and write it to docs/security/threat-model-repo.md.",
        "",
    ),
    (
        "tm-service",
        "threat-model",
        "docs/security/threat-model-service.md",
        ["1", "2", "3"],
        "Threat-model the service and storage layers (src/sample_app/api.py and db.py) and save the "
        "result to docs/security/threat-model-service.md.",
        "",
    ),
    (
        "tm-cli-exposure",
        "threat-model",
        "docs/security/threat-model-cli.md",
        ["1", "3"],
        "We're about to let other teams run this tool's search and delete commands. Assess the "
        "security risks first: write a STRIDE threat model to docs/security/threat-model-cli.md.",
        "",
    ),
    (
        "pb-cli",
        "product-brief",
        "docs/product/cli-brief.md",
        ["6a", "6b"],
        "Write a product/UX brief for this tool's command-line interface at "
        "docs/product/cli-brief.md.",
        "",
    ),
    (
        "pb-projects",
        "product-brief",
        "docs/product/projects-brief.md",
        ["6b", "6a"],
        "Users keep complaining about the project management commands. Review them from a UX angle "
        "and write a brief to docs/product/projects-brief.md.",
        "",
    ),
    (
        "pb-report",
        "product-brief",
        "docs/product/report-brief.md",
        ["6a"],
        "Write a product brief for the monthly usage report experience (running the report command "
        "and reading its output) at docs/product/report-brief.md.",
        "",
    ),
    (
        "rd-page-count",
        "review-diff",
        None,
        ["4"],
        "Review my uncommitted changes before I commit them.",
        "cat >> src/sample_app/reports.py <<'PY'\n\n\ndef page_count(total: int, page_size: int) -> int:\n"
        "    return max(1, -(-total // page_size))\nPY\n",
    ),
    (
        "rd-paginate-all",
        "review-diff",
        None,
        ["4"],
        "Please review the change I just made to the reports module.",
        "cat >> src/sample_app/reports.py <<'PY'\n\n\ndef paginate_all(items: list, page_size: int) -> list:\n"
        "    pages, page = [], 1\n    while chunk := paginate(items, page, page_size):\n"
        "        pages.append(chunk)\n        page += 1\n    return pages\nPY\n",
    ),
    (
        "rd-search-limit",
        "review-diff",
        None,
        ["1"],
        "Code review my working-tree changes, please.",
        "cat >> src/sample_app/db.py <<'PY'\n\n\ndef find_users_limited(conn, name_fragment, limit=20):\n"
        '    query = (\n        "SELECT id, name, role FROM users "\n'
        "        f\"WHERE name LIKE '%{name_fragment}%' LIMIT {limit}\"\n    )\n"
        "    return conn.execute(query).fetchall()\nPY\n",
    ),
]

SCAFFOLD = """#!/bin/bash
# Generated by evals/build_suite.py. Copies the fixture into the empty eval workspace.
set -euo pipefail
here="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
src="$here/../../../../fixtures/sample-py-app"
tar -C "$src" --exclude=.venv --exclude=.pytest_cache --exclude=__pycache__ --exclude='*.db' \\
  -cf - . | tar -xf -
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm init
{extra}"""


def load_patterns(path: Path = ANSWER_KEY) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    block = text.split("## Hit patterns", 1)[1].split("```text", 1)[1].split("```", 1)[0]
    patterns = {}
    for line in block.strip().splitlines():
        key, pattern = line.split(None, 1)
        re.compile(pattern)  # must also be valid as a Python regex (close enough to JS here)
        patterns[key] = pattern.strip()
    return patterns


def _yaml_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def render_case(case: tuple, patterns: dict[str, str]) -> dict[str, str]:
    cid, skill, out, issues, prompt, extra = case
    needs_bash = skill == "review-diff"
    tags = [skill] + (["needs-bash"] if needs_bash else [])
    files = {
        "prompt.md": "\n".join(
            [
                "---",
                f"description: {_yaml_str(f'{skill}: expects answer-key issues ' + ', '.join(issues))}",
                f"tags: [{', '.join(tags)}]",
                "max_turns: 40",
                "timeout_seconds: 900",
                "allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]",
                f"append_system_prompt: {_yaml_str(NO_QUESTIONS)}",
                "---",
                "",
                prompt,
                "",
            ]
        ),
        "case.yaml": f'schema_version: "1.1"\nname: {cid}\ncontext:\n  scaffold_script: scaffold.sh\n',
        "scaffold.sh": SCAFFOLD.format(extra=extra),
        "graders/skill-fired.md": "\n".join(
            [
                "---",
                "type: tool_used",
                "tool: Skill",
                "input_match: " + _yaml_str(SKILL_MATCH.format(skill=skill)),
                "---",
                "",
            ]
        ),
    }
    if out:
        files["graders/output-file.md"] = f"---\ntype: file_exists\npath: {out}\n---\n"
    target = f"target: {{ source: file, path: {out} }}" if out else "target: last_message"
    for issue in issues:
        files[f"graders/hit-{issue}.md"] = "\n".join(
            [
                "---",
                "type: regex",
                target,
                "flags: i",
                f"pattern: {_yaml_str(patterns[issue])}",
                "---",
                "",
            ]
        )
    return files


def build() -> dict[Path, str]:
    patterns = load_patterns()
    out: dict[Path, str] = {}
    for case in CASES:
        for rel, content in render_case(case, patterns).items():
            out[SUITE / case[0] / rel] = content
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    planned = build()
    stale = [
        p for p, c in planned.items() if not p.is_file() or p.read_bytes() != c.encode("utf-8")
    ]
    if "--check" in args:
        for p in stale:
            print(f"out of date: {p.relative_to(REPO).as_posix()}")
        return 1 if stale else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(planned[p].encode("utf-8"))
    print(
        f"{len(CASES)} cases, {len(stale)} file(s) written under {SUITE.relative_to(REPO).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
