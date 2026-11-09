from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "foundry"
HOOK_SCRIPTS = PLUGIN / "hooks" / "scripts"
BOOTSTRAP_SCRIPTS = PLUGIN / "skills" / "bootstrap" / "scripts"
PACK_PY = PLUGIN / "packs" / "python"
FIXTURE = REPO / "fixtures" / "sample-py-app"

# Scripts under test are standalone (they're copied to the plugin cache), so import them by path.
for p in (HOOK_SCRIPTS, BOOTSTRAP_SCRIPTS, PACK_PY / "hooks"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def run_hook(
    script: Path, payload: dict | str, env: dict | None = None
) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(script)],
        input=data,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


@pytest.fixture
def hook():
    return run_hook
