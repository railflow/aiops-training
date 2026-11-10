"""Store and list 'hello' records in Appwrite using its REST API.

Environment:
  APPWRITE_ENDPOINT    default http://localhost/v1
  APPWRITE_PROJECT_ID  your project id (Appwrite console > project settings)
  APPWRITE_API_KEY     a server API key with the databases scopes (never commit it)

Usage:
  python appwrite_hello.py setup        create database + collection + attributes (idempotent)
  python appwrite_hello.py add NAME     create a document
  python appwrite_hello.py list         list documents

Written against the Appwrite 1.6 Databases API. Newer Appwrite versions add a
"Tables" API; check the Appwrite docs if an endpoint has moved.
"""
import json
import os
import sys
import time

import requests

ENDPOINT = os.environ.get("APPWRITE_ENDPOINT", "http://localhost/v1").rstrip("/")
PROJECT = os.environ.get("APPWRITE_PROJECT_ID", "")
API_KEY = os.environ.get("APPWRITE_API_KEY", "")
DATABASE_ID = "hello"
COLLECTION_ID = "greetings"

HEADERS = {
    "Content-Type": "application/json",
    "X-Appwrite-Project": PROJECT,
    "X-Appwrite-Key": API_KEY,
}


def call(method, path, body=None, ok_conflict=False):
    resp = requests.request(method, f"{ENDPOINT}{path}", headers=HEADERS, json=body, timeout=15)
    if resp.status_code == 409 and ok_conflict:
        return None
    if not resp.ok:
        sys.exit(f"{method} {path} failed: HTTP {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else None


def setup():
    call("POST", "/databases", {"databaseId": DATABASE_ID, "name": "Hello"}, ok_conflict=True)
    base = f"/databases/{DATABASE_ID}/collections"
    call(
        "POST",
        base,
        {"collectionId": COLLECTION_ID, "name": "Greetings", "permissions": [], "documentSecurity": False},
        ok_conflict=True,
    )
    for key, size in (("name", 128), ("message", 512)):
        call(
            "POST",
            f"{base}/{COLLECTION_ID}/attributes/string",
            {"key": key, "size": size, "required": True},
            ok_conflict=True,
        )
    # Attributes are created asynchronously; wait until they are usable.
    for key in ("name", "message"):
        for _ in range(30):
            attr = call("GET", f"{base}/{COLLECTION_ID}/attributes/{key}")
            if attr.get("status") == "available":
                break
            time.sleep(1)
        else:
            sys.exit(f"attribute {key} did not become available in time")
    print("setup complete")


def add(name):
    doc = call(
        "POST",
        f"/databases/{DATABASE_ID}/collections/{COLLECTION_ID}/documents",
        {"documentId": "unique()", "data": {"name": name, "message": f"Hello, {name}!"}},
    )
    print("created", doc["$id"])


def list_docs():
    result = call("GET", f"/databases/{DATABASE_ID}/collections/{COLLECTION_ID}/documents")
    print(f"{result['total']} document(s)")
    for doc in result["documents"]:
        print(json.dumps({k: doc[k] for k in ("$id", "name", "message", "$createdAt")}))


if __name__ == "__main__":
    if not PROJECT or not API_KEY:
        sys.exit("Set APPWRITE_PROJECT_ID and APPWRITE_API_KEY (see day04).")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "setup":
        setup()
    elif cmd == "add" and len(sys.argv) > 2:
        add(sys.argv[2])
    elif cmd == "list":
        list_docs()
    else:
        sys.exit(__doc__)
