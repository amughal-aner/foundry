"""Monthly usage reports for finance."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}


def paginate(items: list[Any], page: int, page_size: int) -> list[Any]:
    """Return one page of items. Pages are numbered from 1."""
    start = page * page_size
    return items[start : start + page_size]


def build_usage_report(
    db_path: str | Path,
    out_path: str | Path,
    month: str,
    page: int = 1,
    page_size: int = 20,
    fmt: str = "text",
    currency: str = "USD",
) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError(f"month must look like YYYY-MM, got {month!r}")
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive")
    if currency not in CURRENCY_SYMBOLS:
        raise ValueError(f"unsupported currency {currency!r}")
    symbol = CURRENCY_SYMBOLS[currency]

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT p.id AS project_id, p.name AS project, u.name AS owner, u.role AS role, "
            "g.day AS day, g.units AS units "
            "FROM usage g JOIN projects p ON p.id = g.project_id "
            "JOIN users u ON u.id = p.owner_id "
            "WHERE substr(g.day, 1, 7) = ? ORDER BY p.name, g.day",
            (month,),
        ).fetchall()
    finally:
        conn.close()

    per_project: dict[int, dict[str, Any]] = {}
    for row in rows:
        entry = per_project.setdefault(
            row["project_id"],
            {
                "project": row["project"],
                "owner": row["owner"],
                "role": row["role"],
                "units": 0,
                "days": set(),
                "peak": 0,
            },
        )
        entry["units"] += row["units"]
        entry["days"].add(row["day"])
        if row["units"] > entry["peak"]:
            entry["peak"] = row["units"]

    items: list[dict[str, Any]] = []
    total_units = 0
    total_amount = 0.0
    total_free = 0
    discounted = 0
    minimum_applied = 0
    for project_id in sorted(per_project, key=lambda pid: per_project[pid]["project"].lower()):
        entry = per_project[project_id]
        units = entry["units"]
        if entry["role"] == "admin":
            tier = "internal"
        elif units > 50_000:
            tier = "enterprise"
        elif units > 5_000:
            tier = "growth"
        else:
            tier = "starter"

        if tier == "internal":
            free, rate = units, 0.0
        elif tier == "starter":
            free, rate = min(units, 1_000), 0.02
        elif tier == "growth":
            free, rate = 0, 0.015
        else:
            free, rate = 0, 0.01

        amount = (units - free) * rate
        active_days = len(entry["days"])
        if tier != "internal" and active_days >= 20:
            amount *= 0.95
            discounted += 1
        if tier != "internal" and 0 < amount < 5:
            amount = 5.0
            minimum_applied += 1
        amount = round(amount, 2)

        total_units += units
        total_free += free
        total_amount += amount
        items.append(
            {
                "project": entry["project"],
                "owner": entry["owner"],
                "tier": tier,
                "units": units,
                "active_days": active_days,
                "peak": entry["peak"],
                "amount": amount,
            }
        )

    page_items = paginate(items, page, page_size)
    pages = max(1, -(-len(items) // page_size))

    lines: list[str] = []
    if fmt == "csv":
        lines.append("project,owner,tier,units,active_days,peak,amount")
        for item in page_items:
            project = item["project"].replace('"', '""')
            if "," in project or '"' in project:
                project = f'"{project}"'
            lines.append(
                f"{project},{item['owner']},{item['tier']},{item['units']},"
                f"{item['active_days']},{item['peak']},{item['amount']:.2f}"
            )
    elif fmt == "text":
        headers = ["Project", "Owner", "Tier", "Units", "Days", "Peak", "Amount"]
        table = [
            [
                item["project"],
                item["owner"],
                item["tier"],
                f"{item['units']:,}",
                str(item["active_days"]),
                f"{item['peak']:,}",
                f"{symbol}{item['amount']:,.2f}",
            ]
            for item in page_items
        ]
        widths = [len(h) for h in headers]
        for cells in table:
            for i, cell in enumerate(cells):
                widths[i] = max(widths[i], len(cell))
        lines.append(f"Usage report {month} (page {page} of {pages})")
        lines.append("")
        lines.append("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        lines.append("  ".join("-" * w for w in widths))
        for cells in table:
            lines.append(
                "  ".join(
                    cell.rjust(widths[i]) if i >= 3 else cell.ljust(widths[i])
                    for i, cell in enumerate(cells)
                )
            )
        if not table:
            lines.append("(no usage recorded)")
        lines.append("")
        lines.append(f"Projects: {len(items)}")
        lines.append(f"Units: {total_units:,} ({total_free:,} free)")
        lines.append(f"Volume discounts: {discounted}, minimum charges: {minimum_applied}")
        lines.append(f"Total: {symbol}{total_amount:,.2f} {currency}")
    else:
        raise ValueError(f"unknown format {fmt!r}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "month": month,
        "projects": len(items),
        "units": total_units,
        "free_units": total_free,
        "amount": round(total_amount, 2),
        "currency": currency,
        "discounted": discounted,
        "minimum_applied": minimum_applied,
        "page": page,
        "pages": pages,
        "rows_written": len(page_items),
    }
