import datetime as dt
import json
import os

import check_skills as cs

D = os.path.join(os.path.dirname(__file__), "..", "skills", "examples")


def test_good_skill_ok():
    errs, warns, name = cs.lint(os.path.join(D, "write-runbook", "SKILL.md"))
    assert errs == [] and name == "write-runbook"


def test_bad_skill_flags_everything_that_must_never_ship():
    errs, _, _ = cs.lint(os.path.join(D, "bad-skill", "SKILL.md"))
    text = "\n".join(errs)
    for needle in ("lowercase", "does not match its folder", "description under 40", "secret", "pipes a download", "prompt-injection", "hide actions"):
        assert needle in text, needle


def test_cli_exit_code_and_duplicates(tmp_path):
    for d in ("a", "b"):
        os.makedirs(tmp_path / d)
        (tmp_path / d / "SKILL.md").write_text("---\nname: same-name\ndescription: Does a useful thing in a clear way. Use when testing.\nowner: x\nversion: 1\n---\nbody\n")
    assert cs.main([str(tmp_path)]) == 1


def test_stale_detection(tmp_path):
    now = dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc)
    u = tmp_path / "u.jsonl"
    u.write_text("\n".join(json.dumps(r) for r in [{"skill": "fresh", "at": "2026-11-01T00:00:00Z"}, {"skill": "old", "at": "2026-01-01T00:00:00Z"}]))
    assert cs.stale(str(u), ["fresh", "old", "never"], 90, now) == ["never", "old"]
