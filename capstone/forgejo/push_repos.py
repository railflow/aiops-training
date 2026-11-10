#!/usr/bin/env python3
"""push_repos.py: put every repo listed in repos.csv into Forgejo, idempotently. Standard library only (plus git on PATH).

  export FORGEJO_URL=http://forgejo.localhost:8080      # the Traefik hostname from Day 7; or http://localhost:3000 via port-forward
  export FORGEJO_TOKEN=...                               # a token with write:organization, write:repository, write:issue; NEVER commit it
  export WEBHOOK_SECRET=...                              # shared HMAC secret for the capstone webhook (optional)
  python3 push_repos.py --csv ../work/repos.csv --org capstone --parallel 4 --webhook-url http://capstone-webhook.localhost:8080/forgejo

Per repo: ensure the org, create the repo if missing, enable issues and the (UI-only) projects toggle, set topics, create the labels
bug / ai-found / coverage / security / ai-fix, add a push+pull_request webhook, add .forgejo/workflows/ci.yaml as one extra commit, and push main.
Safe to re-run: every step checks first. Rate limits and 5xx get exponential backoff. Prints one line per repo and a summary; exit 1 if any repo failed.
No Forgejo API creates a project board (see the page): this script turns the has_projects switch on and uses status/* labels as the board convention.
Forgejo's own swagger at $FORGEJO_URL/api/swagger is the source of truth for field names: they were checked against a Forgejo development swagger, not v11.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LABELS = [("bug", "d73a4a", "Something is broken"), ("ai-found", "7057ff", "Filed by an agent"), ("coverage", "0e8a16", "Test coverage work"),
          ("security", "b60205", "Security issue"), ("ai-fix", "1d76db", "An agent may attempt the fix"),
          ("status/todo", "ededed", "Board column: to do"), ("status/doing", "fbca04", "Board column: in progress"), ("status/review", "0052cc", "Board column: in review"),
          ("status/done", "0e8a16", "Board column: done")]
WORKFLOW = Path(__file__).resolve().parent / "ci.yaml"


class Api:
    def __init__(self, base, token, retries=4):
        self.base, self.token, self.retries = base.rstrip("/") + "/api/v1", token, retries

    def call(self, method, path, body=None, ok=(200, 201, 204)):
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(self.base + path, data=data, method=method)
            req.add_header("Authorization", f"token {self.token}")
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    return r.status, (json.loads(raw) if raw else None)
            except urllib.error.HTTPError as e:
                raw = e.read()
                if e.code == 429 or e.code >= 500:
                    if attempt < self.retries:
                        time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                        continue
                return e.code, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode()[:200])
            except urllib.error.URLError as e:
                if attempt == self.retries:
                    raise SystemExit(f"cannot reach {self.base}: {e.reason}")
                time.sleep(2 ** attempt)


def git(args, cwd, env=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **(env or {})}, check=check, capture_output=True, text=True)


def ensure_org(api, org):
    if api.call("GET", f"/orgs/{org}")[0] == 200:
        return
    code, out = api.call("POST", "/orgs", {"username": org, "visibility": "private"})
    if code not in (200, 201, 422):    # 422 = already exists (race with another worker)
        raise SystemExit(f"cannot create org {org}: {code} {out}")


def process(api, a, row, git_env):
    name, lang, domain = row["name"], row["language"], row["domain"]
    path = Path(row["path"]) if Path(row["path"]).is_absolute() else Path(a.csv).resolve().parent / row["path"]
    steps = []
    code, _ = api.call("GET", f"/repos/{a.org}/{name}")
    if code == 404:
        code, out = api.call("POST", f"/orgs/{a.org}/repos", {"name": name, "description": f"{lang} {domain} service (capstone, owner {row.get('owner_team', '')})",
                                                              "private": True, "default_branch": "main", "auto_init": False})
        if code not in (200, 201):
            return name, "FAILED", f"create repo: {code} {out}"
        steps.append("created")
    elif code != 200:
        return name, "FAILED", f"lookup: {code}"
    else:
        steps.append("exists")
    api.call("PATCH", f"/repos/{a.org}/{name}", {"has_issues": True, "has_projects": True, "default_branch": "main"})
    api.call("PUT", f"/repos/{a.org}/{name}/topics", {"topics": sorted({lang, domain, "capstone", row.get("owner_team", "") or "capstone"})})
    code, have = api.call("GET", f"/repos/{a.org}/{name}/labels?limit=50")
    have = {l["name"] for l in have} if code == 200 and isinstance(have, list) else set()
    for lname, color, desc in LABELS:
        if lname not in have:
            api.call("POST", f"/repos/{a.org}/{name}/labels", {"name": lname, "color": "#" + color, "description": desc})
    if a.webhook_url:
        code, hooks = api.call("GET", f"/repos/{a.org}/{name}/hooks")
        if not any(h.get("config", {}).get("url") == a.webhook_url for h in (hooks if isinstance(hooks, list) else [])):
            cfg = {"url": a.webhook_url, "content_type": "json"}
            if os.environ.get("WEBHOOK_SECRET"):
                cfg["secret"] = os.environ["WEBHOOK_SECRET"]
            api.call("POST", f"/repos/{a.org}/{name}/hooks", {"type": "forgejo", "active": True, "events": ["push", "pull_request", "issues", "issue_comment"], "config": cfg})
            steps.append("hook")
    if not path.is_dir():
        return name, "FAILED", f"local path {path} is missing"
    wf = path / ".forgejo" / "workflows" / "ci.yaml"
    if a.ci and not wf.exists():
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(WORKFLOW.read_text())
        git(["add", ".forgejo"], path)
        git(["-c", "user.name=capstone", "-c", "user.email=capstone@example.com", "commit", "-q", "-m", "Add golden-path CI workflow"], path)
        steps.append("ci-commit")
    remote = f"{(a.git_url or a.url).rstrip('/')}/{a.org}/{name}.git"
    cur = git(["remote", "get-url", "forgejo"], path, check=False)
    if cur.returncode != 0:
        git(["remote", "add", "forgejo", remote], path)
    elif cur.stdout.strip() != remote:
        git(["remote", "set-url", "forgejo", remote], path)
    pushed = git(["push", "-u", "forgejo", "main"], path, env=git_env, check=False)
    if pushed.returncode != 0:
        return name, "FAILED", "push: " + pushed.stderr.strip()[-200:]
    steps.append("pushed")
    return name, "OK", ",".join(steps)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--org", default="capstone")
    ap.add_argument("--url", default=os.environ.get("FORGEJO_URL", "http://forgejo.localhost:8080"))
    ap.add_argument("--git-url", default=os.environ.get("FORGEJO_GIT_URL", ""), help="clone/push base URL if different from --url (tests use file://)")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--webhook-url", default=os.environ.get("WEBHOOK_URL", ""))
    ap.add_argument("--no-ci", dest="ci", action="store_false", help="do not add the workflow commit")
    ap.add_argument("--limit", type=int, default=0, help="only the first N rows (try 3 first)")
    a = ap.parse_args()
    token = os.environ.get("FORGEJO_TOKEN")
    if not token:
        sys.exit("FORGEJO_TOKEN is not set (create one in Settings > Applications; never put it in a file in git)")
    # git reads the token from the environment, so it never appears in argv, .git/config or the remote URL.
    git_env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraHeader", "GIT_CONFIG_VALUE_0": f"Authorization: token {token}", "GIT_TERMINAL_PROMPT": "0"}
    rows = list(csv.DictReader(open(a.csv)))
    if a.limit:
        rows = rows[:a.limit]
    api = Api(a.url, token)
    ensure_org(api, a.org)
    results = []
    with ThreadPoolExecutor(max_workers=a.parallel) as ex:
        futs = [ex.submit(process, api, a, r, git_env) for r in rows]
        for f in as_completed(futs):
            try:
                name, status, detail = f.result()
            except Exception as e:     # one bad repo must not stop the other 99
                name, status, detail = "?", "FAILED", repr(e)
            results.append((name, status, detail))
            print(f"{status:6s} {name:28s} {detail}", flush=True)
    bad = [r for r in results if r[1] != "OK"]
    print(f"\nsummary: {len(results) - len(bad)} ok, {len(bad)} failed, {len(results)} total")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
