#!/usr/bin/env python3
"""file_issue.py: the ONLY way an agent reports a bug it found. Deduplicates, rate-limits, labels, and tags the issue for later scoring.

  file_issue.py --title "paginate drops the last item" --severity high --category off-by-one --file shop/rules.py --line 4 \
                --test test_paginate_last_page --body-file /tmp/body.md

Environment: FORGEJO_URL, FORGEJO_TOKEN (a per-run token injected as a Secret), REPO (org/name), AGENT_RUN_ID, MAX_ISSUES (default 10 per run).
Standard library only. Prints `FILED #N <url>` or `DUPLICATE #N` (both exit 0), exit 3 when the per-run cap is reached, exit 1 on API errors.

How dedupe works: a fingerprint = sha256(repo | file | test | normalised title)[:16] is written into a hidden HTML comment in the issue body, and Forgejo's
issue search (`GET /repos/{o}/{r}/issues?q=...`) is asked for it BEFORE creating. The hidden marker also carries file and line so a trusted job outside the
sandbox can match the issue against the answer key without the agent ever seeing it.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COUNTER = Path(os.environ.get("ISSUE_COUNTER_FILE", "/tmp/issues-filed-count"))


def call(method, path, body=None, retries=3):
    base = os.environ["FORGEJO_URL"].rstrip("/") + "/api/v1"
    for attempt in range(retries + 1):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, method=method)
        req.add_header("Authorization", "token " + os.environ["FORGEJO_TOKEN"])
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                continue
            raise SystemExit(f"file_issue.py: Forgejo said {e.code} for {method} {path}: {e.read().decode()[:200]}")


def fingerprint(repo, file, test, title):
    norm = re.sub(r"\W+", " ", title.lower()).strip()
    return hashlib.sha256(f"{repo}|{file}|{test}|{norm}".encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--severity", choices=["low", "medium", "high", "critical"], required=True)
    ap.add_argument("--category", default="bug")
    ap.add_argument("--file", default="")
    ap.add_argument("--line", type=int, default=0)
    ap.add_argument("--test", default="", help="name of the failing test that reproduces it")
    ap.add_argument("--repo", default=os.environ.get("REPO", ""))
    a = ap.parse_args()
    if not a.repo:
        sys.exit("file_issue.py: --repo or REPO is required (org/name)")
    body = Path(a.body_file).read_text() if a.body_file else a.body
    if not body.strip():
        sys.exit("file_issue.py: an issue needs a body: reproduction steps, expected vs actual, the failing test name")
    cap = int(os.environ.get("MAX_ISSUES", "10"))
    used = int(COUNTER.read_text()) if COUNTER.exists() else 0
    fp = fingerprint(a.repo, a.file, a.test, a.title)
    found = call("GET", f"/repos/{a.repo}/issues?" + urllib.parse.urlencode({"q": fp, "type": "issues", "state": "all", "limit": 20})) or []
    for i in found:
        if f"capstone-fingerprint: {fp}" in (i.get("body") or ""):
            print(f"DUPLICATE #{i['number']}")
            return 0
    if used >= cap:
        print(f"file_issue.py: per-run cap of {cap} issues reached; put the rest in your final summary instead", file=sys.stderr)
        return 3
    labels = call("GET", f"/repos/{a.repo}/labels?limit=50") or []
    ids = {l["name"]: l["id"] for l in labels}
    want = ["bug", "ai-found"] + (["security"] if a.category in ("sql-injection", "hardcoded-secret", "missing-validation", "security") else [])
    marker = (f"<!-- capstone-fingerprint: {fp}; agent-run: {os.environ.get('AGENT_RUN_ID', '')}; severity: {a.severity}; category: {a.category}; "
              f"file: {a.file}; line: {a.line}; test: {a.test} -->")
    text = f"**Severity:** {a.severity}  \n**Category:** {a.category}  \n**Failing test:** `{a.test}`  \n**Location:** `{a.file}:{a.line}`  \n**Agent run:** `{os.environ.get('AGENT_RUN_ID', '')}`\n\n{body}\n\n{marker}\n"
    created = call("POST", f"/repos/{a.repo}/issues", {"title": a.title, "body": text, "labels": [ids[n] for n in want if n in ids]})
    COUNTER.write_text(str(used + 1))
    print(f"FILED #{created['number']} {created.get('html_url', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
