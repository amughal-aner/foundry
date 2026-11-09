#!/usr/bin/env python3
"""foundry PreToolUse guard: block edits to secrets and VCS internals.

Matcher: Edit|Write|NotebookEdit. Reads the hook JSON on stdin.
- Blocked: exit 2 with a one-line reason on stderr, prefixed "foundry:".
- Allowed: exit 0.
- Internal error: log to stderr and exit 0, so a broken guard never bricks a session.

This is a second layer. Permission deny rules and the sandbox are the real boundary.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys

# --- Rules (data) -----------------------------------------------------------------------------
ENV_ALLOWED = {".env.example", ".env.sample"}  # templates that are safe to edit
BLOCKED_NAME_GLOBS = ["*.pem", "*.key", "id_rsa*"]  # matched against the lower-cased file name
BLOCKED_DIRS = {"secrets": "secrets directory", ".git": "git internals"}  # any path segment
# ----------------------------------------------------------------------------------------------


def _parts(path: str, project_dir: str | None) -> list[str]:
    """Split a path into segments, relative to the project when the path is inside it."""
    p = path.replace("\\", "/")
    if project_dir:
        root = project_dir.replace("\\", "/").rstrip("/")
        if p.lower().startswith(root.lower() + "/"):
            p = p[len(root) + 1 :]
    return [s for s in p.split("/") if s not in ("", ".")]


def block_reason(path: str, project_dir: str | None = None) -> str | None:
    """Return why `path` is protected, or None if edits are allowed."""
    parts = [s.lower() for s in _parts(path, project_dir)]  # case-insensitive filesystems
    if not parts:
        return None
    name = parts[-1]
    if name == ".env" or (name.startswith(".env.") and name not in ENV_ALLOWED):
        return "environment file"
    if any(fnmatch.fnmatchcase(name, g) for g in BLOCKED_NAME_GLOBS):
        return "key or certificate file"
    for seg in parts[:-1]:
        if seg in BLOCKED_DIRS:
            return BLOCKED_DIRS[seg]
    return None


def main() -> int:
    if sys.version_info < (3, 9):  # noqa: UP036 - macOS CLT python3 is 3.9; older: fail open
        return 0
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(path, str) or not path:
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd")
    reason = block_reason(path, project_dir)
    if reason is None:
        return 0
    shown = "/".join(_parts(path, project_dir))
    print(
        f"foundry: blocked edit to {shown} ({reason}). "
        "If the change is really needed, ask the user to make it manually.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - fail open by design
        print(f"foundry: protect_paths internal error, allowing: {exc}", file=sys.stderr)
        sys.exit(0)
