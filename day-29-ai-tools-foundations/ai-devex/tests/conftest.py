import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("lib", "gateway", "specs", "evals", "decision", "incident-to-pr", "sandbox", "skills"):
    sys.path.insert(0, os.path.join(ROOT, p))


class _H(BaseHTTPRequestHandler):
    seen = []
    answer = lambda body: "pong"  # noqa: E731

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        type(self).seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if self.path.endswith("/chat/completions"):
            out = {"model": body.get("model"), "choices": [{"message": {"content": type(self).answer(body)}}],
                   "usage": {"prompt_tokens": 7, "completion_tokens": 3, "cost": 0.0001}}
        elif self.path.endswith("/alpha/decisions") or self.path.endswith("/pulls"):
            out = type(self).answer(body)
        else:
            self.send_response(404)
            self.end_headers()
            return
        raw = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_server():
    """A local stand-in for a gateway. NOT a real model: it proves our client shapes requests and parses responses correctly."""
    handler = type("H", (_H,), {"seen": [], "answer": staticmethod(lambda body: "pong")})
    srv = HTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    handler.url = f"http://127.0.0.1:{srv.server_port}"
    yield handler
    srv.shutdown()
