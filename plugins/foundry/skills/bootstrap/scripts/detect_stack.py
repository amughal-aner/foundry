#!/usr/bin/env python3
"""Inventory a repository for /foundry:bootstrap. Read-only. Prints one JSON object.

Usage:
    detect_stack.py [TARGET_DIR]

A pack matches when any file in its pack.json `detect` list exists in TARGET_DIR. For the
python pack, the runner (uv / poetry / hatch / pip) and tools (mypy vs pyright, black, flake8)
are chosen from lockfiles and [tool.*] sections in pyproject.toml. The scan uses section headers,
not a TOML parser, so it works on Python 3.9 and 3.10 (no tomllib).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
PACKS_DIR = PLUGIN_ROOT / "packs"
README_NAMES = ["README.md", "README.rst", "README.txt", "README"]

RUNNER_PREFIX = {"uv": "uv run", "poetry": "poetry run", "hatch": "hatch run", "pip": "python -m"}
RUNNER_INSTALL = {"uv": "uv sync", "poetry": "poetry install", "hatch": "hatch env create"}


def load_packs(packs_dir: Path = PACKS_DIR) -> list[dict]:
    packs = []
    for manifest in sorted(packs_dir.glob("*/pack.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["_dir"] = manifest.parent
        packs.append(data)
    return packs


def tool_sections(pyproject: Path) -> set[str]:
    if not pyproject.is_file():
        return set()
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    return {m.lower() for m in re.findall(r"^\s*\[tool\.([A-Za-z0-9_-]+)", text, re.MULTILINE)}


def python_commands(
    target: Path, defaults: dict[str, str]
) -> tuple[dict[str, str], list[str], list[str]]:
    """Return (commands, tool_hints, notes) for a Python project."""
    has = lambda name: (target / name).exists()  # noqa: E731
    sections = tool_sections(target / "pyproject.toml")
    if has("uv.lock") or "uv" in sections:
        runner = "uv"
    elif has("poetry.lock") or "poetry" in sections:
        runner = "poetry"
    elif "hatch" in sections or has("hatch.toml"):
        runner = "hatch"
    elif has("pyproject.toml"):
        runner = "uv"  # pack default for a plain PEP 621 project
    else:
        runner = "pip"  # requirements*.txt / setup.py / setup.cfg only
    typecheck = "mypy" if ("mypy" in sections or has("mypy.ini") or has(".mypy.ini")) else "pyright"
    black_only = "black" in sections and "ruff" not in sections
    flake8 = has(".flake8") or "flake8" in sections
    hints = sorted(
        {runner, typecheck, "pytest"}
        | ({"black"} if black_only else {"ruff"})
        | ({"flake8"} if flake8 else set())
        | (sections & {"pydantic", "django"})
    )
    notes: list[str] = []
    if has("tox.ini"):
        notes.append(
            "tox.ini present: `tox` may be the full test matrix; commands below run one env."
        )

    if runner == "uv" and typecheck == "pyright" and not black_only and not flake8:
        return dict(defaults), hints, notes

    p = RUNNER_PREFIX[runner]
    if runner == "pip":
        reqs = [r for r in ("requirements.txt", "requirements-dev.txt") if has(r)]
        install = (
            ("python -m pip install " + " ".join(f"-r {r}" for r in reqs))
            if reqs
            else ("python -m pip install -e .")
        )
    else:
        install = RUNNER_INSTALL[runner]
    commands = {
        "install": install,
        "test": f"{p} pytest -q",
        "test_one": f"{p} pytest -q path/to/test_file.py::test_name",
        "lint": f"{p} flake8 ." if flake8 else f"{p} ruff check .",
        "format": f"{p} black ." if black_only else f"{p} ruff format .",
        "format_check": f"{p} black --check ." if black_only else f"{p} ruff format --check .",
        "typecheck": f"{p} mypy ." if typecheck == "mypy" else f"{p} pyright",
    }
    return commands, hints, notes


OVERRIDES: dict[
    str, Callable[[Path, dict[str, str]], tuple[dict[str, str], list[str], list[str]]]
] = {
    "python": python_commands,
}


def _git_repo(target: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return out.returncode == 0 and out.stdout.strip() == "true"


def detect(target: Path, packs_dir: Path = PACKS_DIR) -> dict:
    target = target.resolve()
    result: dict = {
        "target": target.as_posix(),
        "git_repo": _git_repo(target),
        "pack": None,
        "matched_files": [],
        "tool_hints": [],
        "commands": {},
        "notes": [],
    }
    for pack in load_packs(packs_dir):
        matched = [f for f in pack.get("detect", []) if (target / f).exists()]
        if not matched:
            continue
        defaults = dict(pack.get("defaults", {}))
        override = OVERRIDES.get(pack["name"])
        commands, hints, notes = override(target, defaults) if override else (defaults, [], [])
        result.update(
            pack=pack["name"],
            matched_files=matched,
            tool_hints=hints,
            commands=commands,
            notes=notes,
        )
        break
    claude = target / ".claude"
    result["existing"] = {
        "readme": next((n for n in README_NAMES if (target / n).is_file()), None),
        "CLAUDE.md": (target / "CLAUDE.md").is_file() or (claude / "CLAUDE.md").is_file(),
        "settings.json": (claude / "settings.json").is_file(),
        "rules": sorted(p.name for p in (claude / "rules").glob("*.md")),
        "skills": sorted(p.parent.name for p in (claude / "skills").glob("*/SKILL.md")),
        "foundry.json": (claude / "foundry.json").is_file(),
    }
    if result["pack"] is None:
        result["notes"].append("No stack pack matched: generic CLAUDE.md and guard settings only.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    target = Path(args[0]) if args else Path.cwd()
    if not target.is_dir():
        print(f"detect_stack: not a directory: {target}", file=sys.stderr)
        return 1
    print(json.dumps(detect(target), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
