"""Forgejo REST helper for the worker (standard library only). Field names follow Forgejo's swagger as seen in a development build: check
$FORGEJO_URL/api/swagger on YOUR version.

Tokens: Forgejo creates access tokens through POST /users/{user}/tokens and, as far as I know, only with HTTP Basic auth as that user (a token cannot mint tokens).
So the lab uses a dedicated bot user whose PASSWORD lives in the vault/Secret, and mints one token per run, then deletes it. The honest limit: a Forgejo token is
scoped by API area (write:issue, write:repository), NOT by repository: the bot user's repository permissions are what bound the blast radius. Give the bot access to
the capstone org only.
"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

MARKER = re.compile(r"<!-- capstone-fingerprint: (?P<fp>\w+); agent-run: (?P<run>[^;]*); severity: (?P<sev>\w+); category: (?P<cat>[^;]*); file: (?P<file>[^;]*); line: (?P<line>\d+); test: (?P<test>.*?) -->")


class ForgejoApi:
    def __init__(self, base, admin_token="", bot_user="agent-bot", bot_password=""):
        self.base, self.token, self.bot_user, self.bot_password = base.rstrip("/") + "/api/v1", admin_token, bot_user, bot_password

    def _call(self, method, path, body=None, basic=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, method=method)
        req.add_header("Content-Type", "application/json")
        if basic:
            req.add_header("Authorization", "Basic " + base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode())
        else:
            req.add_header("Authorization", "token " + self.token)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def mint_token(self, run_id):
        t = self._call("POST", f"/users/{self.bot_user}/tokens", {"name": f"run-{run_id}", "scopes": ["write:issue", "write:repository"]}, basic=(self.bot_user, self.bot_password))
        return t["sha1"]

    def revoke_token(self, run_id):
        try:
            self._call("DELETE", f"/users/{self.bot_user}/tokens/run-{run_id}", basic=(self.bot_user, self.bot_password))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise

    def issues_for_run(self, repo, run_id):
        q = urllib.parse.urlencode({"q": f"agent-run: {run_id}", "type": "issues", "state": "all", "limit": 50})
        rows = []
        for i in self._call("GET", f"/repos/{repo}/issues?{q}") or []:
            m = MARKER.search(i.get("body") or "")
            if m and m["run"] == run_id:
                rows.append({"repo": repo.split("/")[-1], "issue_number": i["number"], "fingerprint": m["fp"], "title": i["title"], "severity": m["sev"], "category": m["cat"],
                             "agent_run_id": run_id, "failing_test": m["test"], "file": m["file"], "line": int(m["line"]), "state": i.get("state", "open")})
        return rows

    def create_issue(self, repo, title, body, labels=()):
        ids = {l["name"]: l["id"] for l in self._call("GET", f"/repos/{repo}/labels?limit=50") or []}
        return self._call("POST", f"/repos/{repo}/issues", {"title": title, "body": body, "labels": [ids[n] for n in labels if n in ids]})
