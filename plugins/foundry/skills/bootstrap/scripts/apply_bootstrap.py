#!/usr/bin/env python3
"""Plan and apply the files /foundry:bootstrap writes into a project. Deterministic and idempotent.

Usage:
    apply_bootstrap.py --target DIR [--answers FILE] --dry-run
    apply_bootstrap.py --target DIR [--answers FILE] [--approve REL_PATH ...] [--approve-all]

--answers defaults to DIR/.claude/foundry.json (schema: skills/bootstrap/reference.md).

Actions per file:
  create     file is missing                         -> written
  unchanged  file already has the planned content    -> nothing
  merge      .claude/settings.json additive merge    -> written (never deletes keys)
  append     .gitignore missing lines                 -> appended
  update     existing file differs                   -> written ONLY if approved
                                                        (--approve PATH or --approve-all)
--dry-run prints the plan and every diff, and writes nothing. Exit codes: 0 ok, 1 bad input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_settings import merge_text, unified_diff  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = PLUGIN_ROOT / "templates"
LAUNCHER = PLUGIN_ROOT / "hooks" / "scripts" / "py"
MAX_CLAUDE_MD_LINES = 80
GITIGNORE_LINES = ["CLAUDE.local.md", ".claude/settings.local.json"]
PACK_COMMAND_KEYS = ["install", "test", "test_one", "lint", "format", "format_check", "typecheck"]
VERIFY_KEYS = ["format_check", "lint", "typecheck", "test"]
COMMAND_LABELS = {
    "install": "Install",
    "test": "Test all",
    "test_one": "Test one",
    "lint": "Lint",
    "format": "Format",
    "typecheck": "Type-check",
}
KNOWN_TOOLS = {"pytest", "ruff", "pyright", "mypy", "black", "flake8", "tox", "isort"}
RUNNERS = {
    ("uv", "run"),
    ("poetry", "run"),
    ("hatch", "run"),
    ("pipenv", "run"),
    ("python", "-m"),
    ("python3", "-m"),
}
SAFE_INSTALL_PREFIXES = {"uv sync", "poetry install", "hatch env"}
VERIFY_NOTE = (
    "Creating .claude/skills/verify/SKILL.md: in this repo it replaces Claude Code's bundled "
    "/verify (which launches and drives the app) with format/lint/type/test checks."
)


@dataclass
class Planned:
    path: str
    action: str
    content: str
    old: str | None = None
    executable: bool = False

    @property
    def diff(self) -> str:
        if self.action in ("update", "merge", "append"):
            return unified_diff(self.old or "", self.content, self.path)
        return ""


class BootstrapError(Exception):
    pass


# --- helpers ------------------------------------------------------------------------------------


def command_prefix(cmd: str) -> str:
    t = cmd.split()
    if len(t) >= 3 and (t[0], t[1]) in RUNNERS:
        return " ".join(t[:3])
    if t and t[0] in KNOWN_TOOLS:
        return t[0]
    return " ".join(t[:2])


def tool_rules(prefixes: list[str]) -> list[str]:
    rules: list[str] = []
    for p in prefixes:
        for tool in ("Bash", "PowerShell"):
            r = f"{tool}({p} *)"
            if r not in rules:
                rules.append(r)
    return rules


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    leftover = re.findall(r"\{\{[a-z_]+\}\}", out)
    if leftover:
        raise BootstrapError(f"unfilled placeholders: {sorted(set(leftover))}")
    return out


def bullets(items: list[str] | None, empty: str) -> str:
    items = [i.strip() for i in (items or []) if i and i.strip()]
    return "\n".join(f"- {i}" for i in items) if items else f"- {empty}"


def tidy(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n"))
    return text.strip() + "\n"


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


# --- planning -----------------------------------------------------------------------------------


def load_answers(path: Path, packs_dir: Path) -> dict:
    try:
        answers = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BootstrapError(f"cannot read answers {path}: {exc}") from exc
    for key in ("name", "summary"):
        if not isinstance(answers.get(key), str) or not answers[key].strip():
            raise BootstrapError(f"answers.{key} must be a non-empty string")
    pack = answers.get("pack")
    if pack is not None and not (packs_dir / str(pack) / "pack.json").is_file():
        raise BootstrapError(f"unknown pack {pack!r}")
    commands = answers.setdefault("commands", {})
    if pack:
        defaults = json.loads((packs_dir / pack / "pack.json").read_text(encoding="utf-8"))[
            "defaults"
        ]
        for key in PACK_COMMAND_KEYS:
            commands.setdefault(key, defaults[key])
    return answers


def render_claude_md(answers: dict, pack_dir: Path | None) -> str:
    commands = answers["commands"]
    if pack_dir is not None:
        fragment = (pack_dir / "claude-md.fragment.md").read_text(encoding="utf-8")
        commands_md = render(fragment, commands).strip()
    else:
        lines = [
            f"- {label}: `{commands[k]}`" for k, label in COMMAND_LABELS.items() if commands.get(k)
        ]
        commands_md = "## Commands\n" + (
            "\n".join(lines) or "- None recorded yet. Add install/test/lint here."
        )
    security = ""
    if answers.get("sensitive"):
        security = "\n## Security notes\n" + bullets(
            [f"Handles: {', '.join(answers['sensitive'])}."]
            + list(answers.get("security_notes") or [])
            + [
                "Never log secrets, tokens or personal data.",
                "Changes to auth, payments or data handling get a "
                "`/foundry:threat-model` pass first.",
            ],
            "",
        )
    text = tidy(
        render(
            (TEMPLATES / "CLAUDE.md.tmpl").read_text(encoding="utf-8"),
            {
                "name": answers["name"].strip(),
                "summary": answers["summary"].strip(),
                "commands": commands_md,
                "conventions": bullets(
                    answers.get("conventions"), "None beyond language defaults."
                ),
                "gotchas": bullets(answers.get("gotchas"), "None recorded yet."),
                "security": security,
            },
        )
    )
    n = text.count("\n")
    if n > MAX_CLAUDE_MD_LINES:
        raise BootstrapError(
            f"CLAUDE.md would be {n} lines (max {MAX_CLAUDE_MD_LINES}); shorten the answers"
        )
    return text


def settings_fragments(answers: dict, pack_dir: Path | None, plugin_root: Path) -> list[dict]:
    frags = [json.loads((TEMPLATES / "settings.base.json").read_text(encoding="utf-8"))]
    commands = answers["commands"]
    if pack_dir is not None:
        pack = json.loads((pack_dir / "settings.json").read_text(encoding="utf-8"))
        allow = pack.get("permissions", {}).get("allow", [])
        if not any(c.startswith("uv ") for c in commands.values()):
            allow = [r for r in allow if "(uv " not in r]
        prefixes = [command_prefix(commands[k]) for k in VERIFY_KEYS if commands.get(k)]
        install = commands.get("install", "")
        if any(install.startswith(s) for s in SAFE_INSTALL_PREFIXES):
            prefixes.insert(0, command_prefix(install))
        allow += [r for r in tool_rules(prefixes) if r not in allow]
        pack.setdefault("permissions", {})["allow"] = allow
        frags.append(pack)
    config = json.loads((plugin_root / "foundry.config.json").read_text(encoding="utf-8"))
    source = config.get("marketplace_source")
    if source:
        market, plugin = (
            config.get("marketplace_name", "foundry"),
            config.get("plugin_name", "foundry"),
        )
        frags.append(
            {
                "extraKnownMarketplaces": {market: {"source": source}},
                "enabledPlugins": {f"{plugin}@{market}": True},
            }
        )
    return frags


def _file(target: Path, rel: str, content: str, executable: bool = False) -> Planned:
    old = read_text(target / rel)
    if old is None:
        return Planned(rel, "create", content, None, executable)
    if old.replace("\r\n", "\n") == content:
        return Planned(rel, "unchanged", content, old, executable)
    return Planned(rel, "update", content, old, executable)


def plan(
    target: Path, answers: dict, plugin_root: Path = PLUGIN_ROOT
) -> tuple[list[Planned], list[str]]:
    packs_dir = plugin_root / "packs"
    pack_dir = packs_dir / answers["pack"] if answers.get("pack") else None
    items: list[Planned] = [_file(target, "CLAUDE.md", render_claude_md(answers, pack_dir))]
    notes: list[str] = []

    rel = ".claude/settings.json"
    old = read_text(target / rel)
    try:
        new, conflicts = merge_text(old, settings_fragments(answers, pack_dir, plugin_root))
    except ValueError as exc:
        raise BootstrapError(f"{rel} is not valid JSON ({exc}); fix it first") from exc
    notes += [f"settings conflict: {c}" for c in conflicts]
    action = "create" if old is None else ("unchanged" if new == old else "merge")
    items.append(Planned(rel, action, new, old))

    if pack_dir is not None:
        for rule in sorted((pack_dir / "rules").glob("*.md")):
            items.append(
                _file(target, f".claude/rules/{rule.name}", rule.read_text(encoding="utf-8"))
            )
        hooks = sorted(
            p
            for p in (pack_dir / "hooks").glob("*")
            if p.is_file() and not p.name.startswith(".") and p.suffix != ".pyc"
        )
        for hook in hooks:
            items.append(
                _file(target, f".claude/hooks/{hook.name}", hook.read_text(encoding="utf-8"), True)
            )
        if hooks:
            items.append(
                _file(target, ".claude/hooks/py", LAUNCHER.read_text(encoding="utf-8"), True)
            )
        commands = answers["commands"]
        values = dict(
            commands,
            allowed_tools=" ".join(tool_rules([command_prefix(commands[k]) for k in VERIFY_KEYS])),
        )
        for skill in sorted((pack_dir / "skills").glob("*/SKILL.md")):
            rel = f".claude/skills/{skill.parent.name}/SKILL.md"
            item = _file(target, rel, render(skill.read_text(encoding="utf-8"), values))
            items.append(item)
            if skill.parent.name == "verify" and item.action == "create":
                notes.append(VERIFY_NOTE)

    for keep in ("docs/plans/.gitkeep", "docs/adr/.gitkeep"):
        items.append(_file(target, keep, ""))

    old = read_text(target / ".gitignore")
    present = {ln.strip() for ln in (old or "").splitlines()}
    missing = [ln for ln in GITIGNORE_LINES if ln not in present]
    if old is None:
        items.append(Planned(".gitignore", "create", "\n".join(GITIGNORE_LINES) + "\n"))
    elif missing:
        base = old if old.endswith("\n") or not old else old + "\n"
        items.append(Planned(".gitignore", "append", base + "\n".join(missing) + "\n", old))
    else:
        items.append(Planned(".gitignore", "unchanged", old, old))

    update_count = sum(i.action == "update" for i in items)
    if update_count:
        notes.append(
            f"{update_count} existing file(s) differ. "
            "They are only overwritten with --approve PATH."
        )
    return items, notes


# --- apply / report -----------------------------------------------------------------------------


def apply(
    target: Path, items: list[Planned], approve: set[str], approve_all: bool
) -> list[tuple[str, str]]:
    results = []
    for item in items:
        if item.action == "unchanged":
            results.append((item.path, "unchanged"))
            continue
        if item.action == "update" and not (approve_all or item.path in approve):
            results.append((item.path, "skipped (not approved)"))
            continue
        dest = target / item.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(item.content.encode("utf-8"))  # LF on every OS; py3.9-safe
        if item.executable and os.name != "nt":
            dest.chmod(0o755)
        results.append((item.path, "wrote" if item.action != "create" else "created"))
    return results


def report(target: Path, items: list[Planned], notes: list[str]) -> str:
    out = [f"foundry bootstrap plan for {target.as_posix()} (dry run, nothing written)"]
    out += [f"  {i.action:<9}  {i.path}" for i in items]
    if notes:
        out += ["", "Notes:"] + [f"  - {n}" for n in notes]
    diffs = [i.diff for i in items if i.diff]
    if diffs:
        out += ["", "--- diffs ---", *diffs]
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--answers")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--approve", action="append", default=[], metavar="REL_PATH")
    ap.add_argument("--approve-all", action="store_true")
    args = ap.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"apply_bootstrap: not a directory: {target}", file=sys.stderr)
        return 1
    answers_path = Path(args.answers) if args.answers else target / ".claude" / "foundry.json"
    try:
        answers = load_answers(answers_path, PLUGIN_ROOT / "packs")
        items, notes = plan(target, answers)
    except BootstrapError as exc:
        print(f"apply_bootstrap: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(report(target, items, notes), end="")
        return 0
    approve = {a.replace("\\", "/") for a in args.approve}
    for path, outcome in apply(target, items, approve, args.approve_all):
        print(f"  {outcome:<22}  {path}")
    for n in notes:
        print(f"note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
