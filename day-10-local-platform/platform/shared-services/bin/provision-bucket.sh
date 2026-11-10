#!/usr/bin/env bash
# Give an app its own bucket and S3 credentials in the shared SeaweedFS.
#   provision-bucket.sh <app> [--dry-run]
# LEAST VERIFIED FILE IN THIS FOLDER: the `s3.configure` flags below come from memory of the SeaweedFS shell and the
# interaction with the -s3.config file used in seaweedfs.yaml is untested. Check the SeaweedFS documentation first.
set -euo pipefail

APP="${1:-}"; MODE="${2:-}"
[[ "$APP" =~ ^[a-z][a-z0-9-]{1,30}$ ]] || { echo "usage: $0 <app> [--dry-run]" >&2; exit 2; }
PGNS="${PGNS:-platform-data}"
BUCKET="$APP"
ACCESS="$(openssl rand -hex 8)"
SECRETKEY="$(openssl rand -hex 24)"

if [ "$MODE" = "--dry-run" ]; then
  echo "-- would run in sts/seaweedfs (namespace $PGNS), weed shell:"
  echo "s3.bucket.create -name $BUCKET"
  echo "s3.configure -user=$APP -buckets=$BUCKET -actions=Read,Write,List -access_key=*** -secret_key=*** -apply"
  echo "-- would create Secret ${APP}-bucket in namespace $APP (S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY)"
  exit 0
fi

printf 's3.bucket.create -name %s\ns3.configure -user=%s -buckets=%s -actions=Read,Write,List -access_key=%s -secret_key=%s -apply\n' \
  "$BUCKET" "$APP" "$BUCKET" "$ACCESS" "$SECRETKEY" |
  kubectl -n "$PGNS" exec -i sts/seaweedfs -- weed shell -master=localhost:9333

kubectl get ns "$APP" >/dev/null 2>&1 || kubectl create namespace "$APP"
kubectl -n "$APP" create secret generic "${APP}-bucket" \
  --from-literal=S3_ENDPOINT="http://seaweedfs.${PGNS}.svc.cluster.local:8333" --from-literal=S3_BUCKET="$BUCKET" \
  --from-literal=S3_ACCESS_KEY="$ACCESS" --from-literal=S3_SECRET_KEY="$SECRETKEY" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "bucket '$BUCKET' ready; Secret $APP/${APP}-bucket created"
