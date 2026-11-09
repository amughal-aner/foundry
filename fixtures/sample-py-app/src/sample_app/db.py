"""SQLite storage for users, projects and usage events."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'member'
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    day TEXT NOT NULL,
    units INTEGER NOT NULL
);
"""


def connect(path: str | Path = "sample_app.db") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def add_user(conn: sqlite3.Connection, name: str, role: str = "member") -> int:
    cur = conn.execute("INSERT INTO users (name, role) VALUES (?, ?)", (name, role))
    conn.commit()
    return int(cur.lastrowid or 0)


def get_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT id, name, role FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, name, role FROM users ORDER BY name").fetchall()


def find_users(conn: sqlite3.Connection, name_fragment: str) -> list[sqlite3.Row]:
    query = f"SELECT id, name, role FROM users WHERE name LIKE '%{name_fragment}%' ORDER BY name"
    return conn.execute(query).fetchall()


def add_project(conn: sqlite3.Connection, name: str, owner_id: int) -> int:
    cur = conn.execute("INSERT INTO projects (name, owner_id) VALUES (?, ?)", (name, owner_id))
    conn.commit()
    return int(cur.lastrowid or 0)


def get_project(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, owner_id FROM projects WHERE id = ?", (project_id,)
    ).fetchone()


def list_projects(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT p.id, p.name, u.name AS owner FROM projects p "
        "JOIN users u ON u.id = p.owner_id ORDER BY p.name"
    ).fetchall()


def rename_project(conn: sqlite3.Connection, project_id: int, name: str) -> None:
    conn.execute("UPDATE projects SET name = ? WHERE id = ?", (name, project_id))
    conn.commit()


def delete_project_row(conn: sqlite3.Connection, project_id: int) -> None:
    conn.execute("DELETE FROM usage WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


def record_usage(conn: sqlite3.Connection, project_id: int, day: str, units: int) -> None:
    conn.execute(
        "INSERT INTO usage (project_id, day, units) VALUES (?, ?, ?)", (project_id, day, units)
    )
    conn.commit()
