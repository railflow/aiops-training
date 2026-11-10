#!/usr/bin/env bash
# Give an app its own database and role in the shared Postgres, and hand it the connection details as a Secret.
#   provision-db.sh <app> [--dry-run]
# Set APP_NS to put the Secret in a namespace that differs from the app name (e.g. APP_NS=temporal for a second database).
# Idempotent: running it again keeps the existing password (reads it back from the app's Secret).
# The password travels over stdin to psql, never on a command line. Dry run prints the SQL with the password masked.
set -euo pipefail

APP="${1:-}"; MODE="${2:-}"
[[ "$APP" =~ ^[a-z][a-z0-9-]{1,30}$ ]] || { echo "usage: $0 <app> [--dry-run]   (app: lowercase letters, digits, dashes)" >&2; exit 2; }
NAME="${APP//-/_}"                     # SQL identifier: dashes become underscores
PGNS="${PGNS:-platform-data}"
SECRET="${APP}-db"
NS="${APP_NS:-$APP}"

existing=""
if [ "$MODE" != "--dry-run" ]; then
  existing="$(kubectl -n "$NS" get secret "$SECRET" -o jsonpath='{.data.PGPASSWORD}' 2>/dev/null | base64 -d || true)"
fi
PASSWORD="${existing:-$(openssl rand -hex 16)}"
[[ "$PASSWORD" =~ ^[0-9a-f]+$ ]] || { echo "unexpected password format" >&2; exit 1; }

sql() {
  local shown="$1"
  cat <<SQL
\\set ON_ERROR_STOP on
\\set db '$NAME'
\\set role '$NAME'
\\set pw '$shown'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role', :'pw')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'role') \\gexec
SELECT format('ALTER ROLE %I PASSWORD %L', :'role', :'pw') \\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'role')
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db') \\gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db') \\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db', :'role') \\gexec
SQL
}

if [ "$MODE" = "--dry-run" ]; then
  echo "-- would run against sts/postgres in namespace $PGNS:"
  sql '***'
  echo "-- would create Secret $SECRET in namespace $NS with PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD"
  exit 0
fi

sql "$PASSWORD" | kubectl -n "$PGNS" exec -i sts/postgres -- psql -U postgres -X -q -f -

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS"
kubectl -n "$NS" create secret generic "$SECRET" \
  --from-literal=PGHOST="postgres.${PGNS}.svc.cluster.local" --from-literal=PGPORT=5432 \
  --from-literal=PGDATABASE="$NAME" --from-literal=PGUSER="$NAME" --from-literal=PGPASSWORD="$PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "database '$NAME' ready; Secret $NS/$SECRET created or updated"
