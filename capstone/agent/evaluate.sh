#!/usr/bin/env bash
# evaluate.sh: the TRUSTED half of an iteration. The agent never grades itself. Runs in a separate Job (the measure image, ClickHouse allowed).
#
# Clones the agent's branch, runs the integrity check against main, runs tests with coverage via `build.sh measure`, ships the measurement row,
# applies the gates, and prints one RESULT line the Temporal activity reads. Environment: REPO, FORGEJO_URL, FORGEJO_TOKEN (read-only is enough),
# BRANCH, AGENT_RUN_ID, ITERATION, PREV_COVERAGE, ALLOW_SRC_CHANGES (0/1), CLICKHOUSE_URL/USER/PASSWORD, RUN_ID.
set -uo pipefail
export WORK="${WORK_DIR:-/work}"
: "${REPO:?}" "${FORGEJO_URL:?}" "${FORGEJO_TOKEN:?}" "${BRANCH:?}"
export HOME="${HOME:-/tmp/home}"; mkdir -p "$HOME" "$WORK/repo"; cd "$WORK"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader GIT_CONFIG_VALUE_0="Authorization: token $FORGEJO_TOKEN" GIT_TERMINAL_PROMPT=0
git clone --quiet "${FORGEJO_URL%/}/$REPO.git" repo && cd repo || { echo 'RESULT {"ok": false, "reason": "clone-failed"}'; exit 0; }
git fetch --quiet origin main "$BRANCH" && git checkout --quiet "$BRANCH" || { echo 'RESULT {"ok": false, "reason": "branch-missing"}'; exit 0; }

NOSRC=""; [ "${ALLOW_SRC_CHANGES:-0}" = 1 ] || NOSRC="--no-src-changes"
INTEGRITY="$(python3 "${AGENT_DIR:-/opt/agent}"/integrity_check.py --base origin/main $NOSRC --json)"
export REPO_NAME="${REPO#*/}"
MEASURE_SHIP="${MEASURE_SHIP:-1}" REPORT_DIR="$WORK/reports" ITERATION="${ITERATION:-1}" build.sh measure --dir . > "$WORK/measure.out" 2>&1
DOC="$(cat "$WORK/reports/measurement.json" 2>/dev/null || echo '{}')"
python3 - "$INTEGRITY" "$DOC" "${PREV_COVERAGE:-}" <<'PY'
import json, sys
integrity, doc, prev = json.loads(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3]
cov = doc.get("line_coverage_pct")
reasons = [f"{v['rule']}: {v['file']}" for v in integrity["violations"]]
if not doc: reasons.append("no measurement produced")
if doc.get("tests_failed"): reasons.append(f"{doc['tests_failed']} tests failing")
if prev and cov is not None and cov + 0.01 < float(prev): reasons.append(f"coverage dropped {prev} -> {cov}")
print("RESULT " + json.dumps({"ok": not reasons, "reasons": reasons, "measurement": doc, "coverage": cov}))
PY
