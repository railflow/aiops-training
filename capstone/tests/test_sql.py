"""Run the DDL and every named query against an embedded ClickHouse (the chdb pip package), with seeded rows.
Skips if chdb is not installed:  pip install chdb pytest
chdb bundles a newer ClickHouse than the course's 24.8: the SQL here avoids features newer than 24.8, but re-run against your server."""
import re
from pathlib import Path

import pytest

chdb = pytest.importorskip("chdb")
from chdb import session  # noqa: E402

SQL = Path(__file__).resolve().parent.parent / "sql"


def statements(text: str):
    return [s.strip() for s in re.sub(r"--[^\n]*", "", text).split(";") if s.strip()]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    s = session.Session(str(tmp_path_factory.mktemp("ch")))
    for f in sorted(SQL.glob("00*.sql")):
        for stmt in statements(f.read_text()):
            s.query(stmt)
    ins = ("INSERT INTO capstone.repo_measurements (ts, repo, language, commit_sha, run_id, iteration, lines_of_code, files, test_count, "
           "tests_passed, tests_failed, line_coverage_pct, vuln_critical, vuln_high, build_ok) VALUES ")
    rows = [
        ("2026-11-01 10:00:00", "a-svc", "python", "c1", "r1", 0, 1000, 10, 5, 5, 0, 10.0, 1, 3, 1),
        ("2026-11-02 10:00:00", "a-svc", "python", "c2", "r2", 1, 1100, 11, 15, 15, 0, 35.0, 1, 3, 1),
        ("2026-11-03 10:00:00", "a-svc", "python", "c3", "r3", 2, 1150, 11, 20, 20, 0, 52.5, 0, 3, 1),
        ("2026-11-01 10:00:00", "b-svc", "go", "d1", "r1", 0, 2000, 20, 0, 0, 0, 0.0, 0, 1, 1),
        ("2026-11-02 10:00:00", "b-svc", "go", "d2", "r2", 1, 2000, 20, 4, 4, 0, 20.0, 0, 1, 1),
        ("2026-11-03 10:00:00", "b-svc", "go", "d3", "r3", 2, 2000, 20, 4, 4, 0, 20.0, 0, 1, 1),
        ("2026-11-04 10:00:00", "b-svc", "go", "d4", "r4", 3, 2000, 20, 4, 4, 0, 20.1, 0, 1, 1),
    ]
    vals = ",".join("(" + ",".join(repr(v) if isinstance(v, str) else str(v) for v in r) + ")" for r in rows)
    s.query(ins + vals)
    s.query("INSERT INTO capstone.planted_issues VALUES ('a-svc','P1','x.py',1,2,'off-by-one','high','d'),('a-svc','P2','y.py',3,4,'null','medium','d'),"
            "('b-svc','P3','z.go',5,6,'race','high','d')")
    s.query("INSERT INTO capstone.issues_filed (repo, issue_number, fingerprint, title, severity, agent_run_id, file, line) VALUES "
            "('a-svc',1,'f1','t','high','run1','x.py',1),('a-svc',2,'f2','t','low','run1','z.py',9)")
    s.query("INSERT INTO capstone.issue_matches (repo, issue_number, planted_id) VALUES ('a-svc',1,'P1'),('a-svc',1,'P1')")
    s.query("INSERT INTO capstone.agent_runs (agent_run_id, repo, iteration, model, prompt_version, duration_s, outcome, cost_usd) VALUES "
            "('run1','a-svc',1,'m','v1',60,'ok',2.5),('run2','a-svc',2,'m','v1',60,'ok',1.5)")
    return s


def named_queries():
    out = {}
    for block in re.split(r"-- Name: ", (SQL / "queries.sql").read_text())[1:]:
        name, _, body = block.partition("\n")
        out[name.split()[0]] = body.strip().rstrip(";")
    return out


def rows(db, q):
    return [r.split(",") for r in str(db.query(q, "CSV")).strip().splitlines()]


def test_every_named_query_runs(db):
    for name, q in named_queries().items():
        db.query(q, "CSV")  # raises on a syntax or type error


def test_baseline_vs_latest(db):
    r = {x[0].strip('"'): x for x in rows(db, named_queries()["baseline_vs_latest"])}
    assert float(r["a-svc"][3]) == pytest.approx(42.5)
    assert float(r["b-svc"][3]) == pytest.approx(0.1, abs=0.01) or float(r["b-svc"][3]) == pytest.approx(20.1)


def test_stuck_repos_finds_only_b(db):
    r = rows(db, named_queries()["stuck_repos"])
    assert [x[0].strip('"') for x in r] == ["b-svc"]


def test_planted_recall(db):
    r = rows(db, named_queries()["planted_bug_recall"])[0]
    assert r[0] == "3" and r[1] == "1" and float(r[2]) == pytest.approx(33.3)
    assert float(r[5]) == pytest.approx(50.0)


def test_portfolio_totals(db):
    r = rows(db, named_queries()["portfolio_totals"])[0]
    assert r[0] == "2" and r[1] == "3150"


def test_cost_per_point(db):
    r = rows(db, named_queries()["cost_per_coverage_point"])[0]
    assert r[0].strip('"') == "a-svc" and float(r[1]) == pytest.approx(4.0) and float(r[2]) == pytest.approx(42.5)
    assert float(r[3]) == pytest.approx(0.09)


def test_every_dashboard_query_runs(db):
    """Extract rawSql from the generated Grafana JSON, replace the plugin macros with plain SQL, and run it."""
    import json
    import subprocess
    import sys
    dash = SQL.parent / "dashboards"
    subprocess.run([sys.executable, str(dash / "build_capstone_dashboards.py")], check=True, capture_output=True)
    n = 0
    for f in dash.glob("capstone-*.json"):
        for p in json.loads(f.read_text())["panels"]:
            sql = p["targets"][0]["rawSql"]
            sql = sql.replace("$__timeFilter(ts)", "1").replace("$__timeInterval(ts)", "toStartOfHour(ts)").replace("$repo", "a-svc")
            db.query(sql, "CSV")
            n += 1
    assert n == 16
