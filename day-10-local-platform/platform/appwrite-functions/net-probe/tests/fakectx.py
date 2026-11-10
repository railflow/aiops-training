"""A stand-in for the runtime's context object, mirroring the attributes the Open Runtimes Python runtime sets."""
import json
from types import SimpleNamespace


class _Res:
    def text(self, body, statusCode=200, headers=None):
        return {"body": body, "statusCode": statusCode, "headers": headers or {}}

    def json(self, obj, statusCode=200, headers=None):
        return {"body": json.dumps(obj), "statusCode": statusCode, "headers": {"content-type": "application/json", **(headers or {})}}


def make_context(path="/", query=None, headers=None, body=b""):
    req = SimpleNamespace(
        path=path,
        query=query or {},
        headers={k.lower(): v for k, v in (headers or {}).items()},
        body_binary=body,
        method="GET" if not body else "POST",
    )
    req.body_text = body.decode("utf-8")
    req.body_json = json.loads(req.body_text) if body else {}
    logs = []
    return SimpleNamespace(req=req, res=_Res(), log=lambda *a: logs.append(a), error=lambda *a: logs.append(("ERR",) + a), logs=logs)
