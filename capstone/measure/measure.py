#!/usr/bin/env python3
"""measure.py: run a repo's tests with coverage and emit ONE JSON measurement document (one row of capstone.repo_measurements).

  python3 measure.py --dir ./repos/orders-py-001 --run-id local-1 --iteration 0 > m.json
  python3 measure.py --dir . --parse-only            # do not run anything, just parse reports already in ./reports

Languages are detected from files: python, node, java (maven), go, dotnet. Tools used (all optional except the language's own):
  tests + coverage  python: pytest-cov (Cobertura XML)   node: node --test with lcov + junit reporters (Node 22 verified)
                    java: mvn test + JaCoCo XML          go: go test -coverprofile + -v output   dotnet: dotnet test + coverlet (Cobertura) + TRX
  lines of code     cloc if on PATH, else a built-in non-blank-line counter (an approximation)
  vulnerabilities   trivy fs --format json, if on PATH; otherwise those columns stay null
Exit code is 0 whenever a document was produced (a failing test suite is a measurement, not an error); 2 for usage errors.
Verified by running: python, node, java. go and dotnet parsers are tested against fixtures only: the toolchains were not available.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

SRC_EXT = {"python": {".py"}, "node": {".js", ".mjs", ".cjs", ".ts"}, "java": {".java"}, "go": {".go"}, "dotnet": {".cs"}}
SKIP_DIRS = {".git", "node_modules", "target", "bin", "obj", ".venv", "venv", "__pycache__", "reports", ".pytest_cache", "TestResults", "vendor"}


def detect_language(d: Path):
    if (d / "pom.xml").exists():
        return "java"
    if (d / "go.mod").exists():
        return "go"
    if (d / "package.json").exists():
        return "node"
    if any(d.rglob("*.csproj")):
        return "dotnet"
    if (d / "requirements.txt").exists() or (d / "pyproject.toml").exists():
        return "python"
    return None


# ----------------------------------------------------------------------------------------------------------- parsers
def parse_junit(paths):
    """Count <testcase> elements: works for pytest, surefire, node's junit reporter. Returns (total, passed, failed, skipped, seconds)."""
    total = failed = skipped = 0
    secs = 0.0
    for p in paths:
        root = ET.parse(p).getroot()
        for tc in root.iter("testcase"):
            total += 1
            secs += float(tc.get("time") or 0)
            kids = {c.tag for c in tc}
            if kids & {"failure", "error"}:
                failed += 1
            elif "skipped" in kids:
                skipped += 1
    return total, total - failed - skipped, failed, skipped, secs


def parse_cobertura(path):
    root = ET.parse(path).getroot()
    lr, br = root.get("line-rate"), root.get("branch-rate")
    line = float(lr) * 100 if lr is not None else None
    has_branches = int(root.get("branches-valid") or 0) > 0
    return line, (float(br) * 100 if br is not None and has_branches else None)


def parse_jacoco(path):
    root = ET.parse(path).getroot()
    out = {}
    for c in root.findall("counter"):   # report-level counters are direct children of <report>
        missed, covered = int(c.get("missed")), int(c.get("covered"))
        out[c.get("type")] = 100.0 * covered / (missed + covered) if missed + covered else None
    return out.get("LINE"), out.get("BRANCH")


def parse_lcov(path, exclude=("test/", "tests/", ".test.", ".spec.")):
    """Node's built-in coverage includes the test files themselves, which inflates the number: drop them."""
    lf = lh = brf = brh = 0
    skip = False
    for ln in Path(path).read_text().splitlines():
        if ln.startswith("SF:"):
            skip = any(x in ln[3:] for x in exclude)
        elif skip:
            continue
        elif ln.startswith("LF:"):
            lf += int(ln[3:])
        elif ln.startswith("LH:"):
            lh += int(ln[3:])
        elif ln.startswith("BRF:"):
            brf += int(ln[4:])
        elif ln.startswith("BRH:"):
            brh += int(ln[4:])
    return (100.0 * lh / lf if lf else None), (100.0 * brh / brf if brf else None)


def parse_go_cover(path):
    """Statement coverage from a coverprofile: 'file:l.c,l.c numStmts count'. Same total as `go tool cover -func`."""
    total = covered = 0
    for ln in Path(path).read_text().splitlines()[1:]:
        m = re.match(r".+:\d+\.\d+,\d+\.\d+ (\d+) (\d+)$", ln.strip())
        if m:
            n, c = int(m.group(1)), int(m.group(2))
            total += n
            covered += n if c > 0 else 0
    return (100.0 * covered / total if total else None), None


def parse_go_test_output(text):
    passed = len(re.findall(r"^\s*--- PASS:", text, re.M))
    failed = len(re.findall(r"^\s*--- FAIL:", text, re.M))
    skipped = len(re.findall(r"^\s*--- SKIP:", text, re.M))
    return passed + failed + skipped, passed, failed, skipped


