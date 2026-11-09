from __future__ import annotations

from sample_app import db


def test_get_user_returns_role(conn):
    user = db.get_user(conn, 1)
    assert user is not None
    assert (user["name"], user["role"]) == ("alice", "admin")


def test_find_users_matches_substring(conn):
    assert [row["name"] for row in db.find_users(conn, "ar")] == ["carol"]


def test_delete_project_row_removes_usage(conn):
    db.record_usage(conn, 1, "2026-10-01", 10)
    db.delete_project_row(conn, 1)
    assert db.get_project(conn, 1) is None
    assert conn.execute("SELECT COUNT(*) FROM usage WHERE project_id = 1").fetchone()[0] == 0
