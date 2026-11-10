"""Every table and query in metrics/, run on embedded ClickHouse (chdb) with seeded rows. Skips without chdb."""
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("chdb")
from chdb import session  # noqa: E402

SQL = Path(__file__).resolve().parent.parent / "metrics"


def statements(text):
    return [s.strip() for s in re.sub(r"--[^\n]*", "", text).split(";") if s.strip()]


def named():
    out = {}
    for block in re.split(r"-- name: ", (SQL / "queries.sql").read_text())[1:]:
        name, _, rest = block.partition("\n")
        out[name.strip()] = statements(rest)[0]
    return out


def ch(author, repo, tier, t0, merged_h, first_review_h, ci1, rework, escaped, failed, cost, tokens, cov=0.0, mut=0.0):
    from datetime import datetime, timedelta
    f = lambda d: d.strftime("%Y-%m-%d %H:%M:%S.000")  # noqa: E731
    t = datetime(2026, 11, 2, t0)
    return {"change_id": f"{repo}-{author}-{t0}-{tokens}", "repo": repo, "author_kind": author, "model_tier": tier, "first_commit_at": f(t), "opened_at": f(t + timedelta(hours=1)),
            "first_review_at": f(t + timedelta(hours=1 + first_review_h)), "merged_at": f(t + timedelta(hours=merged_h)), "deployed_at": None,
            "ci_first_pass": ci1, "review_rounds": 1, "reworked": rework, "escaped_defect": escaped, "caused_failure": failed, "cost_usd": cost, "tokens": tokens,
            "coverage_delta": cov, "mutation_delta": mut}


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    s = session.Session(str(tmp_path_factory.mktemp("ch")))
    for stmt in statements((SQL / "001_ai_tables.sql").read_text()):
        s.query(stmt)
    rows = [
        ch("human", "api", "", 9, 10, 2, 1, 0, 0, 0, 0, 0, 1.0, 2.0), ch("human", "api", "", 9, 20, 4, 1, 0, 0, 0, 0, 0, 1.0, 2.0),
        ch("ai", "api", "frontier", 9, 6, 1, 1, 0, 0, 0, 2.0, 500000), ch("ai", "api", "mid", 9, 8, 1, 0, 1, 0, 0, 0.5, 900000),
        ch("ai", "web", "mid", 9, 10, 1, 0, 1, 1, 1, 0.5, 9000000), ch("ai", "web", "small", 9, 12, 1, 0, 0, 0, 0, 0.1, 100),
    ]
    s.query("INSERT INTO ai.changes FORMAT JSONEachRow " + "\n".join(json.dumps(r) for r in rows))
    inc = [{"incident_id": "i1", "repo": "api", "opened_at": "2026-11-02 10:00:00.000", "resolved_at": "2026-11-02 14:00:00.000", "resolved_by": "human"},
           {"incident_id": "i2", "repo": "api", "opened_at": "2026-11-02 10:00:00.000", "resolved_at": "2026-11-02 11:00:00.000", "resolved_by": "ai-assisted"}]
    s.query("INSERT INTO ai.incidents FORMAT JSONEachRow " + "\n".join(json.dumps(r) for r in inc))
    s.query("INSERT INTO ai.test_runs VALUES ('2026-11-02','t1',100,5),('2026-11-02','t2',100,1),('2026-11-03','t1',100,0)")
    return s


def run(db, name):
    return [r.split("\t") for r in db.query(named()[name], "TSV").bytes().decode().strip().splitlines()]


def test_all_queries_parse_and_return_rows(db):
    for n in named():
        assert run(db, n), n


def test_lead_time(db):
    r = {x[0]: x for x in run(db, "lead_time_hours_by_author")}
    assert (r["human"][1], float(r["human"][2])) == ("2", 15.0)
    assert (r["ai"][1], float(r["ai"][2])) == ("4", 9.0)


def test_quality_by_author(db):
    r = {x[0]: x for x in run(db, "quality_by_author")}
    assert float(r["human"][2]) == 100.0 and float(r["ai"][2]) == 25.0
    assert float(r["ai"][3]) == 50.0 and float(r["ai"][4]) == 25.0 and float(r["ai"][5]) == 25.0
    assert float(r["human"][6]) == 1.0 and float(r["human"][7]) == 2.0


def test_cost_per_clean_change_penalises_rework(db):
    r = {x[0]: x for x in run(db, "cost_per_accepted_change")}
    assert float(r["frontier"][3]) == 2.0 and float(r["mid"][3]) == 0.5
    assert r["mid"][4] == "\\N"  # both mid changes needed rework: no clean change to divide by


def test_tokens_vs_outcomes_shows_the_expensive_repo_is_not_the_best(db):
    r = run(db, "tokens_vs_outcomes")
    assert r[0][0] == "web" and float(r[0][4]) > float(r[1][4])


def test_ttr_and_flaky(db):
    assert {x[0]: float(x[2]) for x in run(db, "time_to_resolve_hours")} == {"ai-assisted": 1.0, "human": 4.0}
    assert [float(x[1]) for x in run(db, "flaky_rate")] == [3.0, 0.0]
