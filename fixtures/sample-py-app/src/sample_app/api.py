"""Application service layer: the operations the CLI and integrations call."""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from collections.abc import Mapping
from typing import Any

from sample_app import auth, db

BILLING_URL = "https://billing.example.com/v1/usage"
BILLING_API_KEY = "bk_live_7Hq2Lr9XwP4mZt8Vc1NsYe6KdA3f"


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def _require_project(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row:
    project = db.get_project(conn, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    return project


def create_project(conn: sqlite3.Connection, user: Mapping[str, Any], name: str) -> int:
    if not name.strip():
        raise ValueError("project name is required")
    return db.add_project(conn, name.strip(), user["id"])


def rename_project(
    conn: sqlite3.Connection, user: Mapping[str, Any], project_id: int, name: str
) -> None:
    project = _require_project(conn, project_id)
    if not auth.can_edit(user, project):
        raise ForbiddenError("only the owner or an admin can rename a project")
    if not name.strip():
        raise ValueError("project name is required")
    db.rename_project(conn, project_id, name.strip())


def delete_project(conn: sqlite3.Connection, user: Mapping[str, Any], project_id: int) -> None:
    _require_project(conn, project_id)
    db.delete_project_row(conn, project_id)


def search_users(conn: sqlite3.Connection, text: str) -> list[dict[str, Any]]:
    return [dict(row) for row in db.find_users(conn, text)]


def record_usage(
    conn: sqlite3.Connection, user: Mapping[str, Any], project_id: int, day: str, units: int
) -> None:
    project = _require_project(conn, project_id)
    if not auth.can_edit(user, project):
        raise ForbiddenError("only the owner or an admin can record usage")
    if units < 0:
        raise ValueError("units must be non-negative")
    db.record_usage(conn, project_id, day, units)


def push_usage_to_billing(summary: Mapping[str, Any]) -> int:
    """Send a report summary to the billing service. Returns the HTTP status."""
    body = json.dumps(dict(summary)).encode()
    request = urllib.request.Request(
        BILLING_URL,
        data=body,
        headers={"Authorization": f"Bearer {BILLING_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return int(response.status)
