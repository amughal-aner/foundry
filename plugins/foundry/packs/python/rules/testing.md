---
paths: ["tests/**", "**/test_*.py"]
---

# Testing conventions

- Use pytest: plain `assert`, `pytest.mark.parametrize` for tables of cases.
- One behavior per test. Name tests after the behavior (`test_rejects_expired_token`).
- Share setup through fixtures (`conftest.py`), not copied setup code.
- No real network calls and no real secrets. Use `tmp_path` and `monkeypatch`, plus fakes.
- Fixing a bug: write the failing test first, see it fail, then fix.
