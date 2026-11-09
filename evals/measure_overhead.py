#!/usr/bin/env python3
"""Measure foundry's always-on context overhead (plan.md §3.1). Stdlib only.

Usage:
    python evals/measure_overhead.py [--runs 3] [--fixture fixtures/sample-py-app]
                                     [--plugin-dir plugins/foundry] [--out evals/results]

Copies the fixture into a fresh temp dir and runs `claude -p "Reply with OK." --output-format json`
`--runs` times without the plugin and `--runs` times with `--plugin-dir`, alternating the arms
so cache warm-up hits both equally. The per-run input total is
input_tokens + cache_creation_input_tokens + cache_read_input_tokens. Overhead is the
difference of the arm medians. Writes evals/results/<YYYY-MM-DD>-overhead.md.
Each run is a real (tiny) model call.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPT = "Reply with OK."
BUDGET = 2_000
IGNORE = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "*.db")


def total_input(result: dict) -> int:
    usage = result.get("usage") or {}
    return sum(
        int(usage.get(k) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )


def summarize(baseline: list[int], plugin: list[int]) -> dict:
    b, p = statistics.median(baseline), statistics.median(plugin)
    return {
        "baseline_median": b,
        "plugin_median": p,
        "overhead": p - b,
        "within_budget": p - b <= BUDGET,
    }


def run_once(cwd: Path, plugin_dir: Path | None, claude: str) -> dict:
    cmd = [claude, "-p", PROMPT, "--output-format", "json"]
    if plugin_dir is not None:
        cmd += ["--plugin-dir", str(plugin_dir)]
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        detail = (out.stderr or out.stdout).strip()[-800:]
        raise RuntimeError(f"claude exited {out.returncode}: {detail}")
    return json.loads(out.stdout)


def render(rows: list[tuple[str, int, dict]], stats: dict, version: str) -> str:
    lines = [
        f"# Always-on overhead: {dt.date.today().isoformat()}",
        "",
        f"Claude Code {version}. Prompt `{PROMPT}` in a temp copy of `fixtures/sample-py-app`.",
        "Input total = input + cache creation + cache read tokens.",
        "",
        "| Run | Arm | Input total | Cost (USD) |",
        "|---|---|---|---|",
    ]
    for i, (arm, tokens, result) in enumerate(rows, 1):
        lines.append(f"| {i} | {arm} | {tokens:,} | {result.get('total_cost_usd', 0):.4f} |")
    verdict = "PASS" if stats["within_budget"] else "OVER BUDGET"
    lines += [
        "",
        f"- Baseline median: **{stats['baseline_median']:,.0f}**",
        f"- With foundry median: **{stats['plugin_median']:,.0f}**",
        f"- **Overhead: {stats['overhead']:,.0f} tokens** (budget {BUDGET:,}) → **{verdict}**",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--fixture", default=str(REPO / "fixtures" / "sample-py-app"))
    ap.add_argument("--plugin-dir", default=str(REPO / "plugins" / "foundry"))
    ap.add_argument("--out", default=str(REPO / "evals" / "results"))
    args = ap.parse_args(argv)

    claude = shutil.which("claude")
    if claude is None:
        print("measure_overhead: claude not on PATH", file=sys.stderr)
        return 1
    version = subprocess.run([claude, "--version"], capture_output=True, text=True).stdout.strip()
    plugin_dir = Path(args.plugin_dir).resolve()
    rows: list[tuple[str, int, dict]] = []
    with tempfile.TemporaryDirectory(prefix="foundry-overhead-") as tmp:
        work = Path(tmp) / "app"
        shutil.copytree(args.fixture, work, ignore=IGNORE)
        for _ in range(args.runs):
            for arm, pdir in (("baseline", None), ("foundry", plugin_dir)):
                try:
                    result = run_once(work, pdir, claude)
                except RuntimeError as exc:  # one retry for transient CLI/API errors
                    print(f"{arm}: retrying after: {exc}", file=sys.stderr)
                    result = run_once(work, pdir, claude)
                rows.append((arm, total_input(result), result))
                print(f"{arm:<9} {rows[-1][1]:>8,}", file=sys.stderr)
    stats = summarize(
        [t for a, t, _ in rows if a == "baseline"], [t for a, t, _ in rows if a == "foundry"]
    )
    out = Path(args.out) / f"{dt.date.today().isoformat()}-overhead.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render(rows, stats, version).encode("utf-8"))
    print(json.dumps(stats))
    return 0 if stats["within_budget"] else 2


if __name__ == "__main__":
    sys.exit(main())
