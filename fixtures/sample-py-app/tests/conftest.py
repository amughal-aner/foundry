from __future__ import annotations

import pytest

from sample_app import db


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.add_user(connection, "alice", "admin")  # id 1
    db.add_user(connection, "bob")  # id 2
    db.add_user(connection, "carol")  # id 3
    db.add_project(connection, "Data pipeline", 2)  # id 1, owned by bob
    db.add_project(connection, "Website", 3)  # id 2, owned by carol
    yield connection
    connection.close()


@pytest.fixture
def users(conn):
    return {row["name"]: row for row in db.list_users(conn)}
