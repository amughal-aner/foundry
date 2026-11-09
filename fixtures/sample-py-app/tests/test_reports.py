from __future__ import annotations

import pytest

from sample_app import db, reports


def test_first_page_starts_at_first_item():
    assert reports.paginate(list(range(10)), 1, 3) == [0, 1, 2]


def test_page_size_limits_results():
    assert len(reports.paginate(list(range(10)), 1, 4)) == 4


def test_page_past_the_end_is_empty():
    assert reports.paginate(list(range(4)), 3, 2) == []


@pytest.fixture
def usage_db(conn, tmp_path):
    for day in range(1, 21):
        db.record_usage(conn, 1, f"2026-10-{day:02d}", 400)  # bob: 8,000 units, 20 days
    db.record_usage(conn, 2, "2026-10-03", 1_200)  # carol: starter tier
    db.record_usage(conn, 2, "2026-09-30", 999)  # previous month, ignored
    return tmp_path / "test.db"


def test_report_totals(usage_db, tmp_path):
    summary = reports.build_usage_report(usage_db, tmp_path / "out.txt", "2026-10")
    assert summary["projects"] == 2
    assert summary["units"] == 9_200
    assert summary["free_units"] == 1_000
    # bob: growth tier 8000 * 0.015 * 0.95 = 114.0 ; carol: (1200 - 1000) * 0.02 = 4.0 -> minimum 5.0
    assert summary["amount"] == 119.0
    assert summary["minimum_applied"] == 1


def test_report_rejects_bad_month(usage_db, tmp_path):
    with pytest.raises(ValueError):
        reports.build_usage_report(usage_db, tmp_path / "out.txt", "October")


def test_csv_report_has_header(usage_db, tmp_path):
    out = tmp_path / "out.csv"
    reports.build_usage_report(usage_db, out, "2026-10", fmt="csv")
    assert out.read_text(encoding="utf-8").splitlines()[0].startswith("project,owner,tier")
