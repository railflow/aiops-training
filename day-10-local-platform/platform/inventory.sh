#!/usr/bin/env bash
# The Infra detour, step 1: what data services does this cluster actually run, and who runs how many of them?
# Read-only. Needs kubectl and jq.
set -euo pipefail

echo "== StatefulSets and Deployments whose image looks like a datastore"
kubectl get sts,deploy -A -o json | jq -r '
  .items[]
  | . as $o
  | ($o.spec.template.spec.containers[].image) as $img
  | select($img | test("postgres|mysql|mariadb|mongo|redis|valkey|clickhouse|nats|minio|seaweedfs|rabbitmq|kafka|opensearch|elasticsearch"))
  | [$o.kind, $o.metadata.namespace, $o.metadata.name, $img] | @tsv' | sort -u | column -t

echo
echo "== Persistent volume claims (what is storing data, and how much)"
kubectl get pvc -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,SIZE:.spec.resources.requests.storage,CLASS:.spec.storageClassName --no-headers | column -t

echo
echo "== Memory requested by datastore-looking workloads (sum, MiB, rough)"
kubectl get pods -A -o json | jq -r '
  [.items[]
   | select(.spec.containers[].image | test("postgres|mysql|mariadb|mongo|redis|valkey|clickhouse|nats|minio|seaweedfs"))
   | .spec.containers[].resources.requests.memory // "0"
   | if test("Gi$") then (sub("Gi$";"")|tonumber*1024) elif test("Mi$") then (sub("Mi$";"")|tonumber) else 0 end
  ] | add // 0'
