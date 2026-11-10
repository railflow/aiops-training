#!/usr/bin/env bash
# Run the fan-out on the course's kind cluster with the mock model.
#   ./run-on-kind.sh [hand|adk] [repos] [concurrency] [extra orchestrator args...]
#   ./run-on-kind.sh clean
# Uses its own namespace (agent-harness) and refuses to run against any other kubectl context.
set -euo pipefail
cd "$(dirname "$0")"
CLUSTER="${KIND_CLUSTER:-ai-ops-training}"
NS=agent-harness
if [ "$(kubectl config current-context)" != "kind-$CLUSTER" ]; then
  echo "kubectl context is not kind-$CLUSTER; refusing to run" >&2; exit 1
fi
if [ "${1:-}" = "clean" ]; then
  kubectl delete namespace "$NS" --ignore-not-found
  docker exec "$CLUSTER-control-plane" rm -rf /var/ah-state
  exit 0
fi
ENGINE="${1:-adk}"; COUNT="${2:-20}"; CONC="${3:-10}"; shift $(( $# > 3 ? 3 : $# ))
docker build -q -f Dockerfile -t agent-harness:dev ../..
kind load docker-image agent-harness:dev --name "$CLUSTER"
kubectl get namespace "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS"
docker exec "$CLUSTER-control-plane" sh -c 'mkdir -p /var/ah-state && chmod 777 /var/ah-state'
RUN_ID="${RUN_ID:-$(date +%H%M%S)}"
PYTHONPATH=. python3 -m fanout.orchestrator --engine "$ENGINE" --count "$COUNT" --concurrency "$CONC" --namespace "$NS" --run-id "$RUN_ID" \
  --ledger "results-$RUN_ID.jsonl" --state-hostpath /var/ah-state --poll 2 "$@"
