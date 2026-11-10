#!/usr/bin/env python3
"""answer_key.py: load the planted-bug answer keys into ClickHouse, and match filed issues against them.

  python3 answer_key.py load --keys ./answer-keys --dry-run          # print the rows
  python3 answer_key.py load --keys ./answer-keys                     # INSERT into capstone.planted_issues (CLICKHOUSE_* env, see measure/ship.py)
  python3 answer_key.py score --keys ./answer-keys                    # run after agents file issues: fills capstone.issue_matches (the agents never see the keys)
  python3 answer_key.py match --keys ./answer-keys --repo R --file src/a.py --line 12     # which planted id does a finding map to?

Matching rule (deliberately simple, and written down so you can argue with it): a finding matches a planted bug in the same repo when the file is the same and
the finding's line is inside [line_start - slack, line_end + slack] (slack default 5). Agents change files and lines move, so for real runs also match on the
failing test name or category: improve this function, it is part of your homework.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "measure"))


def load_keys(keys_dir):
    out = {}
    for f in sorted(Path(keys_dir).glob("*.planted-issues.json")):
        j = json.loads(f.read_text())
        out[j["repo"]] = j["issues"]
    return out


def rows(keys):
    for repo, issues in keys.items():
        for i in issues:
            yield {"repo": repo, "planted_id": i["id"], "file": i["file"], "line_start": i["line_start"], "line_end": i["line_end"],
                   "category": i["category"], "severity": i["severity"], "description": i["description"]}


def match(keys, repo, file, line, slack=5):
    for i in keys.get(repo, []):
        if i["file"] == file and i["line_start"] - slack <= line <= i["line_end"] + slack:
            return i["id"]
    return ""


def score(keys, issues, slack=5):
    """issues: dicts with repo, issue_number, file, line. Returns issue_matches rows."""
    out = []
    for i in issues:
        pid = match(keys, i["repo"], i["file"], int(i["line"]), slack)
        if pid:
            out.append({"repo": i["repo"], "issue_number": int(i["issue_number"]), "planted_id": pid, "rule": "file+line"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("load")
    l.add_argument("--keys", required=True)
    l.add_argument("--dry-run", action="store_true")
    sc = sub.add_parser("score", help="match issues_filed rows that have no match yet and INSERT into capstone.issue_matches")
    sc.add_argument("--keys", required=True)
    sc.add_argument("--dry-run", action="store_true")
    m = sub.add_parser("match")
    m.add_argument("--keys", required=True)
    m.add_argument("--repo", required=True)
    m.add_argument("--file", required=True)
    m.add_argument("--line", type=int, required=True)
    m.add_argument("--slack", type=int, default=5)
    a = ap.parse_args()
    keys = load_keys(a.keys)
    if a.cmd == "score":
        import ship
        pending = ship.query_rows("SELECT repo, issue_number, file, line FROM capstone.issues_filed WHERE line > 0 AND (repo, issue_number) NOT IN "
                                  "(SELECT repo, issue_number FROM capstone.issue_matches)")
        found = score(keys, pending)
        ship.insert_rows(found, table="capstone.issue_matches", dry_run=a.dry_run) if found else None
        print(f"answer_key.py: {len(pending)} unmatched issues examined, {len(found)} matched a planted bug", file=sys.stderr)
    elif a.cmd == "load":
        import ship
        n = ship.insert_rows(list(rows(keys)), table="capstone.planted_issues", dry_run=a.dry_run)
        print(f"answer_key.py: {n} planted issues from {len(keys)} repos", file=sys.stderr)
    else:
        print(match(keys, a.repo, a.file, a.line, a.slack) or "no match")


if __name__ == "__main__":
    main()
