#!/usr/bin/env python3
"""foundry PreToolUse guard: block a short list of destructive shell commands.

Matcher: Bash|PowerShell (on Windows the PowerShell tool is often the primary shell).
Reads the hook JSON on stdin and inspects tool_input.command.
- Blocked: exit 2 with a one-line reason on stderr, prefixed "foundry:".
- Allowed: exit 0. Internal error: log to stderr and exit 0 (fail open).

BEST EFFORT ONLY. Plain text matching can't see through `sh -c "$VAR"`, aliases, scripts or
encoded commands. Permission `deny` rules and the sandbox are the real boundary.

Quoted text is NOT parsed out on purpose: `echo "rm -rf /"` and a commit message mentioning
`git push --force` are blocked too. A false positive costs one retry. Treating quoted text as
inert would let `bash -c 'rm -rf /'` through.
"""

from __future__ import annotations

import json
import re
import sys

# --- Rules (data) -----------------------------------------------------------------------------
RM_WORDS_POSIX = {"rm"}
RM_WORDS_POWERSHELL = {"remove-item", "ri", "del", "erase", "rd", "rmdir"}
DANGEROUS_RM_TARGETS = {
    "/",
    "/*",
    "~",
    "~/",
    "~/*",
    "$home",
    "$home/",
    "$home/*",
    "${home}",
    "${home}/",
    ".",
    "./",
    "./*",
    "..",
    "../",
    "*",
    "\\",
    "$env:userprofile",
    "$env:homepath",
}
DRIVE_ROOT = re.compile(r"^[a-z]:[\\/]?\*?$")  # C:  C:\  C:/  C:\*
PROTECTED_BRANCH = re.compile(r"^(?:.*:)?(?:refs/heads/)?(?:main|master)$")  # main, HEAD:main
FILE_READERS = {"cat", "less", "more", "head", "tail", "bat", "nl", "get-content", "gc", "type"}
ENV_ALLOWED = {".env.example", ".env.sample"}
PIPE_TO_SHELL = [
    re.compile(
        r"\b(?:curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n|]*\|\s*(?:sudo\s+)?"
        r"(?:sh|bash|zsh|dash|ksh|iex|invoke-expression)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:sh|bash|zsh)\b[^\n]*(?:<\(|\$\()\s*(?:curl|wget)\b", re.IGNORECASE),
]
MESSAGES = {
    "rm": "recursive force-delete of a root, home or working-directory target",
    "force_push": "force push (use --force-with-lease if you must)",
    "push_main": "direct push to main/master",
    "reset_origin": "git reset --hard to an origin/* ref",
    "clean_fdx": "git clean -fdx (deletes ignored files too)",
    "pipe_shell": "piping a download straight into a shell",
    "read_env": "reading a .env file",
}
# ----------------------------------------------------------------------------------------------

SEGMENT_SPLIT = re.compile(r"&&|\|\||[;&|\n]")


def _word(token: str) -> str:
    """Normalize a token that might be a command name: strip quoting/subshell chars and paths."""
    w = token.lower().lstrip("$(`\"'{").rstrip(")`\"'};")
    return w.replace("\\", "/").rsplit("/", 1)[-1]


def _arg(token: str) -> str:
    return token.lower().strip("\"'`").rstrip(");")


def _rm_hit(tokens: list[str]) -> bool:
    for i, tok in enumerate(tokens):
        word = _word(tok)
        if word not in RM_WORDS_POSIX | RM_WORDS_POWERSHELL:
            continue
        args = [_arg(t) for t in tokens[i + 1 :]]
        flags = [a for a in args if a.startswith("-")]
        targets = [a for a in args if a and not a.startswith("-")]
        if word in RM_WORDS_POSIX:
            short = "".join(f[1:] for f in flags if re.fullmatch(r"-[a-z]+", f))
            recursive = "r" in short or "--recursive" in flags
            force = "f" in short or "--force" in flags
        else:  # PowerShell parameter prefixes: -r / -rec / -recurse, -fo / -force
            recursive = any(f.startswith("-r") for f in flags)
            force = any(f.startswith("-fo") for f in flags)
        if (
            recursive
            and force
            and any(t in DANGEROUS_RM_TARGETS or DRIVE_ROOT.match(t) for t in targets)
        ):
            return True
    return False


def _git_hits(tokens: list[str]) -> list[str]:
    hits: list[str] = []
    for i, tok in enumerate(tokens):
        if _word(tok) != "git":
            continue
        rest = [_arg(t) for t in tokens[i + 1 :]]
        j = 0
        while j < len(rest) and rest[j].startswith("-"):  # global options; -C/-c take a value
            j += 2 if rest[j] == "-c" else 1  # args are lower-cased, so this covers -C too
        if j >= len(rest):
            continue
        sub, args = rest[j], rest[j + 1 :]
        short = "".join(a[1:] for a in args if re.fullmatch(r"-[a-z]+", a))
        if sub == "push":
            if (
                "--force" in args
                or any(a.startswith("--force=") for a in args)
                or "f" in short
                or any(a.startswith("+") and len(a) > 1 for a in args)
            ):
                hits.append("force_push")
            positional = [a for a in args if not a.startswith("-")]
            if any(PROTECTED_BRANCH.match(a) for a in positional[1:]):
                hits.append("push_main")
        elif sub == "reset" and "--hard" in args and any("origin/" in a for a in args):
            hits.append("reset_origin")
        elif sub == "clean" and {"f", "d", "x"} <= set(short + ("f" if "--force" in args else "")):
            hits.append("clean_fdx")
    return hits


def _reads_env(tokens: list[str]) -> bool:
    for i, tok in enumerate(tokens):
        if _word(tok) not in FILE_READERS:
            continue
        for arg in tokens[i + 1 :]:
            name = _arg(arg).replace("\\", "/").rsplit("/", 1)[-1]
            if name == ".env" or (name.startswith(".env.") and name not in ENV_ALLOWED):
                return True
    return False


def check(command: str) -> str | None:
    """Return the id of the first rule `command` violates, or None."""
    if any(p.search(command) for p in PIPE_TO_SHELL):
        return "pipe_shell"
    for segment in SEGMENT_SPLIT.split(command):
        tokens = segment.split()
        if _rm_hit(tokens):
            return "rm"
        git = _git_hits(tokens)
        if git:
            return git[0]
        if _reads_env(tokens):
            return "read_env"
    return None


def main() -> int:
    if sys.version_info < (3, 9):  # noqa: UP036 - macOS CLT python3 is 3.9; older: fail open
        return 0
    data = json.load(sys.stdin)
    command = (data.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return 0
    rule = check(command)
    if rule is None:
        return 0
    print(
        f"foundry: blocked {MESSAGES[rule]}. If it is really intended, ask the user to run it.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - fail open by design
        print(f"foundry: guard_bash internal error, allowing: {exc}", file=sys.stderr)
        sys.exit(0)
