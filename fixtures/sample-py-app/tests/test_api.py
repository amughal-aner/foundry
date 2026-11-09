from __future__ import annotations

import pytest

from sample_app import api, db


def test_create_project_requires_name(conn, users):
    with pytest.raises(ValueError):
        api.create_project(conn, users["bob"], "   ")


def test_rename_by_non_owner_is_forbidden(conn, users):
    with pytest.raises(api.ForbiddenError):
        api.rename_project(conn, users["carol"], 1, "Mine now")


def test_owner_can_delete_project(conn, users):
    api.delete_project(conn, users["bob"], 1)
    assert db.get_project(conn, 1) is None


def test_delete_missing_project_raises(conn, users):
    with pytest.raises(api.NotFoundError):
        api.delete_project(conn, users["bob"], 99)


def test_record_usage_rejects_negative_units(conn, users):
    with pytest.raises(ValueError):
        api.record_usage(conn, users["bob"], 1, "2026-10-01", -5)
