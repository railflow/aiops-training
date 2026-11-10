"""A tiny fake of the Forgejo API endpoints push_repos.* and the capstone code use. Test double only: it implements what was needed, not Forgejo."""
import json
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Fake:
    def __init__(self, bare_root: Path, fail_once_429=False):
        self.bare_root, self.orgs, self.repos = bare_root, set(), {}
        self.calls, self.tokens, self.lock = [], set(), threading.Lock()
        self.throttle_next = fail_once_429
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, obj=None, headers=None):
                body = json.dumps(obj).encode() if obj is not None else b""
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n)) if n else {}

            def handle_any(self):
                m, p = self.command, self.path.split("?")[0].replace("/api/v1", "", 1)
                b = self._body() if m in ("POST", "PATCH", "PUT") else {}
                with fake.lock:
                    fake.tokens.add(self.headers.get("Authorization"))
                    fake.calls.append((m, p))
                    if fake.throttle_next and m == "POST" and p.endswith("/repos"):
                        fake.throttle_next = False
                        return self._send(429, {"message": "slow down"}, {"Retry-After": "1"})
                    if (mm := re.fullmatch(r"/orgs/([^/]+)", p)):
                        if m == "GET":
                            return self._send(200 if mm[1] in fake.orgs else 404, {})
                        if m == "DELETE":
                            fake.orgs.discard(mm[1])
                            return self._send(204)
                    if p == "/orgs" and m == "POST":
                        fake.orgs.add(b["username"])
                        return self._send(201, {})
                    if (mm := re.fullmatch(r"/orgs/([^/]+)/repos", p)) and m == "POST":
                        key = (mm[1], b["name"])
                        if key in fake.repos:
                            return self._send(409, {"message": "exists"})
                        fake.repos[key] = {"topics": [], "labels": [], "hooks": [], "settings": {}}
                        bare = fake.bare_root / mm[1] / f"{b['name']}.git"
                        bare.parent.mkdir(parents=True, exist_ok=True)
                        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
                        return self._send(201, {"name": b["name"]})
                    mm = re.fullmatch(r"/repos/([^/]+)/([^/]+)(/[a-z]+)?", p)
                    if mm:
                        repo = fake.repos.get((mm[1], mm[2]))
                        sub = mm[3]
                        if repo is None:
                            return self._send(404, {})
                        if sub is None:
                            if m == "DELETE":
                                del fake.repos[(mm[1], mm[2])]
                                return self._send(204)
                            if m == "PATCH":
                                repo["settings"].update(b)
                            return self._send(200, {})
                        if sub == "/topics" and m == "PUT":
                            repo["topics"] = b["topics"]
                            return self._send(204)
                        if sub == "/labels":
                            if m == "POST":
                                b = {**b, "id": len(repo["labels"]) + 1}
                                repo["labels"].append(b)
                                return self._send(201, b)
                            return self._send(200, repo["labels"])
                        if sub == "/issues":
                            if m == "POST":
                                repo.setdefault("issues", []).append({"number": len(repo.get("issues", [])) + 1, "html_url": "http://fake/i", **b})
                                return self._send(201, repo["issues"][-1])
                            q = (self.path.split("q=")[1].split("&")[0]) if "q=" in self.path else ""
                            return self._send(200, [i for i in repo.get("issues", []) if q in i["body"]])
                        if sub == "/hooks":
                            if m == "POST":
                                repo["hooks"].append(b)
                                return self._send(201, b)
                            return self._send(200, repo["hooks"])
                self._send(404, {"message": f"fake has no {m} {p}"})

            do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = handle_any

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.srv.server_port}"

    def stop(self):
        self.srv.shutdown()
