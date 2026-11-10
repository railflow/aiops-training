#!/usr/bin/env bash
# Build and serve the docs of this repository (Astro Starlight, in docs/).
#
#   ./build.sh                  install if needed, build, then serve the built site (default http://localhost:4321/)
#   ./build.sh --dev            dev server with live reload (no search index; search needs a build)
#   ./build.sh --build-only     install and build, print where the static files are, do not serve (for CI)
#   ./build.sh --port 4400      use another port (same as PORT=4400 ./build.sh)
#   ./build.sh --reinstall      delete docs/node_modules first, then install again
#   ./build.sh --help
#
# Needs Node.js 22.23.4 or newer and npm. Works on macOS, Linux and Windows through WSL. Installs nothing outside docs/.
set -euo pipefail

MIN_NODE_MAJOR=22
MIN_NODE_MINOR=23
MIN_NODE_PATCH=4
DEFAULT_PORT=4321

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS="$ROOT/docs"

mode=serve
reinstall=0
port="${PORT:-}"
port_explicit=0
[[ -z "$port" ]] || port_explicit=1

say() { printf '%s\n' "$*"; }
die() { printf 'build.sh: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Usage: ./build.sh [--dev | --build-only] [--port N] [--reinstall] [--help]

  (no flag)       install dependencies if needed, build the docs, serve them on http://localhost:4321/
  --dev           run the dev server with live reload (search is only available after a build)
  --build-only    build into docs/dist and stop (for CI or to copy the files elsewhere)
  --port N        port to serve on (default 4321; the PORT environment variable does the same)
  --reinstall     remove docs/node_modules and install again
  --help          show this text

Needs Node.js 22.23.4 or newer and npm.
USAGE
}

while (($#)); do
  case "$1" in
    --dev) mode=dev ;;
    --build-only) mode=build ;;
    --reinstall) reinstall=1 ;;
    --port)
      (($# >= 2)) || die "--port needs a number, for example: ./build.sh --port 4400"
      port="$2"; port_explicit=1; shift ;;
    --port=*) port="${1#--port=}"; port_explicit=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
  shift
done

if [[ -n "$port" ]]; then
  if [[ ! "$port" =~ ^[0-9]+$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
    die "port must be a number from 1 to 65535 (got '$port')"
  fi
  port=$((10#$port))
else
  port="$DEFAULT_PORT"
fi

command -v node >/dev/null 2>&1 || die "node was not found. Install Node.js ${MIN_NODE_MAJOR}.${MIN_NODE_MINOR}.${MIN_NODE_PATCH} or newer from https://nodejs.org/ (or: nvm install ${MIN_NODE_MAJOR}), open a new terminal, and run ./build.sh again."
command -v npm >/dev/null 2>&1 || die "npm was not found. It ships with Node.js; reinstall Node.js from https://nodejs.org/."

node_version="$(node --version)"
node_major="${node_version#v}"; node_major="${node_major%%.*}"
node_rest="${node_version#v*.}"
node_minor="${node_rest%%.*}"
node_patch="${node_rest#*.}"; node_patch="${node_patch%%[!0-9]*}"
if ((node_major < MIN_NODE_MAJOR || (node_major == MIN_NODE_MAJOR && (node_minor < MIN_NODE_MINOR || (node_minor == MIN_NODE_MINOR && node_patch < MIN_NODE_PATCH))))); then
  die "Node.js ${MIN_NODE_MAJOR}.${MIN_NODE_MINOR}.${MIN_NODE_PATCH} or newer is required, found ${node_version}. Upgrade (for example: nvm install ${MIN_NODE_MAJOR}) and run ./build.sh again."
fi
say "node ${node_version}, npm $(npm --version)"

[[ -f "$DOCS/package.json" ]] || die "docs/package.json is missing. Run ./build.sh from a full clone of the repository."
cd "$DOCS"

if ((reinstall)); then
  say "Removing docs/node_modules"
  rm -rf node_modules
fi

# npm writes node_modules/.package-lock.json after every install; a newer package-lock.json means the install is stale.
if [[ ! -d node_modules || ! -f node_modules/.package-lock.json || package-lock.json -nt node_modules/.package-lock.json ]]; then
  say "Installing docs dependencies (npm ci)"
  npm ci --no-audit --no-fund --loglevel=error || die "npm ci failed. Try ./build.sh --reinstall; if it still fails, check your network and the npm error above."
else
  say "Dependencies are up to date (docs/node_modules)"
fi

port_busy() {
  local p="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$p" >/dev/null 2>&1
  else
    (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null
  fi
}

choose_port() {
  if port_busy "$port"; then
    if ((port_explicit)); then
      die "port $port is already in use. Pick another one: ./build.sh --port $((port + 1))  (or stop the program that uses it)."
    fi
    local p=$((port + 1))
    while ((p < port + 20)) && port_busy "$p"; do p=$((p + 1)); done
    ((p < port + 20)) || die "no free port found between $port and $((port + 19)). Use ./build.sh --port N."
    say "Port $port is busy, using $p instead"
    port="$p"
  fi
}

case "$mode" in
  dev)
    choose_port
    say "Dev server: http://localhost:${port}/  (Ctrl+C to stop; search needs a build, use ./build.sh)"
    exec npm run dev --silent -- --host 127.0.0.1 --port "$port"
    ;;
  build|serve)
    say "Building the docs (full output: docs/.build.log)"
    if ! npm run build --silent >.build.log 2>&1; then
      tail -n 40 .build.log >&2
      die "the docs build failed; the lines above are the end of docs/.build.log"
    fi
    pages="$(find dist -name '*.html' | wc -l | tr -d ' ')"
    say "Built ${pages} pages into docs/dist"
    if [[ "$mode" == build ]]; then
      say "Static output: docs/dist (plain HTML, CSS and JS; any static web server can serve it)"
      exit 0
    fi
    choose_port
    say "Docs: http://localhost:${port}/  (Ctrl+C to stop)"
    exec npm run preview --silent -- --host 127.0.0.1 --port "$port"
    ;;
esac
