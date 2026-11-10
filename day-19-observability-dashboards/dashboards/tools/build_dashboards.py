#!/usr/bin/env python3
"""Generate the Grafana dashboard JSON files in ../grafana/.

Why a generator at all? Grafana dashboard JSON is long and repetitive. Keeping the SQL here, in readable
Python, makes reviews easier; the generated JSON is ALSO committed because that is what Grafana loads.
Change the SQL here, run this script, and commit both. (You can also edit dashboards in the Grafana UI, export
the JSON, and commit that instead; either way the repository is the source of truth.)

    python3 day-19-observability-dashboards/dashboards/tools/build_dashboards.py

Assumptions to verify against YOUR versions (see the lesson): ClickHouse exporter column names,
span kind and status strings, metric names, and the ClickHouse data source's query model.
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "grafana"
DS = {"type": "grafana-clickhouse-datasource", "uid": "clickhouse"}
ERR_STATUS = "('Error', 'STATUS_CODE_ERROR')"
ERR_SEV = "('ERROR', 'Error', 'error', 'FATAL', 'Fatal', 'fatal')"
SERVER_KIND = "('Server', 'SPAN_KIND_SERVER')"
SVC = "$__conditionalAll(ServiceName IN ($service), $service)"
CLUSTER_T = "ResourceAttributes['k8s.cluster.name'] IN ($cluster)"
G = "otel.otel_metrics_gauge"

_ids = {"n": 0}


def _ref():
    _ids["n"] += 1
    return chr(ord("A") + (_ids["n"] - 1) % 26)


def target(sql, kind="timeseries"):
    fmt = {"timeseries": 0, "table": 1, "logs": 2}[kind]
    return {"datasource": DS, "editorType": "sql", "format": fmt, "queryType": kind,
            "rawSql": " ".join(sql.split()), "refId": "A"}


def panel(pid, title, ptype, x, y, w, h, sql, kind="timeseries", unit=None, description="",
          thresholds=None, options=None, overrides=None, stacking=None, decimals=None):
    defaults = {}
    if unit:
        defaults["unit"] = unit
    if decimals is not None:
        defaults["decimals"] = decimals
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
    if stacking:
        defaults["custom"] = {"stacking": {"mode": "normal", "group": "A"}, "fillOpacity": 60}
    p = {"id": pid, "type": ptype, "title": title, "description": description, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": [target(sql, kind)],
         "fieldConfig": {"defaults": defaults, "overrides": overrides or []}, "options": options or {}}
    return p


def row(pid, title, y):
    return {"id": pid, "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def qvar(name, label, sql, multi=True, include_all=True):
    return {"name": name, "label": label, "type": "query", "datasource": DS, "query": " ".join(sql.split()),
            "definition": " ".join(sql.split()), "refresh": 2, "multi": multi, "includeAll": include_all,
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]} if include_all else {},
            "sort": 1}


def dashboard(uid, title, tags, panels, variables, links=None, refresh="30s", time_from="now-1h"):
    return {"uid": uid, "title": title, "tags": tags, "timezone": "browser", "schemaVersion": 39, "version": 1,
            "editable": True, "refresh": refresh, "time": {"from": time_from, "to": "now"},
            "graphTooltip": 1, "templating": {"list": variables}, "panels": panels, "links": links or [],
            "annotations": {"list": []}}


def nav_links(current):
    items = [("service-overview-red", "Service Overview (RED)"), ("logs-and-traces", "Application Logs & Traces"),
             ("kubernetes-infra", "Kubernetes / Infra"), ("golden-signals-home", "Home: Golden signals")]
    return [{"title": t, "type": "link", "url": f"/d/{u}", "keepTime": True, "includeVars": True,
             "targetBlank": False, "icon": "dashboard"} for u, t in items if u != current]


def trace_link():
    return [{"matcher": {"id": "byName", "options": "TraceId"},
             "properties": [{"id": "links", "value": [{"title": "Open this trace in Logs & Traces",
                             "url": "/d/logs-and-traces?var-trace_id=${__value.raw}&${__url_time_range}"}]}]}]


SERVICE_VAR = qvar("service", "Service", "SELECT DISTINCT ServiceName FROM otel.otel_traces WHERE $__timeFilter(Timestamp) ORDER BY 1")
CLUSTER_VAR = qvar("cluster", "Cluster", f"SELECT DISTINCT ResourceAttributes['k8s.cluster.name'] FROM {G} WHERE $__timeFilter(TimeUnix) ORDER BY 1")
NS_VAR = qvar("namespace", "Namespace", f"SELECT DISTINCT ResourceAttributes['k8s.namespace.name'] FROM {G} WHERE $__timeFilter(TimeUnix) AND ResourceAttributes['k8s.cluster.name'] IN ($cluster) ORDER BY 1")
POD_VAR = qvar("pod", "Pod", f"SELECT DISTINCT ResourceAttributes['k8s.pod.name'] FROM {G} WHERE $__timeFilter(TimeUnix) AND ResourceAttributes['k8s.namespace.name'] IN ($namespace) ORDER BY 1")

# ---- reusable SQL ----------------------------------------------------------------------------------------
RATE = f"""SELECT $__timeInterval(Timestamp) AS time, ServiceName, count() / $__interval_s AS rps
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}
 GROUP BY time, ServiceName ORDER BY time"""
ERRPCT = f"""SELECT $__timeInterval(Timestamp) AS time, ServiceName,
 100 * countIf(StatusCode IN {ERR_STATUS}) / count() AS error_pct
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}
 GROUP BY time, ServiceName ORDER BY time"""
LAT = f"""SELECT $__timeInterval(Timestamp) AS time,
 quantile(0.50)(Duration) / 1e6 AS p50, quantile(0.95)(Duration) / 1e6 AS p95, quantile(0.99)(Duration) / 1e6 AS p99
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}
 GROUP BY time ORDER BY time"""
ERRLOGS = f"""SELECT Timestamp AS timestamp, Body AS body, SeverityText AS level, ServiceName AS service, TraceId AS traceID
 FROM otel.otel_logs WHERE $__timeFilter(Timestamp) AND SeverityText IN {ERR_SEV} AND {SVC}
 ORDER BY Timestamp DESC LIMIT 200"""


def build_red():
    panels = [
        row(100, "Traffic, errors, latency", 0),
        panel(1, "Request rate (req/s)", "timeseries", 0, 1, 8, 7, RATE, unit="reqps", description="Server spans per second, per service."),
        panel(2, "Error rate (%)", "timeseries", 8, 1, 8, 7, ERRPCT, unit="percent",
              thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}],
              description="Share of server spans with an error status."),
        panel(3, "Latency p50 / p95 / p99 (ms)", "timeseries", 16, 1, 8, 7, LAT, unit="ms",
              description="Percentiles of server span duration. Duration is stored in nanoseconds; we divide by 1e6."),
        row(101, "Right now", 8),
        panel(4, "Error rate, last interval", "stat", 0, 9, 6, 4,
              f"""SELECT 100 * countIf(StatusCode IN {ERR_STATUS}) / count() AS error_pct FROM otel.otel_traces
 WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}""", kind="table", unit="percent", decimals=2,
              thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}]),
        panel(5, "p95 latency, selected range", "stat", 6, 9, 6, 4,
              f"""SELECT quantile(0.95)(Duration) / 1e6 AS p95_ms FROM otel.otel_traces
 WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}""", kind="table", unit="ms", decimals=1,
              thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 300}, {"color": "red", "value": 800}]),
        panel(6, "Requests, selected range", "stat", 12, 9, 6, 4,
              f"""SELECT count() AS requests FROM otel.otel_traces
 WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}""", kind="table"),
        panel(7, "Services reporting", "stat", 18, 9, 6, 4,
              """SELECT uniqExact(ServiceName) AS services FROM otel.otel_traces WHERE $__timeFilter(Timestamp)""", kind="table"),
        row(102, "Where it hurts", 13),
        panel(8, "Slowest endpoints (p95)", "table", 0, 14, 12, 9,
              f"""SELECT ServiceName, SpanName AS endpoint, count() AS requests,
 round(quantile(0.95)(Duration) / 1e6, 1) AS p95_ms, round(quantile(0.99)(Duration) / 1e6, 1) AS p99_ms,
 round(100 * countIf(StatusCode IN {ERR_STATUS}) / count(), 2) AS error_pct
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}
 GROUP BY ServiceName, SpanName ORDER BY p95_ms DESC LIMIT 15""", kind="table"),
        panel(9, "Recent error logs", "logs", 12, 14, 12, 9, ERRLOGS, kind="logs",
              options={"showTime": True, "wrapLogMessage": True, "enableLogDetails": True, "sortOrder": "Descending"},
              description="Click a line to see its fields; traceID is shown so you can open the trace."),
        panel(10, "Slowest requests (click a TraceId)", "table", 0, 23, 24, 8,
              f"""SELECT Timestamp, TraceId, ServiceName, SpanName, round(Duration / 1e6, 1) AS ms, StatusCode
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND SpanKind IN {SERVER_KIND} AND {SVC}
 ORDER BY Duration DESC LIMIT 20""", kind="table", overrides=trace_link()),
    ]
    return dashboard("service-overview-red", "Service Overview (RED)", ["course", "app", "red"], panels,
                     [SERVICE_VAR], nav_links("service-overview-red"))


def build_logs_traces():
    panels = [
        row(100, "Logs", 0),
        panel(1, "Log volume by severity", "timeseries", 0, 1, 12, 7,
              f"""SELECT $__timeInterval(Timestamp) AS time, SeverityText AS severity, count() AS lines
 FROM otel.otel_logs WHERE $__timeFilter(Timestamp) AND {SVC} GROUP BY time, severity ORDER BY time""", stacking=True),
        panel(2, "Top error messages", "table", 12, 1, 12, 7,
              f"""SELECT ServiceName, substring(Body, 1, 120) AS message, count() AS occurrences, max(Timestamp) AS last_seen
 FROM otel.otel_logs WHERE $__timeFilter(Timestamp) AND SeverityText IN {ERR_SEV} AND {SVC}
 GROUP BY ServiceName, message ORDER BY occurrences DESC LIMIT 15""", kind="table"),
        panel(3, "Logs (filter with the variables above; trace_id empty = all)", "logs", 0, 8, 24, 10,
              f"""SELECT Timestamp AS timestamp, Body AS body, SeverityText AS level, ServiceName AS service, TraceId AS traceID
 FROM otel.otel_logs WHERE $__timeFilter(Timestamp) AND {SVC}
 AND $__conditionalAll(SeverityText IN ($severity), $severity)
 AND ('${{trace_id}}' = '' OR TraceId = '${{trace_id}}')
 ORDER BY Timestamp DESC LIMIT 500""", kind="logs",
              options={"showTime": True, "wrapLogMessage": True, "enableLogDetails": True, "sortOrder": "Descending"}),
        row(101, "Traces", 18),
        panel(4, "Trace duration distribution (50 ms buckets)", "barchart", 0, 19, 12, 8,
              f"""SELECT toString(floor(Duration / 1e6 / 50) * 50) AS bucket_ms, count() AS spans
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND ParentSpanId = '' AND {SVC}
 GROUP BY bucket_ms ORDER BY toFloat64(bucket_ms)""", kind="table",
              options={"xField": "bucket_ms", "legend": {"showLegend": False}}),
        panel(5, "Service dependencies (calls)", "table", 12, 19, 12, 8,
              """SELECT p.ServiceName AS caller, c.ServiceName AS callee, count() AS calls,
 round(quantile(0.95)(c.Duration) / 1e6, 1) AS callee_p95_ms
 FROM otel.otel_traces AS c INNER JOIN otel.otel_traces AS p ON c.TraceId = p.TraceId AND c.ParentSpanId = p.SpanId
 WHERE $__timeFilter(c.Timestamp) AND $__timeFilter(p.Timestamp) AND p.ServiceName != c.ServiceName
 GROUP BY caller, callee ORDER BY calls DESC""", kind="table"),
        panel(6, "Slowest traces (click a TraceId)", "table", 0, 27, 24, 8,
              f"""SELECT Timestamp, TraceId, ServiceName, SpanName, round(Duration / 1e6, 1) AS ms, StatusCode
 FROM otel.otel_traces WHERE $__timeFilter(Timestamp) AND ParentSpanId = '' AND {SVC}
 ORDER BY Duration DESC LIMIT 20""", kind="table", overrides=trace_link()),
        panel(7, "Spans of the selected trace (set trace_id)", "table", 0, 35, 24, 8,
              """SELECT Timestamp, ServiceName, SpanName, SpanKind, SpanId, ParentSpanId, round(Duration / 1e6, 1) AS ms, StatusCode
 FROM otel.otel_traces WHERE '${trace_id}' != '' AND TraceId = '${trace_id}' ORDER BY Timestamp""", kind="table"),
    ]
    sev = qvar("severity", "Severity", "SELECT DISTINCT SeverityText FROM otel.otel_logs WHERE $__timeFilter(Timestamp) ORDER BY 1")
    tid = {"name": "trace_id", "label": "Trace id", "type": "textbox", "query": "", "current": {"text": "", "value": ""},
           "options": [{"selected": True, "text": "", "value": ""}]}
    return dashboard("logs-and-traces", "Application Logs & Traces", ["course", "app", "logs", "traces"], panels,
                     [SERVICE_VAR, sev, tid], nav_links("logs-and-traces"))


def gauge_q(metric, extra="", agg="avg"):
    return f"""SELECT $__timeInterval(TimeUnix) AS time, {{group}} AS series, {agg}(Value) AS value FROM {G}
 WHERE MetricName = '{metric}' AND $__timeFilter(TimeUnix) AND {CLUSTER_T} {extra}
 GROUP BY time, series ORDER BY time"""


def build_infra():
    NS = "AND ResourceAttributes['k8s.namespace.name'] IN ($namespace)"
    PODF = "AND ResourceAttributes['k8s.namespace.name'] IN ($namespace) AND ResourceAttributes['k8s.pod.name'] IN ($pod)"
    NODE = "ResourceAttributes['k8s.node.name']"
    NSG = "ResourceAttributes['k8s.namespace.name']"
    POD = "ResourceAttributes['k8s.pod.name']"
    panels = [
        row(100, "Nodes", 0),
        panel(1, "Node CPU (cores)", "timeseries", 0, 1, 8, 7, gauge_q("k8s.node.cpu.usage").replace("{group}", NODE), unit="none"),
        panel(2, "Node memory working set", "timeseries", 8, 1, 8, 7, gauge_q("k8s.node.memory.working_set").replace("{group}", NODE), unit="bytes"),
        panel(3, "Node pressure (1 = under pressure)", "timeseries", 16, 1, 8, 7,
              f"""SELECT $__timeInterval(TimeUnix) AS time, concat({NODE}, ' ', MetricName) AS series, max(Value) AS value FROM {G}
 WHERE MetricName IN ('k8s.node.condition_memory_pressure', 'k8s.node.condition_disk_pressure', 'k8s.node.condition_pid_pressure')
 AND $__timeFilter(TimeUnix) AND {CLUSTER_T} GROUP BY time, series ORDER BY time""",
              thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 1}],
              description="Needs node_conditions_to_report in the k8s_cluster receiver (set in cluster-values.yaml)."),
        row(101, "Namespaces", 8),
        panel(4, "CPU by namespace (cores)", "timeseries", 0, 9, 12, 7,
              f"""SELECT time, ns AS series, sum(v) AS value FROM (
 SELECT $__timeInterval(TimeUnix) AS time, {NSG} AS ns, {POD} AS pod, avg(Value) AS v FROM {G}
 WHERE MetricName = 'k8s.pod.cpu.usage' AND $__timeFilter(TimeUnix) AND {CLUSTER_T} GROUP BY time, ns, pod)
 GROUP BY time, series ORDER BY time""", stacking=True),
        panel(5, "Memory by namespace", "timeseries", 12, 9, 12, 7,
              f"""SELECT time, ns AS series, sum(v) AS value FROM (
 SELECT $__timeInterval(TimeUnix) AS time, {NSG} AS ns, {POD} AS pod, avg(Value) AS v FROM {G}
 WHERE MetricName = 'k8s.pod.memory.working_set' AND $__timeFilter(TimeUnix) AND {CLUSTER_T} GROUP BY time, ns, pod)
 GROUP BY time, series ORDER BY time""", unit="bytes", stacking=True),
        row(102, "Pods", 16),
        panel(6, "Pod CPU (cores)", "timeseries", 0, 17, 12, 8, gauge_q("k8s.pod.cpu.usage", PODF).replace("{group}", POD)),
        panel(7, "Pod memory working set", "timeseries", 12, 17, 12, 8, gauge_q("k8s.pod.memory.working_set", PODF).replace("{group}", POD), unit="bytes"),
        panel(8, "Memory vs limit (per pod, latest)", "table", 0, 25, 12, 8,
              f"""SELECT m.pod AS pod, round(m.mem / 1048576, 1) AS memory_mib, round(l.lim / 1048576, 1) AS limit_mib,
 round(100 * m.mem / l.lim, 1) AS percent_of_limit FROM
 (SELECT {POD} AS pod, argMax(Value, TimeUnix) AS mem FROM {G} WHERE MetricName = 'k8s.pod.memory.working_set'
   AND $__timeFilter(TimeUnix) AND {CLUSTER_T} {NS} GROUP BY pod) AS m
 INNER JOIN (SELECT {POD} AS pod, sum(Value) AS lim FROM {G} WHERE MetricName = 'k8s.container.memory_limit'
   AND $__timeFilter(TimeUnix) AND {CLUSTER_T} {NS} GROUP BY pod) AS l ON m.pod = l.pod
 WHERE l.lim > 0 ORDER BY percent_of_limit DESC LIMIT 20""", kind="table",
              description="Pods without a memory limit have no row (no limit to compare with): itself a finding."),
        panel(9, "Container restarts (increase in range)", "table", 12, 25, 12, 8,
              f"""SELECT {NSG} AS namespace, {POD} AS pod, ResourceAttributes['k8s.container.name'] AS container,
 max(Value) - min(Value) AS restarts FROM {G} WHERE MetricName = 'k8s.container.restarts'
 AND $__timeFilter(TimeUnix) AND {CLUSTER_T} {NS} GROUP BY namespace, pod, container HAVING restarts > 0 ORDER BY restarts DESC""",
              kind="table", description="If this stays empty but you know a pod restarted, the metric may be in otel_metrics_sum: check names."),
        panel(10, "Pods not Running (latest phase)", "table", 0, 33, 12, 7,
              f"""SELECT {NSG} AS namespace, {POD} AS pod, argMax(Value, TimeUnix) AS phase FROM {G}
 WHERE MetricName = 'k8s.pod.phase' AND $__timeFilter(TimeUnix) AND {CLUSTER_T} {NS} GROUP BY namespace, pod
 HAVING phase != 2 ORDER BY phase DESC""", kind="table",
              description="Phase codes: 1 Pending, 2 Running, 3 Succeeded, 4 Failed, 5 Unknown (check the receiver docs)."),
        row(103, "Workloads", 40),
        panel(11, "Replicas: desired vs available", "timeseries", 0, 41, 12, 8,
              f"""SELECT $__timeInterval(TimeUnix) AS time,
 concat(ResourceAttributes['k8s.deployment.name'], ' ', replaceOne(MetricName, 'k8s.deployment.', '')) AS series, max(Value) AS value
 FROM {G} WHERE MetricName IN ('k8s.deployment.desired', 'k8s.deployment.available') AND $__timeFilter(TimeUnix)
 AND {CLUSTER_T} {NS} GROUP BY time, series ORDER BY time"""),
        panel(12, "HPA replicas", "timeseries", 12, 41, 12, 8,
              f"""SELECT $__timeInterval(TimeUnix) AS time, concat(ResourceAttributes['k8s.hpa.name'], ' ', replaceOne(MetricName, 'k8s.hpa.', '')) AS series, max(Value) AS value
 FROM {G} WHERE MetricName IN ('k8s.hpa.current_replicas', 'k8s.hpa.desired_replicas') AND $__timeFilter(TimeUnix) AND {CLUSTER_T}
 GROUP BY time, series ORDER BY time""", description="Metric names depend on the receiver version: list them first."),
    ]
    return dashboard("kubernetes-infra", "Kubernetes / Infra", ["course", "infra", "kubernetes"], panels,
                     [CLUSTER_VAR, NS_VAR, POD_VAR], nav_links("kubernetes-infra"))


def build_home():
    panels = [
        row(100, "App (what users feel)", 0),
        panel(1, "Request rate (req/s)", "timeseries", 0, 1, 6, 6, RATE, unit="reqps"),
        panel(2, "Error rate (%)", "timeseries", 6, 1, 6, 6, ERRPCT, unit="percent"),
        panel(3, "Latency p50 / p95 / p99 (ms)", "timeseries", 12, 1, 12, 6, LAT, unit="ms"),
        row(101, "Platform (what the cluster is doing)", 7),
        panel(4, "Pod CPU (cores), top pods", "timeseries", 0, 8, 8, 7,
              f"""SELECT $__timeInterval(TimeUnix) AS time, ResourceAttributes['k8s.pod.name'] AS series, avg(Value) AS value FROM {G}
 WHERE MetricName = 'k8s.pod.cpu.usage' AND $__timeFilter(TimeUnix) AND ResourceAttributes['k8s.namespace.name'] = 'apps'
 AND ResourceAttributes['k8s.cluster.name'] IN ($cluster) GROUP BY time, series ORDER BY time"""),
        panel(5, "Pod memory, top pods", "timeseries", 8, 8, 8, 7,
              f"""SELECT $__timeInterval(TimeUnix) AS time, ResourceAttributes['k8s.pod.name'] AS series, avg(Value) AS value FROM {G}
 WHERE MetricName = 'k8s.pod.memory.working_set' AND $__timeFilter(TimeUnix) AND ResourceAttributes['k8s.namespace.name'] = 'apps'
 AND ResourceAttributes['k8s.cluster.name'] IN ($cluster) GROUP BY time, series ORDER BY time""", unit="bytes"),
        panel(6, "Restarts and not-ready pods", "stat", 16, 8, 8, 7,
              f"""SELECT sum(r) AS restarts_in_range FROM (SELECT max(Value) - min(Value) AS r FROM {G}
 WHERE MetricName = 'k8s.container.restarts' AND $__timeFilter(TimeUnix) AND ResourceAttributes['k8s.cluster.name'] IN ($cluster)
 GROUP BY ResourceAttributes['k8s.pod.name'], ResourceAttributes['k8s.container.name'])""", kind="table",
              thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 3}],
              description="Compare with the latency panel above: do spikes line up with restarts or CPU?"),
    ]
    return dashboard("golden-signals-home", "Home: Golden signals (app + platform)", ["course", "home"], panels,
                     [SERVICE_VAR, CLUSTER_VAR], nav_links("golden-signals-home"), time_from="now-30m")


for fname, build in [("service-overview-red.json", build_red), ("logs-and-traces.json", build_logs_traces),
                     ("kubernetes-infra.json", build_infra), ("golden-signals-home.json", build_home)]:
    (OUT / fname).write_text(json.dumps(build(), indent=2) + "\n")
    print("wrote", fname)
