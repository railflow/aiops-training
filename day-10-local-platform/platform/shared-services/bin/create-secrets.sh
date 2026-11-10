#!/usr/bin/env bash
# Create the admin Secrets for the shared services. Values are generated here and never printed or committed.
#   ./bin/create-secrets.sh
set -euo pipefail
command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 2; }
kubectl get ns platform-data >/dev/null 2>&1 || kubectl apply -f "$(dirname "$0")/../00-namespace.yaml"

if kubectl -n platform-data get secret postgres-admin >/dev/null 2>&1; then
  echo "postgres-admin already exists: leaving it alone (changing it would not change the password inside an existing database)"
else
  kubectl -n platform-data create secret generic postgres-admin --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)"
fi
if kubectl -n platform-data get secret seaweedfs-admin >/dev/null 2>&1; then
  echo "seaweedfs-admin already exists: leaving it alone"
else
  kubectl -n platform-data create secret generic seaweedfs-admin \
    --from-literal=s3-access-key="$(openssl rand -hex 8)" --from-literal=s3-secret-key="$(openssl rand -hex 24)"
fi
