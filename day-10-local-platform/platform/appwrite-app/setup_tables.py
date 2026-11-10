#!/usr/bin/env python3
"""Create the guestbook database, table and columns in a local Appwrite. Safe to run twice (409 means "already there").

    export APPWRITE_ENDPOINT=http://appwrite.localhost:8080/v1
    export APPWRITE_PROJECT_ID=<project id from the console>
    export APPWRITE_API_KEY=<a server API key with database/table/column scopes: create it in the console>
    python3 setup_tables.py

Routes are from Appwrite's 2.7 OpenAPI spec (tablesdb). Column creation is asynchronous: wait for status "available".
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request


def call(method, path, payload=None, opener=None):
    request = urllib.request.Request(
        os.environ["APPWRITE_ENDPOINT"].rstrip("/") + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={
            "content-type": "application/json",
            "x-appwrite-project": os.environ["APPWRITE_PROJECT_ID"],
            "x-appwrite-key": os.environ["APPWRITE_API_KEY"],
        },
    )
    try:
        with (opener or urllib.request.urlopen)(request, timeout=15) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            return {"exists": True}
        raise SystemExit(f"{method} {path} -> HTTP {exc.code}: {exc.read().decode()[:300]}")


def main():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        if not os.environ.get(var):
            raise SystemExit(f"set {var} first (see the docstring)")
    call("POST", "/tablesdb", {"databaseId": "guestbook", "name": "Guestbook"})
    call("POST", "/tablesdb/guestbook/tables", {"tableId": "entries", "name": "Entries"})
    for key, size in (("name", 100), ("message", 500)):
        call("POST", "/tablesdb/guestbook/tables/entries/columns/varchar", {"key": key, "size": size, "required": True})
    for _ in range(30):
        columns = call("GET", "/tablesdb/guestbook/tables/entries/columns").get("columns", [])
        if columns and all(c.get("status") == "available" for c in columns):
            print("ready:", ", ".join(c["key"] for c in columns))
            return
        time.sleep(1)
    print("columns are not available yet: check the console, then run this again", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
