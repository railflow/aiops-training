"""Two interchangeable stores for guestbook entries.

MemoryStore   lives inside one runtime container: lost on restart and not shared between replicas. Good for a first run.
AppwriteStore keeps rows in a TablesDB table through Appwrite's REST API. It needs the runtime to be able to reach the API:
              see Day 26 ("Can my function call Appwrite back?").
"""
import json
import urllib.request


class MemoryStore:
    def __init__(self):
        self._rows = []

    def add(self, name, message):
        row = {"id": str(len(self._rows) + 1), "name": name, "message": message}
        self._rows.append(row)
        return row

    def latest(self, limit=20):
        return list(reversed(self._rows))[:limit]


class AppwriteStore:
    def __init__(self, endpoint, project, key, database="guestbook", table="entries", opener=urllib.request.urlopen):
        self._base = f"{endpoint.rstrip('/')}/tablesdb/{database}/tables/{table}/rows"
        self._headers = {"content-type": "application/json", "x-appwrite-project": project, "x-appwrite-key": key}
        self._open = opener

    def _call(self, method, url, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers=self._headers)
        with self._open(request, timeout=10) as response:
            return json.loads(response.read())

    def add(self, name, message):
        row = self._call("POST", self._base, {"rowId": "unique()", "data": {"name": name, "message": message}})
        return {"id": row.get("$id"), "name": name, "message": message}

    def latest(self, limit=20):
        # Appwrite's query syntax is JSON strings in a `queries[]` parameter: check the Queries docs for your version.
        query = json.dumps({"method": "orderDesc", "attribute": "$createdAt"})
        limit_q = json.dumps({"method": "limit", "values": [limit]})
        from urllib.parse import quote

        url = f"{self._base}?queries[]={quote(query)}&queries[]={quote(limit_q)}"
        rows = self._call("GET", url).get("rows", [])
        return [{"id": r["$id"], "name": r.get("name"), "message": r.get("message")} for r in rows]
