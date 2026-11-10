"""Guestbook API as an Appwrite Function (python-3.12).

GET  /entries           latest entries
POST /entries           {"name": "Ada", "message": "hi"}  -> 201
GET  /healthz           liveness for synthetic checks (answers without touching the store)

Function variables:
  STORE              memory (default) or appwrite
  APPWRITE_ENDPOINT  API URL reachable FROM THE RUNTIME (optional; falls back to APPWRITE_FUNCTION_API_ENDPOINT)
"""
import os

from store import AppwriteStore, MemoryStore

_memory = MemoryStore()  # survives between requests while this runtime container stays warm


def _store(context):
    if os.environ.get("STORE", "memory") == "appwrite":
        endpoint = os.environ.get("APPWRITE_ENDPOINT") or os.environ["APPWRITE_FUNCTION_API_ENDPOINT"]
        return AppwriteStore(endpoint, os.environ["APPWRITE_FUNCTION_PROJECT_ID"], context.req.headers.get("x-appwrite-key", ""))
    return _memory


def main(context):
    path, method = context.req.path, context.req.method
    if path == "/healthz":
        return context.res.json({"status": "ok"})
    if path != "/entries":
        return context.res.json({"error": "not found"}, 404)
    store = _store(context)
    if method == "GET":
        return context.res.json({"entries": store.latest()})
    if method == "POST":
        try:
            body = context.req.body_json
            name, message = str(body["name"]).strip(), str(body["message"]).strip()
        except (ValueError, KeyError, TypeError):
            return context.res.json({"error": 'send JSON like {"name": "Ada", "message": "hi"}'}, 400)
        if not (1 <= len(name) <= 100 and 1 <= len(message) <= 500):
            return context.res.json({"error": "name 1-100 characters, message 1-500 characters"}, 400)
        context.log(f"new entry from {name}")
        return context.res.json(store.add(name, message), 201)
    return context.res.json({"error": "method not allowed"}, 405)
