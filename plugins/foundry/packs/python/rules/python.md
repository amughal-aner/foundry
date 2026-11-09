---
paths: ["**/*.py"]
---

# Python conventions

- Run everything through the project's runner (see CLAUDE.md "Commands"). Never call bare `pip install`.
- Public functions and methods have type hints, including return types.
- No bare `except:`. Catch the narrowest exception, and re-raise or log with context.
- Use `pathlib.Path`, not `os.path`.
- Library code logs with `logging.getLogger(__name__)`. Only CLI entry points print.
- Validate external input (CLI args, HTTP, files, env) at the boundary. Use pydantic models
  only if the project already depends on pydantic.
- Don't add a dependency without saying so and naming why the stdlib or an existing dependency
  isn't enough.
