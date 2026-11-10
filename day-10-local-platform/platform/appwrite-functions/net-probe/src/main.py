"""Diagnostic function: can code running inside the Appwrite executor reach the places you need?

Targets come from the PROBE_TARGETS function variable (comma separated host:port), NOT from the request, so nobody
can use this function to scan your network. Delete the function when you are done: it exists to answer questions.
"""
import os
import socket


def probe(target, timeout=2.0):
    host, _, port = target.rpartition(":")
    result = {"target": target}
    try:
        result["resolved"] = sorted({a[4][0] for a in socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)})
    except (socket.gaierror, ValueError) as exc:
        result["dns_error"] = str(exc)
        return result
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            result["connected"] = True
    except OSError as exc:
        result["connected"] = False
        result["connect_error"] = str(exc)
    return result


def main(context):
    targets = [t.strip() for t in os.environ.get("PROBE_TARGETS", "").split(",") if t.strip()]
    return context.res.json(
        {
            "api_endpoint_env": os.environ.get("APPWRITE_FUNCTION_API_ENDPOINT", ""),
            "own_hostname": socket.gethostname(),
            "results": [probe(t) for t in targets],
        }
    )
