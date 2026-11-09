# sample-app

A small project tracker for internal teams. Members create projects, the platform records daily
usage units per project, and finance pulls a monthly usage report that feeds billing.

## Usage

```bash
uv sync
uv run sample-app --db tracker.db add-user alice --role admin
uv run sample-app --db tracker.db new-project "Data pipeline" --as-user 1
uv run sample-app --db tracker.db report 2026-10 --out report.txt
```

Commands: `add-user`, `users`, `search`, `new-project`, `projects`, `rename`, `delete`,
`record`, `report`.

## Development

```bash
uv run pytest
uv run ruff check .
uv run pyright
```

Data lives in a single SQLite file (default `sample_app.db`).
