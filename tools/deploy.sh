#!/usr/bin/env bash
# deploy.sh: ask the policy engine whether this deploy is allowed, then deploy with kubectl.
#
#   deploy.sh IMAGE [--service NAME] [--namespace NS] [--dry-run]
#
# Inputs it gathers (all can be overridden for tests):
#   coverage        from reports/coverage.xml or reports/jacoco.xml   (override: COVERAGE)
#   vulnerabilities from reports/trivy-fs.json or reports/trivy-image.json  (override: VULN_CRITICAL, VULN_HIGH)
#   clock/timezone  now, in TIMEZONE (default UTC)                    (override: NOW_NS)
# Policy: OPA_URL (an OPA server, e.g. http://opa.platform:8181) or, if unset, `opa eval` on POLICY_DIR.
#
# Exit codes: 0 deployed (or allowed in dry run), 1 denied or deploy failed, 2 usage or missing input.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_DIR="${POLICY_DIR:-$SCRIPT_DIR/../day-15-guard-rails-and-opa/policies}"
REPORT_DIR="${REPORT_DIR:-reports}"
NAMESPACE="apps"
SERVICE=""
DRY_RUN=0
IMAGE=""

die() { echo "deploy.sh: $*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --service) shift; SERVICE="${1:?}" ;;
    --namespace) shift; NAMESPACE="${1:?}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) die "unknown flag: $1" ;;
    *) IMAGE="$1" ;;
  esac
  shift
done
[ -n "$IMAGE" ] || die "usage: deploy.sh IMAGE [--service NAME] [--namespace NS] [--dry-run]"
SERVICE="${SERVICE:-$(basename "${IMAGE%%:*}")}"

command -v jq >/dev/null || die "jq is required"

coverage="${COVERAGE:-}"
if [ -z "$coverage" ]; then
  for f in "$REPORT_DIR/coverage.xml" "$REPORT_DIR/jacoco.xml"; do
    [ -f "$f" ] && { coverage="$(python3 "$SCRIPT_DIR/coverage_percent.py" "$f")"; break; }
  done
fi
[ -n "$coverage" ] || die "no coverage report in $REPORT_DIR and COVERAGE is not set"

critical="${VULN_CRITICAL:-}"; high="${VULN_HIGH:-}"
if [ -z "$critical" ] || [ -z "$high" ]; then
  for f in "$REPORT_DIR/trivy-image.json" "$REPORT_DIR/trivy-fs.json"; do
    if [ -f "$f" ]; then
      critical="$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$f")"
      high="$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$f")"
      break
    fi
  done
fi
[ -n "$critical" ] && [ -n "$high" ] || die "no vulnerability report in $REPORT_DIR and VULN_CRITICAL/VULN_HIGH are not set"

now_ns="${NOW_NS:-$(python3 -c 'import time; print(time.time_ns())')}"

input="$(jq -nc --arg service "$SERVICE" --arg image "$IMAGE" --argjson coverage "$coverage" \
  --argjson critical "$critical" --argjson high "$high" --arg tz "${TIMEZONE:-UTC}" --argjson now "$now_ns" \
  '{service:$service, image:$image, coverage:$coverage, vulnerabilities:{critical:$critical, high:$high}, timezone:$tz, now_ns:$now}')"

echo "deploy.sh: asking the policy about: $input"

if [ -n "${OPA_URL:-}" ]; then
  decision="$(curl -sf -X POST "$OPA_URL/v1/data/deploy/decision" -H 'Content-Type: application/json' -d "{\"input\": $input}" | jq -c '.result')" \
    || die "could not reach the policy server at $OPA_URL"
else
  command -v opa >/dev/null || die "opa is not installed and OPA_URL is not set"
  decision="$(printf '%s' "$input" | opa eval --format json -d "$POLICY_DIR" --stdin-input 'data.deploy.decision' | jq -c '.result[0].expressions[0].value')"
fi

[ "$decision" != "null" ] && [ -n "$decision" ] || die "the policy returned no decision (is the package named deploy?)"

if [ "$(echo "$decision" | jq -r '.allow')" != "true" ]; then
  echo "deploy.sh: DENIED"
  echo "$decision" | jq -r '.reasons[] | "  - " + .'
  exit 1
fi

echo "deploy.sh: ALLOWED"
cmd=(kubectl -n "$NAMESPACE" set image "deploy/$SERVICE" "$SERVICE=$IMAGE")
echo "+ ${cmd[*]}"
if [ "$DRY_RUN" -eq 1 ]; then echo "deploy.sh: dry run, not deploying"; exit 0; fi
"${cmd[@]}"
kubectl -n "$NAMESPACE" rollout status "deploy/$SERVICE" --timeout=180s
