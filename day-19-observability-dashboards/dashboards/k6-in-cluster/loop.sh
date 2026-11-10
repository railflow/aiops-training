#!/usr/bin/env bash
# Run k6 again and again from your laptop so dashboards always have fresh data. Stop with Ctrl+C.
# Usage: loop.sh [rate-per-second] [minutes-per-round]
set -u
RATE="${1:-5}"
MINUTES="${2:-10}"
cd "$(dirname "$0")/../../../day-18-monitoring-your-kubernetes-cluster/monitoring/k6" || exit 1
while true; do
  echo "$(date -u +%H:%M:%SZ) starting k6 round: ${RATE}/s for ${MINUTES}m"
  k6 run --quiet -e RATE="$RATE" -e DURATION="${MINUTES}m" loop.js || echo "k6 exited non-zero (a threshold failed?); continuing"
done
