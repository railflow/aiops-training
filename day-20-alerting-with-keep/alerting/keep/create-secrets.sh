#!/usr/bin/env bash
# Creates the Kubernetes Secrets Keep needs, with generated values. Nothing secret is written to a file or to git.
# Requires: kubectl pointed at kind-ai-ops-training, jq, openssl, and the ClickHouse Secret from Day 17.
# Re-running replaces the Secrets with NEW random values (and invalidates old API keys): delete and re-run on purpose only.
set -euo pipefail
CTX=kind-ai-ops-training
K="kubectl --context $CTX"

$K create namespace keep --dry-run=client -o yaml | $K apply -f -

ADMIN_PASSWORD=$(openssl rand -hex 12)
JWT_SECRET=$(openssl rand -hex 32)
NEXTAUTH_SECRET=$(openssl rand -hex 32)
GATUS_KEY=$(openssl rand -hex 24)
ADMIN_KEY=$(openssl rand -hex 24)
CH_PASSWORD=$($K -n observability get secret clickhouse-credentials -o jsonpath='{.data.password}' | base64 -d)

# KEEP_DEFAULT_API_KEYS format is name:role:secret,name:role:secret (see Keep's configuration docs).
$K -n keep create secret generic keep-auth \
  --from-literal=AUTH_TYPE=DB \
  --from-literal=KEEP_JWT_SECRET="$JWT_SECRET" \
  --from-literal=KEEP_DEFAULT_USERNAME=keep \
  --from-literal=KEEP_DEFAULT_PASSWORD="$ADMIN_PASSWORD" \
  --from-literal=KEEP_DEFAULT_API_KEYS="gatus:webhook:$GATUS_KEY,admin-cli:admin:$ADMIN_KEY" \
  --from-literal=KEEP_GATUS_API_KEY="$GATUS_KEY" \
  --dry-run=client -o yaml | $K apply -f -

$K -n keep create secret generic keep-ui \
  --from-literal=AUTH_TYPE=DB \
  --from-literal=NEXTAUTH_SECRET="$NEXTAUTH_SECRET" \
  --dry-run=client -o yaml | $K apply -f -

PROVIDERS=$(jq -nc --arg chpw "$CH_PASSWORD" '{
  "clickhouse-otel": {type: "clickhouse", authentication: {host: "clickhouse.observability", port: 9000, username: "otel", password: $chpw, database: "otel", protocol: "clickhouse"}},
  "mailpit":         {type: "smtp",       authentication: {smtp_server: "mailpit.keep", smtp_port: 1025, encryption: "None"}},
  "echo-sink":       {type: "webhook",    authentication: {url: "http://echo-sink.keep", method: "POST", verify: false}}
}')
$K -n keep create secret generic keep-providers \
  --from-literal=KEEP_PROVIDERS="$PROVIDERS" \
  --dry-run=client -o yaml | $K apply -f -

echo "Secrets created in namespace keep: keep-auth, keep-ui, keep-providers."
echo "Admin login: user 'keep'. Read the password with:"
echo "  kubectl -n keep get secret keep-auth -o jsonpath='{.data.KEEP_DEFAULT_PASSWORD}' | base64 -d"
