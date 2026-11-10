#!/usr/bin/env bash
# baseline.sh: measure ONE repo chosen by the Indexed Job's JOB_COMPLETION_INDEX (line N+1 of repos.csv) and ship the row. Runs inside the measure image.
# Environment: REPOS_CSV (mounted from a ConfigMap), FORGEJO_URL, FORGEJO_TOKEN (read), ORG, CLICKHOUSE_URL/USER/PASSWORD, RUN_ID.
set -uo pipefail
IDX="${JOB_COMPLETION_INDEX:?this script is meant for an Indexed Job}"
LINE="$(tail -n +2 "${REPOS_CSV:-/config/repos.csv}" | tr -d '\r' | sed -n "$((IDX + 1))p")"
[ -n "$LINE" ] || { echo "no repo for index $IDX"; exit 0; }
NAME="${LINE%%,*}"
export HOME=/tmp/home; mkdir -p "$HOME" /work && cd /work
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader GIT_CONFIG_VALUE_0="Authorization: token $FORGEJO_TOKEN" GIT_TERMINAL_PROMPT=0
git clone --quiet "${FORGEJO_URL%/}/${ORG:-capstone}/$NAME.git" repo || { echo "FAILED clone $NAME"; exit 1; }
cd repo
REPO_NAME="$NAME" RUN_ID="${RUN_ID:-baseline}" ITERATION=0 MEASURE_SHIP=1 REPORT_DIR=/work/reports build.sh measure && echo "OK $NAME"
