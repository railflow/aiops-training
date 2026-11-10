#!/usr/bin/env python3
"""Generate the two capstone Grafana dashboards (portfolio, repo drilldown) as JSON, like day-19-observability-dashboards/dashboards/tools/build_dashboards.py does for the course dashboards.

    python3 build_capstone_dashboards.py          # writes capstone-portfolio.json and capstone-repo.json next to this file

Load them with the same ConfigMap + sidecar mechanism as the Day 19 dashboards (kustomization.yaml here). The data source uid is `clickhouse`
(Day 19). These are a SKELETON: the SQL is tested against a ClickHouse engine, the panel layout and options were NOT opened in a real Grafana by the author;
import them, fix what you dislike, and re-export. Macros used ($__timeFilter) belong to the ClickHouse data source plugin: check its docs for your version.
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent
DS = {"type": "grafana-clickhouse-datasource", "uid": "clickhouse"}

LATEST = ("(SELECT repo, argMax(language, ts) AS language, argMax(lines_of_code, ts) AS loc, argMax(line_coverage_pct, ts) AS cov, argMax(vuln_critical, ts) AS vc, "
          "argMax(vuln_high, ts) AS vh, argMax(secrets_found, ts) AS secrets, argMax(test_count, ts) AS tests, argMax(tests_failed, ts) AS failed "
          "FROM capstone.repo_measurements GROUP BY repo)")
FIRST = "(SELECT repo, argMin(line_coverage_pct, ts) AS cov FROM capstone.repo_measurements WHERE iteration = 0 GROUP BY repo)"


def panel(pid, title, ptype, x, y, w, h, sql, kind="table", unit=None, description="", thresholds=None):
    d = {}
    if unit:
        d["unit"] = unit
    if thresholds:
        d["thresholds"] = {"mode": "absolute", "steps": thresholds}
    return {"id": pid, "type": ptype, "title": title, "description": description, "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "targets": [{"datasource": DS, "editorType": "sql", "format": 0 if kind == "timeseries" else 1, "queryType": kind, "rawSql": " ".join(sql.split()), "refId": "A"}],
            "fieldConfig": {"defaults": d, "overrides": []}, "options": {}}


GREEN_RED = [{"color": "red", "value": None}, {"color": "orange", "value": 30}, {"color": "green", "value": 60}]

PORTFOLIO = [
    panel(1, "Repos measured", "stat", 0, 0, 4, 4, f"SELECT count() AS repos FROM {LATEST}"),
    panel(2, "Total lines of code", "stat", 4, 0, 4, 4, f"SELECT sum(loc) AS lines FROM {LATEST}"),
    panel(3, "Average line coverage (latest per repo)", "stat", 8, 0, 5, 4, f"SELECT round(avg(cov), 1) AS avg_cov FROM {LATEST}", unit="percent", thresholds=GREEN_RED),
    panel(4, "Critical + high vulnerabilities", "stat", 13, 0, 5, 4, f"SELECT sum(vc) + sum(vh) AS vulns FROM {LATEST}", description="Null when trivy was not available in the measure image."),
    panel(5, "Planted bugs found (recall)", "stat", 18, 0, 6, 4,
          "SELECT round(100 * (SELECT uniqExact(repo, planted_id) FROM capstone.issue_matches) / nullIf((SELECT count() FROM capstone.planted_issues), 0), 1) AS recall_pct", unit="percent",
          description="Uses the answer key. Never expose the key to the agents: only this dashboard reads it."),
    panel(6, "Average coverage over time", "timeseries", 0, 4, 12, 8,
          "SELECT $__timeInterval(ts) AS time, avg(line_coverage_pct) AS avg_line_coverage FROM capstone.repo_measurements WHERE $__timeFilter(ts) AND line_coverage_pct IS NOT NULL GROUP BY time ORDER BY time",
          kind="timeseries", unit="percent", description="Averages every measurement in the bucket, including baselines of repos not yet touched: read the drilldown for per-repo truth."),
    panel(7, "Repos by language", "barchart", 12, 4, 12, 8, f"SELECT language, count() AS repos FROM {LATEST} GROUP BY language ORDER BY repos DESC"),
    panel(8, "Worst 15 repos (lowest coverage, then most vulnerabilities)", "table", 0, 12, 12, 9,
          f"SELECT repo, language, round(cov, 1) AS coverage_pct, vc AS critical, vh AS high, secrets, failed AS tests_failed FROM {LATEST} ORDER BY cov ASC, vc DESC LIMIT 15"),
    panel(9, "Biggest gains (baseline to latest)", "table", 12, 12, 12, 9,
          f"SELECT l.repo AS repo, round(f.cov, 1) AS baseline_pct, round(l.cov, 1) AS latest_pct, round(l.cov - f.cov, 1) AS gain_pct FROM {LATEST} AS l JOIN {FIRST} AS f ON l.repo = f.repo ORDER BY gain_pct DESC LIMIT 15"),
    panel(10, "Cost per coverage point", "table", 0, 21, 12, 8,
          "SELECT a.repo AS repo, round(sum(a.cost_usd), 2) AS cost_usd, round(any(g.gain), 1) AS gain_pct, round(sum(a.cost_usd) / nullIf(any(g.gain), 0), 2) AS usd_per_point "
          "FROM capstone.agent_runs AS a LEFT JOIN (SELECT repo, argMax(line_coverage_pct, ts) - argMinIf(line_coverage_pct, ts, iteration = 0) AS gain FROM capstone.repo_measurements WHERE line_coverage_pct IS NOT NULL GROUP BY repo) AS g ON g.repo = a.repo "
          "GROUP BY a.repo ORDER BY usd_per_point DESC", description="A repo with cost and zero gain has usd_per_point NULL: that is the signal."),
    panel(11, "Agent runs by outcome", "barchart", 12, 21, 12, 8, "SELECT outcome, count() AS runs FROM capstone.agent_runs GROUP BY outcome ORDER BY runs DESC"),
]

REPO = [
    panel(1, "Coverage over time", "timeseries", 0, 0, 12, 8,
          "SELECT ts AS time, line_coverage_pct AS line, branch_coverage_pct AS branch FROM capstone.repo_measurements WHERE repo = '$repo' AND $__timeFilter(ts) ORDER BY ts", kind="timeseries", unit="percent"),
    panel(2, "Tests", "timeseries", 12, 0, 12, 8,
          "SELECT ts AS time, tests_passed AS passed, tests_failed AS failed FROM capstone.repo_measurements WHERE repo = '$repo' AND $__timeFilter(ts) ORDER BY ts", kind="timeseries"),
    panel(3, "Measurements (every iteration)", "table", 0, 8, 24, 8,
          "SELECT ts, iteration, commit_sha, round(line_coverage_pct, 1) AS line_pct, test_count, tests_failed, vuln_critical, vuln_high, secrets_found, agent_run_id FROM capstone.repo_measurements WHERE repo = '$repo' ORDER BY ts DESC LIMIT 50"),
    panel(4, "Issues the agents filed", "table", 0, 16, 12, 8,
          "SELECT ts, issue_number, severity, category, file, line, failing_test, title FROM capstone.issues_filed WHERE repo = '$repo' ORDER BY ts DESC"),
    panel(5, "Agent runs", "table", 12, 16, 12, 8,
          "SELECT ts, iteration, outcome, round(cost_usd, 2) AS cost_usd, duration_s, commits, model, prompt_version FROM capstone.agent_runs WHERE repo = '$repo' ORDER BY ts DESC"),
]


def dash(uid, title, panels, variables=()):
    return {"uid": uid, "title": title, "tags": ["capstone"], "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True, "refresh": "1m",
            "time": {"from": "now-7d", "to": "now"}, "graphTooltip": 1, "templating": {"list": list(variables)}, "panels": panels, "links": [], "annotations": {"list": []}}


REPO_VAR = {"name": "repo", "label": "Repo", "type": "query", "datasource": DS, "query": "SELECT DISTINCT repo FROM capstone.repo_measurements ORDER BY repo",
            "definition": "SELECT DISTINCT repo FROM capstone.repo_measurements ORDER BY repo", "refresh": 2, "multi": False, "includeAll": False, "sort": 1}

if __name__ == "__main__":
    (OUT / "capstone-portfolio.json").write_text(json.dumps(dash("capstone-portfolio", "Capstone: portfolio", PORTFOLIO), indent=2) + "\n")
    (OUT / "capstone-repo.json").write_text(json.dumps(dash("capstone-repo", "Capstone: repo drilldown", REPO, [REPO_VAR]), indent=2) + "\n")
    print("wrote capstone-portfolio.json and capstone-repo.json")
