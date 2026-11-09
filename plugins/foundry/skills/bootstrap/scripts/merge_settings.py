#!/usr/bin/env python3
"""Merge settings fragments into a Claude Code settings.json without losing anything.

Usage:
    merge_settings.py TARGET_SETTINGS FRAGMENT [FRAGMENT ...] [--dry-run]

Rules:
- Lists (permissions.allow / deny / ask, ...) are unioned. Existing order is kept and new
  items are appended.
- hooks.<Event>: a handler is added to the group with the same matcher (or to a new group)
  unless an identical handler (type + command + args) is already registered there.
- Dicts merge recursively. Existing keys are never deleted.
- A scalar the fragment would change is kept as-is and reported as a conflict on stderr.
- Formatting is stable: an unchanged file is never rewritten, and the existing indent is reused.
--dry-run prints a unified diff (or "no changes") and writes nothing.
Exit codes: 0 ok, 1 invalid input (nothing written).
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import re
import sys
from pathlib import Path


def _handler_key(handler: dict) -> tuple:
    return (
        handler.get("type"),
        handler.get("command"),
        json.dumps(handler.get("args"), sort_keys=True),
        handler.get("url"),
        handler.get("prompt"),
    )


def _merge_hooks(dst: dict, src: dict, conflicts: list[str]) -> None:
    for event, groups in src.items():
        current = dst.setdefault(event, [])
        if not isinstance(current, list) or not isinstance(groups, list):
            conflicts.append(f"hooks.{event}: not a list, left unchanged")
            continue
        for group in groups:
            matcher = group.get("matcher", "")
            same = [g for g in current if isinstance(g, dict) and g.get("matcher", "") == matcher]
            known = {_handler_key(h) for g in same for h in g.get("hooks", [])}
            new = [h for h in group.get("hooks", []) if _handler_key(h) not in known]
            if not new:
                continue
            if same:
                same[0].setdefault("hooks", []).extend(copy.deepcopy(new))
            else:
                fresh = copy.deepcopy({k: v for k, v in group.items() if k != "hooks"})
                fresh["hooks"] = copy.deepcopy(new)
                current.append(fresh)


def _merge_into(dst: dict, src: dict, path: str, conflicts: list[str]) -> None:
    for key, value in src.items():
        here = f"{path}.{key}" if path else key
        if key not in dst:
            dst[key] = copy.deepcopy(value)
            continue
        cur = dst[key]
        if here == "hooks" and isinstance(cur, dict) and isinstance(value, dict):
            _merge_hooks(cur, value, conflicts)
        elif isinstance(cur, dict) and isinstance(value, dict):
            _merge_into(cur, value, here, conflicts)
        elif isinstance(cur, list) and isinstance(value, list):
            cur.extend(copy.deepcopy(v) for v in value if v not in cur)
        elif cur != value:
            conflicts.append(f"{here}: kept existing {cur!r} (fragment wanted {value!r})")


def merge(existing: dict, fragment: dict) -> tuple[dict, list[str]]:
    """Return (merged copy, conflicts). Neither input is modified."""
    result = copy.deepcopy(existing)
    conflicts: list[str] = []
    _merge_into(result, fragment, "", conflicts)
    return result, conflicts


def detect_indent(text: str) -> int | str:
    m = re.search(r"^([ \t]+)\"", text, re.MULTILINE)
    if not m:
        return 2
    ws = m.group(1)
    return "\t" if ws.startswith("\t") else len(ws)


def merge_text(existing_text: str | None, fragments: list[dict]) -> tuple[str, list[str]]:
    """Merge fragments into settings text. Returns (new_text, conflicts).

    Raises ValueError if existing_text isn't a JSON object.
    """
    if existing_text is None or not existing_text.strip():
        existing: dict = {}
        indent: int | str = 2
    else:
        existing = json.loads(existing_text)
        if not isinstance(existing, dict):
            raise ValueError("settings file must contain a JSON object")
        indent = detect_indent(existing_text)
    merged, conflicts = existing, []
    for fragment in fragments:
        merged, more = merge(merged, fragment)
        conflicts.extend(more)
    if existing_text is not None and merged == existing:
        return existing_text, conflicts
    return json.dumps(merged, indent=indent, ensure_ascii=False) + "\n", conflicts


def unified_diff(old: str, new: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{name}", f"b/{name}"
        )
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("target")
    ap.add_argument("fragments", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    target = Path(args.target)
    try:
        old = target.read_text(encoding="utf-8") if target.exists() else None
        frags = [json.loads(Path(f).read_text(encoding="utf-8")) for f in args.fragments]
        new, conflicts = merge_text(old, frags)
    except (OSError, ValueError) as exc:
        print(f"merge_settings: {exc}", file=sys.stderr)
        return 1
    for c in conflicts:
        print(f"merge_settings: conflict: {c}", file=sys.stderr)
    if new == (old or ""):
        print("no changes")
        return 0
    if args.dry_run:
        print(unified_diff(old or "", new, target.as_posix()), end="")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(new.encode("utf-8"))  # LF on every OS; py3.9-safe
    print(f"wrote {target.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
