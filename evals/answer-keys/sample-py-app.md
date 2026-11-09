# Answer key: `fixtures/sample-py-app`

The seeded issues are recorded **only here**. Never mention them inside the fixture. Each issue
lists regexes (case-insensitive, JavaScript syntax) that a specialist's output must match to
count as a hit. Phase 3 graders inline these patterns.

| # | Category | Location | Issue | Expected finder |
|---|---|---|---|---|
| 1 | Security | `src/sample_app/db.py` `find_users` | SQL built with an f-string from user input (`LIKE '%{name_fragment}%'`) → SQL injection, reachable via `cli search` → `api.search_users` | threat-model, security-auditor, review-diff |
| 2 | Security | `src/sample_app/api.py` `BILLING_API_KEY` | Hardcoded live API key constant in source | threat-model, security-auditor |
| 3 | Security | `src/sample_app/api.py` `delete_project` | No authorization check: any user can delete any project (`rename_project` and `record_usage` call `auth.can_edit`, `delete_project` doesn't) | threat-model, security-auditor, review-diff |
| 4 | Bug | `src/sample_app/reports.py` `paginate` | Off-by-one: `start = page * page_size` with 1-based pages skips the first page (`tests/test_reports.py::test_first_page_starts_at_first_item` fails). In the report, page 1 shows "(no usage recorded)" | review-diff (on a change to reports.py), test-runner |
| 5 | Design | `src/sample_app/reports.py` `build_usage_report`; `src/sample_app/cli.py` | One ~170-line function mixes DB I/O, pricing/business rules, formatting and file writing. `cli.py` imports `db` directly (`users`, `projects`, `_current_user`) and bypasses the `api` service layer | system-design / architect |
| 6 | Product/UX | `src/sample_app/cli.py` | Errors surface as raw tracebacks (no handling of `LookupError`, `ForbiddenError`, `NotFoundError`, `ValueError`). `delete` destroys a project and its usage with no confirmation or `--yes` flag | product-brief / product-designer |

## Hit patterns

`evals/build_suite.py` parses this block (one `id  pattern` per line) into graders. Patterns
must not match the fixture's source code verbatim (e.g. no bare `find_users`), so a document that
merely quotes the code doesn't count as finding the issue.

```text
1   sql.?injection|f-?string.{0,80}(sql|query)|parameteri[sz]ed
2   hard.?coded.{0,40}(key|secret|credential|token)|(secret|credential|api.?key).{0,60}(in (the )?source|committed|in code)
3   (authori[sz]ation|permission|access.?control|can_edit|ownership|owner check).{0,120}delet|delete_project.{0,160}(authori[sz]|permission|check|owner|can_edit)
4   off.?by.?one|\(page ?- ?1\)|skips? the first|first page|[01].?based|zero.?based
5a  (single|one|monolithic|god|large|long|\d{3}.?line).{0,40}function|build_usage_report.{0,160}(split|separate|responsibilit|mix|extract)
5b  bypass.{0,60}(api|service)|cli.{0,80}(imports?|calls?|uses?|reaches?).{0,40}\bdb\b|direct(ly)?.{0,40}(db|database|storage)
6a  traceback|raw exception|stack trace|unhandled (exception|error)
6b  confirm(ation)?.{0,80}delet|delet.{0,80}confirm|--yes|are you sure
```

## Not seeded (don't count as misses)

- `push_usage_to_billing` has no retry or backoff, and `db.connect` default path is relative.
  Valid findings, but not scored.
