#!/usr/bin/env python3
"""integrity_check.py: did the change keep the tests honest? A deterministic check that runs OUTSIDE the agent, on the diff between a base ref and HEAD.

  python3 integrity_check.py --base origin/main [--dir .] [--no-src-changes] [--json]

Flags (exit 1 if any, 0 if none):
  deleted-test-file      a test file that existed on base is gone
  fewer-tests            a test file has fewer test definitions than on base
  fewer-assertions       a test file has fewer assertion statements than on base
  trivial-assertion      an added line asserts something that cannot fail (assert True, assertTrue(true), expect(true)...)
  skip-without-issue     an added skip/disable marker with no issue reference (#123, issues/123, ISSUE-123) on the same or the previous line
  src-changed            production code changed while --no-src-changes is set (coverage-only runs may not touch it)

This is a counting heuristic, not a proof: a determined agent can fool it, and Goodhart's law applies (see the page). Pair it with mutation testing
(PIT for Java, mutmut for Python, go-mutesting for Go, Stryker for JS/.NET: check each tool's docs) which asks the real question: would the tests
FAIL if the code were wrong?
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|_test\.go$|\.(test|spec)\.[cm]?[jt]sx?$|(Tests?|IT)\.(java|cs)$")
DEFS = {".py": r"^\s*(async\s+)?def\s+test_", ".js": r"^\s*(test|it)\s*\(", ".ts": r"^\s*(test|it)\s*\(", ".java": r"@Test\b|@ParameterizedTest\b",
        ".go": r"^func\s+Test\w*\(", ".cs": r"\[(Fact|Theory)\b"}
ASSERTS = {".py": r"\bassert\b|self\.assert\w+\(|pytest\.raises|pytest\.approx", ".js": r"\bassert(\.\w+)?\(|\bexpect\(", ".ts": r"\bassert(\.\w+)?\(|\bexpect\(",
           ".java": r"\bassert[A-Z]\w*\(|\bassertThat\(", ".go": r"\bt\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(", ".cs": r"\bAssert\.\w+\("}
TRIVIAL = re.compile(r"assert\s+True\b|assert\s+1\b|assertTrue\(\s*true\s*\)|assert\.ok\(\s*true\s*\)|expect\(\s*true\s*\)|Assert\.True\(\s*true\s*\)|assertEquals\(\s*(\w+)\s*,\s*\1\s*\)|\|\|\s*true")
SKIP = re.compile(r"@pytest\.mark\.(skip|xfail)|pytest\.skip\(|\bt\.skip\(|\.skip\(|\bxit\(|@Disabled|@Ignore|\bt\.Skip(Now)?\(|Skip\s*=|\[Ignore")
ISSUE_REF = re.compile(r"#\d+|issues/\d+|ISSUE-\d+", re.I)


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout


def count(rx, text):
    return len(re.findall(rx, text, re.M)) if rx else 0


def check(cwd, base, no_src_changes=False):
    out = []
    code, names = git(["diff", "--name-status", "--no-renames", f"{base}...HEAD"], cwd)
    if code != 0:
        raise SystemExit(f"git diff {base}...HEAD failed: is {base} fetched?")
    for line in names.splitlines():
        status, path = line.split("\t", 1)
        ext = Path(path).suffix
        is_test = bool(TEST_PATH.search(path))
        if not is_test:
            if no_src_changes and status != "A" and ext in DEFS and not path.startswith((".forgejo", "docs")):
                out.append({"rule": "src-changed", "file": path, "detail": "production code modified in a run that may only add tests"})
            elif no_src_changes and ext in DEFS and status == "A":
                out.append({"rule": "src-changed", "file": path, "detail": "new production file in a run that may only add tests"})
            continue
        if status == "D":
            out.append({"rule": "deleted-test-file", "file": path, "detail": "test file removed"})
            continue
        if status == "M":
            _, old = git(["show", f"{base}:{path}"], cwd)
            new = (Path(cwd) / path).read_text(errors="ignore")
            for rule, table in (("fewer-tests", DEFS), ("fewer-assertions", ASSERTS)):
                a, b = count(table.get(ext), old), count(table.get(ext), new)
                if b < a:
                    out.append({"rule": rule, "file": path, "detail": f"{a} -> {b}"})
        new_text = (Path(cwd) / path).read_text(errors="ignore")
        _, patch = git(["diff", "-U1", f"{base}...HEAD", "--", path], cwd)
        added = [ln[1:] for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
        for ln in added:
            if TRIVIAL.search(ln):
                out.append({"rule": "trivial-assertion", "file": path, "detail": ln.strip()[:100]})
        lines = new_text.splitlines()
        for i, ln in enumerate(lines):
            if ln in added and SKIP.search(ln):
                context = " ".join(lines[max(0, i - 1):i + 1])
                if not ISSUE_REF.search(context):
                    out.append({"rule": "skip-without-issue", "file": path, "detail": f"line {i + 1}: {ln.strip()[:80]}"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--no-src-changes", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    v = check(a.dir, a.base, a.no_src_changes)
    if a.json:
        print(json.dumps({"ok": not v, "violations": v}))
    else:
        for x in v:
            print(f"{x['rule']:20s} {x['file']}: {x['detail']}")
        print("test-integrity: " + ("FAILED" if v else "ok"))
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
