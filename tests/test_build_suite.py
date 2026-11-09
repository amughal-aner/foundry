from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from build_suite import CASES, SUITE, build, load_patterns, main  # noqa: E402
from conftest import FIXTURE  # noqa: E402


def test_suite_on_disk_matches_generator():
    assert main(["--check"]) == 0, "run: python evals/build_suite.py"


def test_three_cases_per_model_invocable_skill():
    skills = [c[1] for c in CASES]
    for skill in ("system-design", "threat-model", "product-brief", "review-diff"):
        assert skills.count(skill) == 3


def test_every_expected_issue_has_a_pattern():
    patterns = load_patterns()
    for case in CASES:
        for issue in case[3]:
            assert issue in patterns


def test_patterns_do_not_match_fixture_source():
    source = "\n".join(p.read_text(encoding="utf-8") for p in (FIXTURE / "src").rglob("*.py"))
    for key, pattern in load_patterns().items():
        assert not re.search(pattern, source, re.IGNORECASE), key


def test_prompts_do_not_leak_answers():
    patterns = load_patterns()
    for cid, _skill, _out, issues, prompt, _extra in CASES:
        for issue in issues:
            assert not re.search(patterns[issue], prompt, re.IGNORECASE), (cid, issue)


def test_generated_graders_shape():
    files = {p.relative_to(SUITE).as_posix(): c for p, c in build().items()}
    tm = files["tm-repo/graders/hit-1.md"]
    assert "target: { source: file, path: docs/security/threat-model-repo.md }" in tm
    assert "type: file_exists" in files["tm-repo/graders/output-file.md"]
    assert "target: last_message" in files["rd-page-count/graders/hit-4.md"]
    assert "needs-bash" in files["rd-page-count/prompt.md"]
    fired = files["tm-repo/graders/skill-fired.md"]
    assert 'input_match: \'"skill"\\s*:\\s*"(?:[\\w-]+:)?threat-model"\'' in fired
