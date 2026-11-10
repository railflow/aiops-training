#!/usr/bin/env bash
# Create (or delete) the "before" scenario: three teams, each with a private Postgres.
#   ./before.sh apply        ./before.sh delete
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for team in alpha beta gamma; do
  case "${1:-}" in
    apply) sed "s/__TEAM__/$team/g" "$HERE/team-postgres.yaml.tpl" | kubectl apply -f - ;;
    delete) sed "s/__TEAM__/$team/g" "$HERE/team-postgres.yaml.tpl" | kubectl delete --ignore-not-found -f - ;;
    *) echo "usage: $0 apply|delete" >&2; exit 2 ;;
  esac
done
