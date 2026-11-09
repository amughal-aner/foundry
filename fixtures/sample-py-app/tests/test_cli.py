from __future__ import annotations

from sample_app import cli


def test_add_user_and_create_project(tmp_path, capsys):
    path = str(tmp_path / "cli.db")
    assert cli.main(["--db", path, "add-user", "dana", "--role", "admin"]) == 0
    assert cli.main(["--db", path, "new-project", "Analytics", "--as-user", "1"]) == 0
    out = capsys.readouterr().out.split()
    assert out == ["1", "1"]


def test_projects_lists_owner(tmp_path, capsys):
    path = str(tmp_path / "cli.db")
    cli.main(["--db", path, "add-user", "erin"])
    cli.main(["--db", path, "new-project", "Docs", "--as-user", "1"])
    capsys.readouterr()
    cli.main(["--db", path, "projects"])
    assert "Docs\terin" in capsys.readouterr().out
