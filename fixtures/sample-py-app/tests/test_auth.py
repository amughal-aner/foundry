from __future__ import annotations

from sample_app import auth


def test_owner_can_edit():
    assert auth.can_edit({"id": 2, "role": "member"}, {"owner_id": 2})


def test_admin_can_edit_any_project():
    assert auth.can_edit({"id": 1, "role": "admin"}, {"owner_id": 2})


def test_other_member_cannot_edit():
    assert not auth.can_edit({"id": 3, "role": "member"}, {"owner_id": 2})
