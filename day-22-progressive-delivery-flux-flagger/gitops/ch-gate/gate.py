"""A Flagger webhook gate that asks ClickHouse whether the CANARY pods are healthy.

Flagger does not have ClickHouse as a built-in metric provider, so this small service stands in: Flagger calls it as a
"rollout" webhook on every analysis interval; any non-2xx answer counts as a failed check.

Flagger POSTs JSON such as:
  {"name": "podinfo", "namespace": "podinfo", "phase": "Progressing",
   "metadata": {"service": "shop-frontend", "max_error_pct": "5", "minutes": "2", "min_requests": "20"}}

The gate looks at server spans of `service` in the last `minutes` minutes, only from pods whose name does NOT contain
"-primary-" (Flagger names the stable pods <deployment>-primary-<hash>), and fails when the error percentage is above
`max_error_pct`. Fewer than `min_requests` spans is treated as "not enough data": it passes but says so.

This relies on spans carrying the resource attribute k8s.pod.name. Check with:
  SELECT DISTINCT ResourceAttributes['k8s.pod.name'] FROM otel.otel_traces LIMIT 10
"""
import json
import os
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

CLICKHOUSE_URL = os.environ.get("CLICKHOUSE_URL", "http://clickhouse.observability:8123")
CLICKHOUSE_USER = os.environ.get("CLICKHOUSE_USER", "otel")
CLICKHOUSE_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "")


def build_query(service: str, minutes: int) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", service):
        raise ValueError("service name has unexpected characters")
    return (
        "SELECT count() AS requests, "
        "countIf(StatusCode IN ('Error', 'STATUS_CODE_ERROR')) AS errors "
        "FROM otel.otel_traces "
        f"WHERE Timestamp > now() - INTERVAL {int(minutes)} MINUTE "
        "AND SpanKind IN ('Server', 'SPAN_KIND_SERVER') "
        f"AND ServiceName = '{service}' "
        "AND ResourceAttributes['k8s.pod.name'] NOT LIKE '%-primary-%' "
        "FORMAT JSON"
    )


def query_clickhouse(sql: str) -> dict:
    url = CLICKHOUSE_URL + "/?" + urllib.parse.urlencode({"user": CLICKHOUSE_USER, "password": CLICKHOUSE_PASSWORD})
    req = urllib.request.Request(url, data=sql.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["data"][0]


def decide(requests: int, errors: int, max_error_pct: float, min_requests: int) -> tuple[int, str]:
    if requests < min_requests:
        return 200, f"only {requests} canary requests (need {min_requests}): not enough data, passing"
    pct = 100.0 * errors / requests
    if pct > max_error_pct:
        return 500, f"canary error rate {pct:.1f}% > {max_error_pct}% ({errors}/{requests})"
    return 200, f"canary error rate {pct:.1f}% <= {max_error_pct}% ({errors}/{requests})"


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, message: str) -> None:
        body = json.dumps({"message": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # health check for Kubernetes probes
        self._reply(200, "ok")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            meta = (json.loads(self.rfile.read(length) or b"{}").get("metadata") or {})
            service = meta["service"]
            row = query_clickhouse(build_query(service, int(meta.get("minutes", 2))))
            code, message = decide(int(row["requests"]), int(row["errors"]),
                                   float(meta.get("max_error_pct", 5)), int(meta.get("min_requests", 20)))
        except Exception as exc:  # any failure to decide must fail the check, never silently pass
            code, message = 500, f"gate error: {exc}"
        print(code, message, flush=True)
        self._reply(code, message)


if __name__ == "__main__":
    HTTPServer(("", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
