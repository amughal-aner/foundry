# Manual pilot: Gate 2

Fixture: `fixtures/sample-py-app` copied to a scratch repo and bootstrapped with `/foundry:bootstrap`.
Answer key: [`evals/answer-keys/sample-py-app.md`](../answer-keys/sample-py-app.md).
Claude Code version: ______ · Model: ______ · Date: ______ · Tester: ______

| Skill run | Expected hits | Hit? (Y/N per issue) | Output file written? | Notes (misses, noise, cost) |
|---|---|---|---|---|
| `/foundry:threat-model` | 1 SQL injection · 2 hardcoded key · 3 missing authz on delete | 1: _ · 2: _ · 3: _ | `docs/security/threat-model-*.md`: _ | |
| `/foundry:review-diff` on a change to `reports.py` | 4 pagination off-by-one | 4: _ | (reply only) | Did security-auditor run? It shouldn't for this diff |
| `/foundry:system-design` "restructure reporting" | 5 god function + CLI bypasses api | 5: _ | `docs/adr/0001-*.md`: _ | |
| `/foundry:product-brief` "the CLI" | 6 raw tracebacks + delete without confirmation | 6: _ | `docs/product/*-brief.md`: _ | |

Suggested change for the review-diff run (it touches `reports.py` without fixing the bug):

```python
# in reports.py, add below paginate():
def page_count(total: int, page_size: int) -> int:
    return max(1, -(-total // page_size))
```

## Observations

- Did each skill delegate to the named `foundry:*` subagent rather than a fork? (`/tasks` shows the agent name)
- Did Claude continue after the background report arrived, without a nudge?
- Anything the specialists got wrong or invented:
