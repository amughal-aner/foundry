#!/usr/bin/env python3
"""foundry Notification hook: desktop alert when Claude Code needs attention.

- All OSes: print a JSON `terminalSequence` (OSC 9). Claude Code writes it to the terminal, so
  Windows Terminal, iTerm2 and WezTerm show a notification. Hooks have no /dev/tty.
- macOS: also `osascript -e 'display notification ...'` (non-blocking).
- Linux: also `notify-send`, only if it's on PATH.
No modal dialogs (decision P-1). Always exits 0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

MAX_LEN = 200


def _clean(text: object, default: str) -> str:
    s = text if isinstance(text, str) and text.strip() else default
    s = "".join(ch for ch in s if ch >= " " and ch != "\x7f")  # control chars break OSC
    return s[:MAX_LEN]


def _quiet_run(cmd: list[str]) -> None:
    subprocess.run(
        cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
    )


def _osascript_quote(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _native(title: str, message: str) -> None:
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = (
            f'display notification "{_osascript_quote(message)}" '
            f'with title "{_osascript_quote(title)}"'
        )
        _quiet_run(["osascript", "-e", script])
    elif sys.platform.startswith("linux") and shutil.which("notify-send"):
        _quiet_run(["notify-send", title, message])


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        data = {}
    title = _clean(data.get("title"), "Claude Code")
    message = _clean(data.get("message"), "Claude Code needs your attention")
    try:
        _native(title, message)
    except Exception as exc:  # noqa: BLE001 - notifications are best effort
        print(f"foundry: notify native alert failed: {exc}", file=sys.stderr)
    print(json.dumps({"terminalSequence": f"\x1b]9;{title}: {message}\x07"}))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"foundry: notify internal error: {exc}", file=sys.stderr)
    sys.exit(0)