def parse_trx(path):
    root = ET.parse(path).getroot()
    ns = {"t": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
    c = root.find(".//t:ResultSummary/t:Counters", ns) if ns else root.find(".//ResultSummary/Counters")
    if c is None:
        return 0, 0, 0, 0
    return int(c.get("total", 0)), int(c.get("passed", 0)), int(c.get("failed", 0)), int(c.get("total", 0)) - int(c.get("executed", c.get("total", 0)))


def parse_trivy(path_or_text):
    data = json.loads(path_or_text if isinstance(path_or_text, str) and path_or_text.lstrip().startswith("{") else Path(path_or_text).read_text())
    sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    secrets = 0
    for r in data.get("Results") or []:
        for v in r.get("Vulnerabilities") or []:
            if v.get("Severity") in sev:
                sev[v["Severity"]] += 1
        secrets += len(r.get("Secrets") or [])
    return sev, secrets


# ----------------------------------------------------------------------------------------------------------- LOC
def count_loc(d: Path, lang):
    if shutil.which("cloc"):
        try:
            out = subprocess.run(["cloc", "--json", "--quiet", "--exclude-dir=" + ",".join(sorted(SKIP_DIRS)), str(d)],
                                 capture_output=True, text=True, timeout=120).stdout
            j = json.loads(out)
            return sum(v["code"] for k, v in j.items() if k not in ("header", "SUM")), sum(v["nFiles"] for k, v in j.items() if k not in ("header", "SUM")), "cloc"
        except Exception:
            pass
    loc = files = 0
    for p in d.rglob("*"):
        if p.is_file() and p.suffix in SRC_EXT[lang] and not (set(p.relative_to(d).parts) & SKIP_DIRS):
            files += 1
            loc += sum(1 for ln in p.read_text(errors="ignore").splitlines() if ln.strip())
    return loc, files, "builtin non-blank-line counter"


# ----------------------------------------------------------------------------------------------------------- runners
def sh(cmd, cwd, timeout, env=None):
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})})
        return r.returncode, r.stdout + r.stderr, time.time() - t
    except FileNotFoundError as e:
        return 127, f"{cmd[0]}: not found ({e})", 0.0
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s", time.time() - t


def measure_language(lang, d: Path, rep: Path, run: bool, timeout):
    """Returns dict with tests/coverage fields + build_ok + notes."""
    rep.mkdir(parents=True, exist_ok=True)
    notes = []
    m = dict(test_count=0, tests_passed=0, tests_failed=0, line_coverage_pct=None, branch_coverage_pct=None, build_ok=0, test_duration_s=None)

    def finish(junit_paths, cov):
        junit_paths = [p for p in junit_paths if Path(p).exists()]
        if junit_paths:
            total, ok, bad, skip, secs = parse_junit(junit_paths)
            m.update(test_count=total, tests_passed=ok, tests_failed=bad, build_ok=1)
            m["test_duration_s"] = m["test_duration_s"] if m["test_duration_s"] is not None else round(secs, 3)
        if cov and Path(cov[0]).exists():
            m["line_coverage_pct"], m["branch_coverage_pct"] = cov[1](cov[0])

    if lang == "python":
        py = d / ".venv" / "bin" / "python"
        py = str(py) if py.exists() else sys.executable
        if run:
            code, out, secs = sh([py, "-m", "pytest", "-q", "--cov=.", "--cov-branch", f"--cov-report=xml:{rep / 'coverage.xml'}", f"--junitxml={rep / 'junit.xml'}"], d, timeout)
            m["test_duration_s"] = round(secs, 3)
            if code not in (0, 1):
                notes.append(f"pytest exited {code}: {out[-300:]}")
        finish([rep / "junit.xml"], (rep / "coverage.xml", parse_cobertura))
    elif lang == "node":
        if run:
            code, out, secs = sh(["node", "--test", "--experimental-test-coverage", "--test-reporter=spec", "--test-reporter-destination=stdout",
                                  "--test-reporter=lcov", f"--test-reporter-destination={rep / 'lcov.info'}",
                                  "--test-reporter=junit", f"--test-reporter-destination={rep / 'junit.xml'}"], d, timeout)
            m["test_duration_s"] = round(secs, 3)
            if code not in (0, 1):
                notes.append(f"node --test exited {code}: {out[-300:]}")
        finish([rep / "junit.xml"], (rep / "lcov.info", parse_lcov))
    elif lang == "java":
        if run:
            code, out, secs = sh(["mvn", "-B", "-q", "test"], d, timeout)
            m["test_duration_s"] = round(secs, 3)
            if code not in (0, 1):
                notes.append(f"mvn exited {code}: {out[-300:]}")
        sr = d / "target" / "surefire-reports"
        finish(sorted(sr.glob("TEST-*.xml")) if sr.exists() else [], (d / "target" / "site" / "jacoco" / "jacoco.xml", parse_jacoco))
    elif lang == "go":
        prof = rep / "cover.out"
        if run:
            code, out, secs = sh(["go", "test", "-v", f"-coverprofile={prof}", "./..."], d, timeout)
            m["test_duration_s"] = round(secs, 3)
            if code == 127 or "[build failed]" in out or "setup failed" in out:
                notes.append(f"go test did not run: {out[-300:]}")
            else:
                (rep / "go-test.txt").write_text(out)
        gt = rep / "go-test.txt"
        if gt.exists():
            total, ok, bad, skip = parse_go_test_output(gt.read_text())
            m.update(test_count=total, tests_passed=ok, tests_failed=bad, build_ok=1)
        if prof.exists():
            m["line_coverage_pct"], m["branch_coverage_pct"] = parse_go_cover(prof)
    elif lang == "dotnet":
        outdir = rep / "dotnet"
        if run:
            code, out, secs = sh(["dotnet", "test", "--collect:XPlat Code Coverage", "--logger", "trx;LogFileName=results.trx", "--results-directory", str(outdir)], d, timeout)
            m["test_duration_s"] = round(secs, 3)
            if code == 127:
                notes.append("dotnet not found")
        trx = sorted(outdir.rglob("*.trx")) if outdir.exists() else []
        if trx:
            total, ok, bad, skip = parse_trx(trx[0])
            m.update(test_count=total, tests_passed=ok, tests_failed=bad, build_ok=1)
        cov = sorted(outdir.rglob("coverage.cobertura.xml")) if outdir.exists() else []
        if cov:
            m["line_coverage_pct"], m["branch_coverage_pct"] = parse_cobertura(cov[0])
    m["_notes"] = notes
    return m


