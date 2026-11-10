#!/usr/bin/env bash
# cleanup.sh: delete the capstone repos from Forgejo (and optionally the org). DESTRUCTIVE: it asks, and DRY_RUN=1 only prints.
#
#   export FORGEJO_URL=... FORGEJO_TOKEN=...
#   DRY_RUN=1 ./cleanup.sh ../work/repos.csv capstone       # show what would go
#   ./cleanup.sh ../work/repos.csv capstone [--delete-org]   # asks you to type the org name first
#
# Only repos named in the CSV are touched, so a typo in the org name cannot wipe other repos. The local folders are never deleted.
set -uo pipefail
CSV="${1:?repos.csv}"; ORG="${2:?org}"; DEL_ORG="${3:-}"
: "${FORGEJO_TOKEN:?set FORGEJO_TOKEN}"
API="${FORGEJO_URL:-http://forgejo.localhost:8080}/api/v1"
n="$(tail -n +2 "$CSV" | wc -l | tr -d ' ')"
if [ "${DRY_RUN:-0}" != 1 ]; then
  read -r -p "Delete $n repos from org '$ORG' at $API? Type the org name to confirm: " ans
  [ "$ans" = "$ORG" ] || { echo "aborted"; exit 1; }
fi
tail -n +2 "$CSV" | tr -d '\r' | cut -d, -f1 | while read -r name; do
  if [ "${DRY_RUN:-0}" = 1 ]; then echo "would delete $ORG/$name"; continue; fi
  code="$(curl -s -o /dev/null -w '%{http_code}' -X DELETE -H "Authorization: token $FORGEJO_TOKEN" "$API/repos/$ORG/$name")"
  echo "$code $ORG/$name"      # 204 deleted, 404 already gone
  sleep "${DELAY:-0.2}"
done
if [ "$DEL_ORG" = "--delete-org" ] && [ "${DRY_RUN:-0}" != 1 ]; then
  echo "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE -H "Authorization: token $FORGEJO_TOKEN" "$API/orgs/$ORG") org $ORG"
fi
