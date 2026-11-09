from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from measure_overhead import render, summarize, total_input  # noqa: E402


def test_total_input_sums_all_input_kinds():
    usage = {
        "input_tokens": 2,
        "cache_creation_input_tokens": 9009,
        "cache_read_input_tokens": 14457,
        "output_tokens": 4,
    }
    assert total_input({"usage": usage}) == 23468
    assert total_input({}) == 0


def test_summarize_uses_medians():
    stats = summarize([100, 120, 110], [900, 1000, 5000])
    assert stats["overhead"] == 1000 - 110
    assert stats["within_budget"] is True
    assert summarize([0], [2001])["within_budget"] is False


def test_render_reports_verdict():
    rows = [("baseline", 100, {"total_cost_usd": 0.01}), ("foundry", 600, {"total_cost_usd": 0.02})]
    text = render(rows, summarize([100], [600]), "2.1.319")
    assert "Overhead: 500 tokens" in text and "PASS" in text