def scan_trivy(d: Path, rep: Path, run: bool):
    out = rep / "trivy-fs.json"
    if run and shutil.which("trivy"):
        subprocess.run(["trivy", "fs", "--scanners", "vuln,secret", "--format", "json", "--quiet", "--output", str(out), str(d)], capture_output=True, timeout=600)
    if out.exists():
        try:
            sev, secrets = parse_trivy(out)
            return sev, secrets
        except Exception:
            return None, None
    return None, None


def git_sha(d: Path):
    r = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=d, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=".")
    ap.add_argument("--repo", default=os.environ.get("REPO_NAME"), help="repo name for the row (default: $REPO_NAME, else the directory name)")
    ap.add_argument("--lang", choices=sorted(SRC_EXT), help="override detection")
    ap.add_argument("--run-id", default=os.environ.get("RUN_ID") or uuid.uuid4().hex[:12])
    ap.add_argument("--agent-run-id", default=os.environ.get("AGENT_RUN_ID", ""))
    ap.add_argument("--iteration", type=int, default=int(os.environ.get("ITERATION", "0")))
    ap.add_argument("--source", default="measure.py")
    ap.add_argument("--report-dir", default=None, help="default: <dir>/reports")
    ap.add_argument("--parse-only", action="store_true", help="do not run tests or scanners; parse existing reports")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--out", help="write JSON here instead of stdout")
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    lang = a.lang or detect_language(d)
    if not lang:
        print(f"measure.py: cannot detect a language in {d}", file=sys.stderr)
        return 2
    rep = Path(a.report_dir).resolve() if a.report_dir else d / "reports"
    run = not a.parse_only
    m = measure_language(lang, d, rep, run, a.timeout)
    loc, files, loc_tool = count_loc(d, lang)
    sev, secrets = scan_trivy(d, rep, run)
    doc = {
        "repo": a.repo or d.name, "language": lang, "commit_sha": git_sha(d), "run_id": a.run_id, "agent_run_id": a.agent_run_id,
        "iteration": a.iteration, "lines_of_code": loc, "files": files,
        "test_count": m["test_count"], "tests_passed": m["tests_passed"], "tests_failed": m["tests_failed"],
        "line_coverage_pct": None if m["line_coverage_pct"] is None else round(m["line_coverage_pct"], 2),
        "branch_coverage_pct": None if m["branch_coverage_pct"] is None else round(m["branch_coverage_pct"], 2),
        "vuln_critical": sev and sev["CRITICAL"], "vuln_high": sev and sev["HIGH"], "vuln_medium": sev and sev["MEDIUM"], "vuln_low": sev and sev["LOW"],
        "secrets_found": secrets, "lint_issues": None, "complexity_avg": None,
        "build_ok": m["build_ok"], "test_duration_s": m["test_duration_s"], "source": a.source,
    }
    for k in ("vuln_critical", "vuln_high", "vuln_medium", "vuln_low"):
        if sev is None:
            doc[k] = None
    for n in m["_notes"]:
        print(f"measure.py: {n}", file=sys.stderr)
    print(f"measure.py: loc via {loc_tool}; trivy {'used' if sev is not None else 'not available (vuln columns null)'}", file=sys.stderr)
    text = json.dumps(doc)
    if a.out:
        Path(a.out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
