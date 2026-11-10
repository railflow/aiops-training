"""Appwrite Function: store a greeting as a row in a TablesDB table, using the function's own ephemeral API key.

POST {"name": "Ada"}  ->  {"id": "<row id>", "name": "Ada"}

Function variables: DATABASE_ID (default hello), TABLE_ID (default greetings).
APPWRITE_ENDPOINT (optional): the API URL the *runtime* can reach; falls back to APPWRITE_FUNCTION_API_ENDPOINT.
On a local cluster the second one (http://appwrite.localhost/...) may point at the runtime itself: see Day 26.
Uses only the standard library, so there is nothing to install at build time.
"""
import json
import os
import urllib.error
import urllib.request


def main(context):
    if context.req.method != "POST":
        return context.res.json({"error": "POST a JSON body like {\"name\": \"Ada\"}"}, 405)
    try:
        name = str(context.req.body_json.get("name", "")).strip()
    except (ValueError, AttributeError):
        return context.res.json({"error": "body must be JSON"}, 400)
    if not name or len(name) > 100:
        return context.res.json({"error": "name is required and at most 100 characters"}, 400)

    endpoint = (os.environ.get("APPWRITE_ENDPOINT") or os.environ["APPWRITE_FUNCTION_API_ENDPOINT"]).rstrip("/")
    db = os.environ.get("DATABASE_ID", "hello")
    table = os.environ.get("TABLE_ID", "greetings")
    request = urllib.request.Request(
        f"{endpoint}/tablesdb/{db}/tables/{table}/rows",
        data=json.dumps({"rowId": "unique()", "data": {"name": name}}).encode(),
        method="POST",
        headers={
            "content-type": "application/json",
            "x-appwrite-project": os.environ["APPWRITE_FUNCTION_PROJECT_ID"],
            "x-appwrite-key": context.req.headers.get("x-appwrite-key", ""),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            row = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        context.error(f"Appwrite answered {exc.code}")
        return context.res.json({"error": "database write failed", "status": exc.code}, 502)
    except OSError as exc:
        context.error(f"could not reach {endpoint}: {exc}")
        return context.res.json({"error": "cannot reach Appwrite from the runtime", "endpoint": endpoint}, 502)
    return context.res.json({"id": row.get("$id"), "name": name}, 201)
