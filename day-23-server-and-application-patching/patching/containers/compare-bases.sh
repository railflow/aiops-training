#!/usr/bin/env bash
# Build the demo app on several bases and print size and HIGH/CRITICAL counts side by side.
#   ./containers/compare-bases.sh
# Requires docker. Trivy runs as the course's pinned container. Counts change daily: capture your own.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
. ../../tools/versions.env
printf '%-22s %10s %9s %9s\n' VARIANT SIZE_MB HIGH CRITICAL
for v in full slim alpine slim-hardened; do
  tag="patch-demo:base-$v"
  docker build -q -f "containers/Dockerfile.$v" -t "$tag" app >/dev/null
  size=$(docker image inspect "$tag" --format '{{.Size}}')
  json=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache "$TRIVY_IMAGE" image -q -f json "$tag")
  high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' <<<"$json")
  crit=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' <<<"$json")
  printf '%-22s %10s %9s %9s\n' "$v" "$((size / 1000000))" "$high" "$crit"
done
