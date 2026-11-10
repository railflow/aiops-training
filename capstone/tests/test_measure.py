"""Parser tests use small fixtures (so go and dotnet are covered without their toolchains). The integration tests run the real tools on a generated repo."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "measure"))
sys.path.insert(0, str(ROOT / "gen"))
import measure  # noqa: E402
import ship  # noqa: E402


def test_junit_counts_failures_errors_and_skips(tmp_path):
    p = tmp_path / "j.xml"
    p.write_text('<testsuites><testsuite><testcase name="a" time="0.5"/><testcase name="b"><failure/></testcase>'
                 '<testcase name="c"><error/></testcase><testcase name="d"><skipped/></testcase></testsuite></testsuites>')
    assert measure.parse_junit([p]) == (4, 1, 2, 1, 0.5)


def test_cobertura_ignores_branch_rate_when_no_branches(tmp_path):
    p = tmp_path / "c.xml"
    p.write_text('<coverage line-rate="0.5" branch-rate="0" branches-valid="0"/>')
    assert measure.parse_cobertura(p) == (50.0, None)
    p.write_text('<coverage line-rate="0.25" branch-rate="0.5" branches-valid="8"/>')
    assert measure.parse_cobertura(p) == (25.0, 50.0)


def test_jacoco_report_level_counters(tmp_path):
    p = tmp_path / "j.xml"
    p.write_text('<report name="x"><package><counter type="LINE" missed="99" covered="1"/></package>'
                 '<counter type="LINE" missed="30" covered="10"/><counter type="BRANCH" missed="1" covered="3"/></report>')
    assert measure.parse_jacoco(p) == (25.0, 75.0)


def test_lcov_excludes_test_files(tmp_path):
    p = tmp_path / "l.info"
    p.write_text("SF:src/a.js\nLH:2\nLF:4\nBRH:1\nBRF:2\nend_of_record\nSF:test/a.test.js\nLH:10\nLF:10\nend_of_record\n")
    assert measure.parse_lcov(p) == (50.0, 50.0)


def test_go_coverprofile_and_output(tmp_path):
    p = tmp_path / "c.out"
    p.write_text("mode: set\nexample.com/x/a.go:3.10,5.2 2 1\nexample.com/x/a.go:7.10,9.2 6 0\n")
    assert measure.parse_go_cover(p) == (25.0, None)
    out = "=== RUN   TestA\n--- PASS: TestA (0.00s)\n--- FAIL: TestB (0.00s)\n--- SKIP: TestC (0.00s)\n    --- PASS: TestA/sub (0.00s)\n"
    assert measure.parse_go_test_output(out) == (4, 2, 1, 1)


def test_trx_counters(tmp_path):
    p = tmp_path / "r.trx"
    p.write_text('<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><ResultSummary outcome="Failed">'
                 '<Counters total="10" executed="9" passed="7" failed="2"/></ResultSummary></TestRun>')
    assert measure.parse_trx(p) == (10, 7, 2, 1)


def test_trivy_severity_counts():
    doc = json.dumps({"Results": [{"Vulnerabilities": [{"Severity": "HIGH"}, {"Severity": "HIGH"}, {"Severity": "LOW"}], "Secrets": [{}]}]})
    sev, secrets = measure.parse_trivy(doc)
    assert sev["HIGH"] == 2 and sev["LOW"] == 1 and sev["CRITICAL"] == 0 and secrets == 1


def test_generator_line_ranges_point_at_the_planted_code(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / "repos"), "--count", "5", "--seed", "1", "--no-git"], check=True, capture_output=True)
    keys = list((tmp_path / "answer-keys").glob("*.json"))
    assert len(keys) == 5
    for k in keys:
        j = json.loads(k.read_text())
        assert not (tmp_path / "repos" / j["repo"] / ".planted-issues.json").exists()   # the answer key is NOT in the repo
        cats = {i["category"] for i in j["issues"]}
        assert {"hardcoded-secret", "null-handling", "flaky-test"} <= cats
        for i in j["issues"]:
            lines = (tmp_path / "repos" / j["repo"] / i["file"]).read_text().splitlines()
            assert 1 <= i["line_start"] <= i["line_end"] <= len(lines)
            snippet = "\n".join(lines[i["line_start"] - 1:i["line_end"]])
            assert snippet.strip(), i
            if i["category"] == "hardcoded-secret":
                assert "AKIA" in snippet


def test_generator_is_deterministic(tmp_path):
    for n in ("a", "b"):
        subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / n / "repos"), "--count", "3", "--seed", "9"], check=True, capture_output=True)
    for repo in (tmp_path / "a" / "repos").iterdir():
        sha = lambda base: subprocess.run(["git", "rev-parse", "HEAD"], cwd=base / repo.name, capture_output=True, text=True).stdout
        assert sha(tmp_path / "a" / "repos") == sha(tmp_path / "b" / "repos")


def test_measure_a_generated_python_repo(tmp_path):
    pytest.importorskip("pytest_cov")
    subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / "repos"), "--lang", "python", "--domain", "billing", "--name", "billing-py-001"], check=True, capture_output=True)
    r = subprocess.run([sys.executable, str(ROOT / "measure" / "measure.py"), "--dir", str(tmp_path / "repos" / "billing-py-001"), "--run-id", "t"], capture_output=True, text=True)
    doc = json.loads(r.stdout)
    assert doc["language"] == "python" and doc["build_ok"] == 1 and doc["test_count"] >= 8
    assert 0 < doc["line_coverage_pct"] < 60          # deliberately poor
    assert doc["vuln_critical"] is None or isinstance(doc["vuln_critical"], int)


def test_measure_document_fits_the_clickhouse_table(tmp_path):
    chdb = pytest.importorskip("chdb")
    from chdb import session
    s = session.Session(str(tmp_path / "ch"))
    for f in sorted((ROOT / "sql").glob("00[12]*.sql")):
        import re
        for stmt in [x.strip() for x in re.sub(r"--[^\n]*", "", f.read_text()).split(";") if x.strip()]:
            s.query(stmt)
    doc = {"repo": "r", "language": "go", "commit_sha": "abc", "run_id": "x", "agent_run_id": "", "iteration": 0, "lines_of_code": 10, "files": 1, "test_count": 2,
           "tests_passed": 2, "tests_failed": 0, "line_coverage_pct": 12.5, "branch_coverage_pct": None, "vuln_critical": None, "vuln_high": None,
           "vuln_medium": None, "vuln_low": None, "secrets_found": None, "lint_issues": None, "complexity_avg": None, "build_ok": 1, "test_duration_s": 0.5, "source": "measure.py"}
    s.query("INSERT INTO capstone.repo_measurements FORMAT JSONEachRow " + json.dumps(doc))
    assert str(s.query("SELECT count() FROM capstone.repo_measurements", "CSV")).strip() == "1"


def test_ship_posts_json_each_row():
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["auth"] = self.headers.get("Authorization")
            seen["body"] = self.rfile.read(int(self.headers["Content-Length"])).decode()
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    n = ship.insert_rows([{"repo": "a"}, {"repo": "b"}], url=f"http://127.0.0.1:{srv.server_port}", user="u", password="p")
    srv.shutdown()
    assert n == 2 and "INSERT+INTO+capstone.repo_measurements+FORMAT+JSONEachRow" in seen["path"]
    assert seen["body"].splitlines() == ['{"repo": "a"}', '{"repo": "b"}'] and seen["auth"].startswith("Basic ")


def test_answer_key_matching(tmp_path):
    import answer_key
    subprocess.run([sys.executable, str(ROOT / "gen" / "generate.py"), "--out", str(tmp_path / "repos"), "--lang", "python", "--domain", "billing", "--name", "b-py"], check=True, capture_output=True)
    keys = answer_key.load_keys(tmp_path / "answer-keys")
    first = keys["b-py"][0]
    assert answer_key.match(keys, "b-py", first["file"], first["line_start"]) == first["id"]
    assert answer_key.match(keys, "b-py", first["file"], 9999) == ""
    assert len(list(answer_key.rows(keys))) == len(keys["b-py"])


def test_score_matches_only_issues_near_a_planted_range():
    import answer_key
    keys = {"r": [{"id": "r-P01", "file": "a.py", "line_start": 10, "line_end": 12, "category": "x", "severity": "high", "description": ""}]}
    got = answer_key.score(keys, [{"repo": "r", "issue_number": 1, "file": "a.py", "line": 14}, {"repo": "r", "issue_number": 2, "file": "a.py", "line": 40}])
    assert got == [{"repo": "r", "issue_number": 1, "planted_id": "r-P01", "rule": "file+line"}]
