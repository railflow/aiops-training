#!/usr/bin/env bash
# THE LEGACY THING. Pretend this is the old CI system's trigger: you call it, wait, and scrape its output. It knows nothing about events.
# usage: run_ci_legacy.sh <repo> <sha> [fail]     prints KEY=VALUE lines, exits 0 on pass, 1 on fail
set -u
repo="${1:?repo}"; sha="${2:?sha}"; mode="${3:-}"
sleep "${LEGACY_SECONDS:-0.3}"
echo "BUILD_URL=http://legacy-ci.example.internal/job/${repo}/${sha}"
echo "TESTS=42"
if [ "$mode" = "fail" ]; then echo "RESULT=FAILURE"; exit 1; fi
echo "RESULT=SUCCESS"
