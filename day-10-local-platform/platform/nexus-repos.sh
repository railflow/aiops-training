#!/usr/bin/env bash
# Create three hosted repositories in Nexus through its REST API: Docker (port 5000), Maven, and PyPI.
# Usage: NEXUS_PASSWORD=... ./nexus-repos.sh      (admin password is read from the environment, never stored)
# The request bodies follow the Nexus REST API; check http://localhost:30081/service/rest/swagger.json if your version differs.
set -euo pipefail
BASE="${NEXUS_URL:-http://localhost:30081}"
AUTH=(-u "admin:${NEXUS_PASSWORD:?set NEXUS_PASSWORD}")
post() {
  local path="$1" body="$2"
  code=$(curl -s -o /tmp/nexus.out -w '%{http_code}' "${AUTH[@]}" -H 'Content-Type: application/json' -X POST "$BASE/service/rest/v1/repositories/$path" -d "$body")
  echo "POST $path -> HTTP $code"
  [ "$code" = 201 ] || [ "$code" = 400 ] || { cat /tmp/nexus.out; exit 1; }
}
STORAGE='"storage":{"blobStoreName":"default","strictContentTypeValidation":true,"writePolicy":"ALLOW"}'
post docker/hosted "{\"name\":\"docker-hosted\",\"online\":true,$STORAGE,\"docker\":{\"v1Enabled\":false,\"forceBasicAuth\":true,\"httpPort\":5000}}"
post maven/hosted  "{\"name\":\"maven-releases\",\"online\":true,$STORAGE,\"maven\":{\"versionPolicy\":\"RELEASE\",\"layoutPolicy\":\"STRICT\"}}"
post pypi/hosted   "{\"name\":\"pypi-hosted\",\"online\":true,$STORAGE}"
