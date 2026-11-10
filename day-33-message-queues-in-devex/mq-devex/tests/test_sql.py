"""The bus_events DDL and every named query, run against embedded ClickHouse (chdb) with seeded rows. Skips without chdb.
chdb bundles a newer ClickHouse than the course's 24.8; re-run against your server."""
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("chdb")
from chdb import session  # noqa: E402

SQL = Path(__file__).resolve().parent.parent / "sql"


def statements(text):
    return [s.strip() for s in re.sub(r"--[^\n]*", "", text).split(";") if s.strip()]


def named_queries():
    out = {}
    for block in re.split(r"-- name: ", (SQL / "queries.sql").read_text())[1:]:
        name, _, rest = block.partition("\n")
        out[name.strip()] = statements(rest)[0]
    return out


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    s = session.Session(str(tmp_path_factory.mktemp("ch")))
    for stmt in statements((SQL / "001_bus_events.sql").read_text()):
        s.query(stmt)

    def row(cid, t, typ, data=None, eid=None):
        return {"event_time": t, "event_id": eid or f"{cid}-{typ}", "correlation_id": cid, "causation_id": "", "type": typ, "source": "t", "entity": "e",
                "data": json.dumps(data or {})}

    rows = [
        row("c1", "2026-11-05 10:00:00.000", "ci.build.completed"), row("c1", "2026-11-05 10:00:01.000", "ci.gate.passed"),
        row("c1", "2026-11-05 10:00:03.500", "ci.deploy.completed"),
        row("c2", "2026-11-05 10:05:00.000", "ci.build.completed"), row("c2", "2026-11-05 10:05:02.000", "ci.gate.failed"),
        row("c3", "2026-11-05 10:06:00.000", "ci.build.completed"),
        row("c3", "2026-11-05 10:06:01.000", "devex.dlq.entry", {"worker": "uitest", "reason": "gave up after 4 deliveries: boom"}),
        row("c4", "2026-11-05 10:07:00.000", "ci.compare.result", {"agree": True}), row("c5", "2026-11-05 10:07:01.000", "ci.compare.result", {"agree": False}),
        row("c4", "2026-11-05 10:07:02.000", "ci.completed", {"impl": "legacy", "shadow": False, "duration_ms": 300}),
        row("c4", "2026-11-05 10:07:03.000", "ci.completed", {"impl": "new", "shadow": True, "duration_ms": 100}),
        row("c6", "2026-11-05 10:07:04.000", "ci.completed", {"impl": "new", "shadow": False, "duration_ms": 120}),
    ]
    s.query("INSERT INTO bus.events FORMAT JSONEachRow " + "\n".join(json.dumps(r) for r in rows))
    return s


def q(db, name, **params):
    sql = named_queries()[name]
    for k, v in params.items():
        sql = sql.replace("{" + k + ":String}", "'" + v + "'")
    return [r for r in db.query(sql, "JSONEachRow").bytes().decode().splitlines() if r]


def test_trace_is_ordered(db):
    rows = [json.loads(r) for r in q(db, "trace_by_correlation", cid="c1")]
    assert [r["type"] for r in rows] == ["ci.build.completed", "ci.gate.passed", "ci.deploy.completed"]


def test_lead_time_only_for_deployed_runs(db):
    rows = [json.loads(r) for r in q(db, "pipeline_lead_time")]
    assert len(rows) == 1 and rows[0]["correlation_id"] == "c1" and int(rows[0]["lead_ms"]) == 3500


def test_events_per_type_and_dlq(db):
    counts = {json.loads(r)["type"]: int(json.loads(r)["n"]) for r in q(db, "events_per_type")}
    assert counts["ci.build.completed"] == 3
    dl = [json.loads(r) for r in q(db, "dead_letters")]
    assert dl[0]["worker"] == "uitest" and "gave up" in dl[0]["reason"]


def test_shadow_agreement_and_impl_mix(db):
    a = json.loads(q(db, "shadow_agreement")[0])
    assert (int(a["agreed"]), int(a["disagreed"])) == (1, 1) and float(a["agreement_pct"]) == 50.0
    mix = {json.loads(r)["impl"]: json.loads(r) for r in q(db, "impl_mix")}
    assert int(mix["legacy"]["runs"]) == 1 and int(mix["new"]["runs"]) == 1


def test_stuck_runs_query_runs(db):
    rows = [json.loads(r) for r in q(db, "stuck_runs")]
    assert {r["correlation_id"] for r in rows} == {"c3"}
