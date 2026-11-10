import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "specs"))
import check_spec  # noqa: E402


def read(name):
    return open(os.path.join(ROOT, "specs", name), encoding="utf-8").read()


def test_good_spec_passes():
    assert check_spec.check(read("examples/good.md")) == []


def test_bad_spec_reports_the_useful_problems():
    problems = "\n".join(check_spec.check(read("examples/bad.md")))
    assert "vague word" in problems
    assert "Non-goals" in problems
    assert "Rollback" in problems
    assert "test plan: no mention of AC-1" in problems


def test_template_is_not_acceptable_until_filled_in():
    assert check_spec.check(read("spec-template.md")) != []


def test_missing_front_matter():
    assert "front matter" in check_spec.check("## Problem\nx")[0]


def test_cli_exit_codes():
    py = sys.executable
    good = subprocess.run([py, os.path.join(ROOT, "specs", "check_spec.py"), os.path.join(ROOT, "specs/examples/good.md")], capture_output=True, text=True)
    bad = subprocess.run([py, os.path.join(ROOT, "specs", "check_spec.py"), os.path.join(ROOT, "specs/examples/bad.md")], capture_output=True, text=True)
    assert good.returncode == 0 and bad.returncode == 1
