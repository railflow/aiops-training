#!/usr/bin/env bash
# validate_repo.sh REPO_DIR ANSWER_KEY.json: does the repo build, do the tests run, and does the answer key point at real lines?
# Uses measure.py (run the tests, parse reports) so "validated" means the same thing as "measured". Exit 0 = good, 1 = problem.
set -euo pipefail
DIR="${1:?repo dir}"; KEY="${2:?answer key json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
doc="$(python3 "$HERE/../measure/measure.py" --dir "$DIR" --run-id validate)"
python3 - "$DIR" "$KEY" "$doc" <<'PY'
import json, sys
from pathlib import Path
d, key, doc = Path(sys.argv[1]), json.load(open(sys.argv[2])), json.loads(sys.argv[3])
bad = []
if not doc["build_ok"]: bad.append("build or tests did not run")
if doc["test_count"] == 0: bad.append("no tests found")
if (doc["line_coverage_pct"] or 0) > 60: bad.append(f"coverage {doc['line_coverage_pct']}% is too good for a mess")
if not 6 <= len(key["issues"]) <= 40: bad.append(f"{len(key['issues'])} planted issues is outside 6..40")
for i in key["issues"]:
    f = d / i["file"]
    if not f.exists(): bad.append(f"{i['id']}: {i['file']} missing"); continue
    n = len(f.read_text().splitlines())
    if not 1 <= i["line_start"] <= i["line_end"] <= n: bad.append(f"{i['id']}: lines {i['line_start']}-{i['line_end']} outside {i['file']} ({n} lines)")
print(("PROBLEMS: " + "; ".join(bad)) if bad else f"ok: {doc['lines_of_code']} loc, {doc['test_count']} tests, coverage {doc['line_coverage_pct']}%, {len(key['issues'])} planted")
sys.exit(1 if bad else 0)
PY
