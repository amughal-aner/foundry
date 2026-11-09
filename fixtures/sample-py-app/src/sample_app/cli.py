"""Command-line interface for sample-app."""

from __future__ import annotations

import argparse
import json
import sys

from sample_app import api, db, reports


def _current_user(conn, user_id: int):
    user = db.get_user(conn, user_id)
    if user is None:
        raise LookupError(f"user {user_id} does not exist")
    return user


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sample-app", description=__doc__)
    parser.add_argument("--db", default="sample_app.db", help="SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add-user")
    p.add_argument("name")
    p.add_argument("--role", choices=["member", "admin"], default="member")

    sub.add_parser("users")

    p = sub.add_parser("search")
    p.add_argument("text")

    p = sub.add_parser("new-project")
    p.add_argument("name")
    p.add_argument("--as-user", type=int, required=True)

    sub.add_parser("projects")

    p = sub.add_parser("rename")
    p.add_argument("project_id", type=int)
    p.add_argument("name")
    p.add_argument("--as-user", type=int, required=True)

    p = sub.add_parser("delete")
    p.add_argument("project_id", type=int)
    p.add_argument("--as-user", type=int, required=True)

    p = sub.add_parser("record")
    p.add_argument("project_id", type=int)
    p.add_argument("day")
    p.add_argument("units", type=int)
    p.add_argument("--as-user", type=int, required=True)

    p = sub.add_parser("report")
    p.add_argument("month")
    p.add_argument("--out", default="report.txt")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--format", choices=["text", "csv"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = db.connect(args.db)

    if args.command == "add-user":
        print(db.add_user(conn, args.name, args.role))
    elif args.command == "users":
        for row in db.list_users(conn):
            print(f"{row['id']}\t{row['name']}\t{row['role']}")
    elif args.command == "search":
        print(json.dumps(api.search_users(conn, args.text), indent=2))
    elif args.command == "new-project":
        user = _current_user(conn, args.as_user)
        print(api.create_project(conn, user, args.name))
    elif args.command == "projects":
        for row in db.list_projects(conn):
            print(f"{row['id']}\t{row['name']}\t{row['owner']}")
    elif args.command == "rename":
        user = _current_user(conn, args.as_user)
        api.rename_project(conn, user, args.project_id, args.name)
    elif args.command == "delete":
        user = _current_user(conn, args.as_user)
        api.delete_project(conn, user, args.project_id)
        print(f"deleted project {args.project_id}")
    elif args.command == "record":
        user = _current_user(conn, args.as_user)
        api.record_usage(conn, user, args.project_id, args.day, args.units)
    elif args.command == "report":
        summary = reports.build_usage_report(
            args.db, args.out, args.month, args.page, args.page_size, args.format
        )
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
