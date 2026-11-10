#!/usr/bin/env bash
# push_repos.sh: the bash twin of push_repos.py (curl + jq + git + xargs -P). Same steps, same idempotency, same environment variables.
#
#   export FORGEJO_URL=http://forgejo.localhost:8080 FORGEJO_TOKEN=... [WEBHOOK_SECRET=...] [WEBHOOK_URL=...]
#   ./push_repos.sh ../work/repos.csv [ORG=capstone] [PARALLEL=4] [LIMIT=0]
#
# CSV: name,language,domain,owner_team,path (header row skipped, no quoted commas). Prints one line per repo and a summary; exit 1 if any failed.
set -uo pipefail
CSV="${1:?repos.csv}"; ORG="${2:-capstone}"; PAR="${3:-4}"; LIMIT="${4:-0}"
: "${FORGEJO_TOKEN:?set FORGEJO_TOKEN (never commit it)}"
FORGEJO_URL="${FORGEJO_URL:-http://forgejo.localhost:8080}"
GIT_URL="${FORGEJO_GIT_URL:-$FORGEJO_URL}"
HERE="$(cd "$(dirname "$0")" && pwd)"
CSV_DIR="$(cd "$(dirname "$CSV")" && pwd)"
API="${FORGEJO_URL%/}/api/v1"
export ORG API GIT_URL HERE CSV_DIR FORGEJO_TOKEN WEBHOOK_URL="${WEBHOOK_URL:-}" WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"
# git reads the token from the environment: not in argv, not in .git/config, not in the remote URL.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader GIT_CONFIG_VALUE_0="Authorization: token $FORGEJO_TOKEN" GIT_TERMINAL_PROMPT=0

# api METHOD PATH [JSON]: prints "<status> <body>"; retries 429/5xx with exponential backoff.
api() {
  local m="$1" p="$2" d="${3:-}" try out code
  for try in 0 1 2 3 4; do
    if [ -n "$d" ]; then out="$(curl -s -w '\n%{http_code}' -X "$m" -H "Authorization: token $FORGEJO_TOKEN" -H 'Content-Type: application/json' -d "$d" "$API$p")"
    else out="$(curl -s -w '\n%{http_code}' -X "$m" -H "Authorization: token $FORGEJO_TOKEN" "$API$p")"; fi
    code="${out##*$'\n'}"
    if [ "$code" = 429 ] || [ "$code" -ge 500 ] 2>/dev/null || [ "$code" = 000 ]; then sleep $((2 ** try)); continue; fi
    break
  done
  printf '%s %s' "$code" "${out%$'\n'*}"
}
export -f api

one() {
  IFS=, read -r name lang domain team path <<<"$1"
  [[ "$path" = /* ]] || path="$CSV_DIR/$path"
  local steps="" r code
  r="$(api GET "/repos/$ORG/$name")"; code="${r%% *}"
  if [ "$code" = 404 ]; then
    r="$(api POST "/orgs/$ORG/repos" "$(jq -nc --arg n "$name" --arg d "$lang $domain service (capstone, owner $team)" '{name:$n,description:$d,private:true,default_branch:"main",auto_init:false}')")"
    case "${r%% *}" in 200|201) steps="created" ;; *) echo "FAILED $name create repo: ${r:0:160}"; return 1 ;; esac
  elif [ "$code" = 200 ]; then steps="exists"; else echo "FAILED $name lookup: $code"; return 1; fi
  api PATCH "/repos/$ORG/$name" '{"has_issues":true,"has_projects":true,"default_branch":"main"}' >/dev/null
  api PUT "/repos/$ORG/$name/topics" "$(jq -nc --arg l "$lang" --arg d "$domain" --arg t "$team" '{topics:([$l,$d,"capstone",$t]|unique)}')" >/dev/null
  have="$(api GET "/repos/$ORG/$name/labels?limit=50" | cut -d' ' -f2- | jq -r '.[]?.name' 2>/dev/null)"
  while IFS='|' read -r ln color desc; do
    grep -qx -- "$ln" <<<"$have" || api POST "/repos/$ORG/$name/labels" "$(jq -nc --arg n "$ln" --arg c "#$color" --arg d "$desc" '{name:$n,color:$c,description:$d}')" >/dev/null
  done <<'LABELS'
bug|d73a4a|Something is broken
ai-found|7057ff|Filed by an agent
coverage|0e8a16|Test coverage work
security|b60205|Security issue
ai-fix|1d76db|An agent may attempt the fix
status/todo|ededed|Board column: to do
status/doing|fbca04|Board column: in progress
status/review|0052cc|Board column: in review
status/done|0e8a16|Board column: done
LABELS
  if [ -n "$WEBHOOK_URL" ]; then
    hooks="$(api GET "/repos/$ORG/$name/hooks" | cut -d' ' -f2-)"
    if ! jq -e --arg u "$WEBHOOK_URL" 'map(select(.config.url==$u))|length>0' <<<"$hooks" >/dev/null 2>&1; then
      api POST "/repos/$ORG/$name/hooks" "$(jq -nc --arg u "$WEBHOOK_URL" --arg s "$WEBHOOK_SECRET" \
        '{type:"forgejo",active:true,events:["push","pull_request","issues","issue_comment"],config:({url:$u,content_type:"json"} + (if $s=="" then {} else {secret:$s} end))}')" >/dev/null
      steps="$steps,hook"
    fi
  fi
  [ -d "$path" ] || { echo "FAILED $name local path $path is missing"; return 1; }
  if [ ! -f "$path/.forgejo/workflows/ci.yaml" ]; then
    mkdir -p "$path/.forgejo/workflows" && cp "$HERE/ci.yaml" "$path/.forgejo/workflows/ci.yaml"
    git -C "$path" add .forgejo && git -C "$path" -c user.name=capstone -c user.email=capstone@example.com commit -q -m "Add golden-path CI workflow"
    steps="$steps,ci-commit"
  fi
  remote="${GIT_URL%/}/$ORG/$name.git"
  git -C "$path" remote get-url forgejo >/dev/null 2>&1 && git -C "$path" remote set-url forgejo "$remote" || git -C "$path" remote add forgejo "$remote"
  if err="$(git -C "$path" push -u forgejo main 2>&1)"; then echo "OK     $name $steps,pushed"; else echo "FAILED $name push: ${err: -160}"; return 1; fi
}
export -f one

# org (create if missing)
r="$(api GET "/orgs/$ORG")"
[ "${r%% *}" = 200 ] || api POST "/orgs" "$(jq -nc --arg u "$ORG" '{username:$u,visibility:"private"}')" >/dev/null

rows="$(tail -n +2 "$CSV" | tr -d '\r')"; [ "$LIMIT" -gt 0 ] && rows="$(head -n "$LIMIT" <<<"$rows")"
out="$(mktemp)"
# xargs -P runs PARALLEL workers; each prints exactly one line.
printf '%s\n' "$rows" | xargs -P "$PAR" -I{} bash -c 'one "$@"' _ {} | tee "$out"
ok="$(grep -c '^OK' "$out" || true)"; bad="$(grep -c '^FAILED' "$out" || true)"
echo; echo "summary: $ok ok, $bad failed"
rm -f "$out"; [ "$bad" -eq 0 ]
