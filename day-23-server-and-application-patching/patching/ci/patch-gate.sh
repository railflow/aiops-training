#!/usr/bin/env bash
# Scan source and image, write an SBOM, and fail when a fixable HIGH/CRITICAL finding exists.
# Uses the course's pinned Trivy and Syft CONTAINER images, so nothing is installed on the machine.
#   ./patch-gate.sh <image> [source-dir]
# Exit codes: 0 clean, 1 findings, 2 usage/tooling problem.
set -euo pipefail

IMAGE="${1:-}"
SRC="${2:-app}"
[ -n "$IMAGE" ] || { echo "usage: $0 <image> [source-dir]" >&2; exit 2; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 2; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$HERE/../../tools/versions.env"
OUT="$HERE/out"
mkdir -p "$OUT"

TRIVY=(docker run --rm -v "$HERE:/work" -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache -w /work "$TRIVY_IMAGE")
SYFT=(docker run --rm -v "$HERE:/work" -v /var/run/docker.sock:/var/run/docker.sock -w /work "$SYFT_IMAGE")

echo "== 1. dependency files (before building anything)"
"${TRIVY[@]}" fs --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$SRC" || FS_RC=$?

echo "== 2. the image"
"${TRIVY[@]}" image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$IMAGE" || IMG_RC=$?

echo "== 3. SBOM (CycloneDX)"
NAME="$(echo "$IMAGE" | tr '/:@' '___')"
"${SYFT[@]}" "$IMAGE" -o "cyclonedx-json=/work/out/${NAME}.cdx.json"
echo "wrote $OUT/${NAME}.cdx.json"

if [ "${FS_RC:-0}" -ne 0 ] || [ "${IMG_RC:-0}" -ne 0 ]; then
  echo "GATE FAILED: fixable HIGH/CRITICAL findings (fs=${FS_RC:-0} image=${IMG_RC:-0})" >&2
  exit 1
fi
echo "GATE PASSED"
