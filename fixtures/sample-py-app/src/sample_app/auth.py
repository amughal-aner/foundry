"""Authorization rules for projects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def is_admin(user: Mapping[str, Any]) -> bool:
    return user["role"] == "admin"


def can_edit(user: Mapping[str, Any], project: Mapping[str, Any]) -> bool:
    """Admins can edit any project; members only the projects they own."""
    return is_admin(user) or project["owner_id"] == user["id"]
