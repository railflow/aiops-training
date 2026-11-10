#!/usr/bin/env bash
# Rotate the hello-app database password: change it in Postgres, then in OpenBao.
# The new value is generated here, printed nowhere, and stored only in those two places.
# Real systems avoid the brief window where the two disagree by using two alternating users
# or dynamic credentials (see the lesson). Usage: rotate-db-password.sh
set -euo pipefail

NEW_PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)"

kubectl -n data exec postgres-0 -- psql -U app -d app -v ON_ERROR_STOP=1 \
  -c "ALTER USER app WITH PASSWORD '$NEW_PASSWORD';"

kubectl -n openbao exec openbao-0 -- env BAO_TOKEN=root BAO_ADDR=http://127.0.0.1:8200 \
  bao kv put secret/hello-app/db username=app password="$NEW_PASSWORD" > /dev/null

echo "rotated at $(date -u +%H:%M:%SZ): Postgres and OpenBao now hold the new password."
