#!/usr/bin/env bash
# Checks the docs image build path without Docker: every COPY source in deploy/Dockerfile exists and is not excluded by
# Dockerfile.dockerignore, the lockfile matches package.json, and a fake `docker` on PATH records the command from Day 28.
# Set REAL_DOCKER=1 to also run the real build (needs a running Docker daemon and network). No installs otherwise.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DF="$HERE/deploy/Dockerfile"
SITE="$HERE/starlight-site"
pass=0; fail=0
ok()   { pass=$((pass+1)); echo "ok   $1"; }
bad()  { fail=$((fail+1)); echo "FAIL $1"; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

while read -r src; do
  check "COPY source exists: $src" "[ -e '$ROOT/${src%/}' ]"
done < <(awk '/^COPY/ && !/--from=/ { for (i=2;i<NF;i++) if ($i !~ /^--/) print $i }' "$DF")

check "Dockerfile builds the example, not docs/" "grep -q 'day-28-write-good-docs/docs-as-code/starlight-site/' '$DF' && ! grep -qE '^COPY docs/' '$DF'"
check "starlight-site has package.json and package-lock.json" "[ -f '$SITE/package.json' ] && [ -f '$SITE/package-lock.json' ]"
check "lockfile name matches package.json" "node -e \"const p=require('$SITE/package.json'),l=require('$SITE/package-lock.json'); process.exit(p.name===l.name?0:1)\""
check "astro config, content config and an index page exist" "[ -f '$SITE/astro.config.mjs' ] && [ -f '$SITE/src/content.config.ts' ] && ls '$SITE'/src/content/docs/index.md* >/dev/null 2>&1"
check "dockerignore does not exclude the example" "grep -q '^!day-28-write-good-docs/docs-as-code/' '$DF.dockerignore'"
check "dockerignore keeps node_modules and dist out" "grep -q 'node_modules' '$DF.dockerignore' && grep -q 'dist' '$DF.dockerignore'"
check "nginx.conf is copied from deploy/" "[ -f '$HERE/deploy/nginx.conf' ] && grep -q 'day-28-write-good-docs/docs-as-code/deploy/nginx.conf' '$DF'"

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir "$T/bin"
printf '#!/bin/sh\necho "$@" >> "%s/docker.calls"\nexit 0\n' "$T" > "$T/bin/docker"; chmod +x "$T/bin/docker"
CMD="$(grep -m1 -oE 'docker build -f [^ ]+ -t [^ ]+ \.' "$DF")"
( cd "$ROOT" && PATH="$T/bin:$PATH" $CMD ) >/dev/null 2>&1
check "the documented docker build command runs from the repo root" "grep -q -- '-f day-28-write-good-docs/docs-as-code/deploy/Dockerfile' '$T/docker.calls'"

if [ "${REAL_DOCKER:-}" = 1 ]; then
  check "real docker build" "cd '$ROOT' && docker build -q -f day-28-write-good-docs/docs-as-code/deploy/Dockerfile -t docs-site:test . >/dev/null"
fi

echo; echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
