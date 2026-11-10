#!/usr/bin/env python3
"""ship.py: insert JSON documents into ClickHouse over its HTTP interface (stdlib only, so it runs in any image).

  python3 measure.py --dir . | python3 ship.py                         # one document from stdin into capstone.repo_measurements
  python3 ship.py --table capstone.issues_filed --file issue.json      # a different table
  python3 ship.py --dry-run < m.json                                    # print the request, send nothing

Environment: CLICKHOUSE_URL (default http://clickhouse.observability.svc.cluster.local:8123), CLICKHOUSE_USER, CLICKHOUSE_PASSWORD.
The password comes from a Secret (Days 11/13), never a flag and never a file in git. Rows are immutable: this tool only INSERTs.
Retries 3 times with backoff on network errors and 5xx; a 4xx (bad column, bad type) fails immediately because retrying cannot help.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def insert_rows(rows, table="capstone.repo_measurements", url=None, user=None, password=None, retries=3, dry_run=False):
    url = url or os.environ.get("CLICKHOUSE_URL", "http://clickhouse.observability.svc.cluster.local:8123")
    user = user or os.environ.get("CLICKHOUSE_USER", "default")
    password = password if password is not None else os.environ.get("CLICKHOUSE_PASSWORD", "")
    query = f"INSERT INTO {table} FORMAT JSONEachRow"
    body = "\n".join(json.dumps(r) for r in rows).encode()
    full = url.rstrip("/") + "/?" + urllib.parse.urlencode({"query": query, "date_time_input_format": "best_effort"})
    if dry_run:
        print(f"POST {full}\n{body.decode()}")
        return len(rows)
    req = urllib.request.Request(full, data=body, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            return len(rows)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == retries:
                raise SystemExit(f"ship.py: ClickHouse said {e.code}: {e.read().decode()[:300]}")
        except urllib.error.URLError as e:
            if attempt == retries:
                raise SystemExit(f"ship.py: cannot reach {url}: {e.reason}")
        time.sleep(2 ** attempt)


def query_rows(sql, url=None, user=None, password=None):
    """Run a SELECT and return a list of dicts (FORMAT JSONEachRow is appended)."""
    url = url or os.environ.get("CLICKHOUSE_URL", "http://clickhouse.observability.svc.cluster.local:8123")
    user = user or os.environ.get("CLICKHOUSE_USER", "default")
    password = password if password is not None else os.environ.get("CLICKHOUSE_PASSWORD", "")
    req = urllib.request.Request(url.rstrip("/") + "/?" + urllib.parse.urlencode({"query": sql + " FORMAT JSONEachRow"}), method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return [json.loads(ln) for ln in r.read().decode().splitlines() if ln.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--table", default="capstone.repo_measurements")
    ap.add_argument("--file", help="JSON or JSON-lines file (default: stdin)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    text = open(a.file).read() if a.file else sys.stdin.read()
    rows = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    n = insert_rows(rows, table=a.table, dry_run=a.dry_run)
    print(f"ship.py: inserted {n} row(s) into {a.table}", file=sys.stderr)


if __name__ == "__main__":
    main()
