#!/usr/bin/env bash
# Two clusters, one Docker network, one proof. Needs docker, kind, kubectl (you install them; this script installs nothing).
# Resource-heavy: each extra kind cluster is another full Kubernetes control plane. Delete both when done: ./probe.sh cleanup
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-up}" in
  up)
    kind get clusters | grep -qx common  || kind create cluster --config kind-common.yaml
    kind get clusters | grep -qx app-foo || kind create cluster --config kind-app-foo.yaml
    kubectl --context kind-common apply -f common-postgres.yaml
    kubectl --context kind-common -n shared rollout status deploy/postgres --timeout=180s
    ip="$(docker inspect -f '{{ (index .NetworkSettings.Networks "kind").IPAddress }}' common-control-plane)"
    echo "common node IP on the kind network: $ip"
    sed "s|__COMMON_NODE_IP__|$ip|" app-foo-link.yaml.tpl | kubectl --context kind-app-foo apply -f -
    echo "now run: ./probe.sh check"
    ;;
  check)
    kubectl --context kind-app-foo -n platform-link run probe --rm -i --restart=Never --image=postgres:17-alpine --env=PGPASSWORD=demo-only-not-a-secret \
      --command -- sh -c 'getent hosts shared-postgres.platform-link.svc.cluster.local; pg_isready -h shared-postgres.platform-link.svc.cluster.local -p 5432; psql -h shared-postgres.platform-link.svc.cluster.local -U postgres -tAc "select current_database(), inet_server_addr()"'
    ;;
  cleanup)
    kind delete cluster --name app-foo || true
    kind delete cluster --name common || true
    ;;
  *) echo "usage: $0 [up|check|cleanup]" >&2; exit 2 ;;
esac
