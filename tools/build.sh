#!/usr/bin/env bash
# build.sh: one central build script for every repo.
#
#   build.sh [build] [test] [secure] [measure] [deploy] [docs] [--java|--gradle|--python|--node|--go|--dotnet] [--dir DIR] [--dry-run]
#
# With no step names, runs: build test secure. The stack is auto-detected from the files in DIR
# (default: current directory) unless a stack flag forces it.
#
# Exit codes: 0 success, 1 a step failed, 2 usage error or stack not detected.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="."
STACK=""
DRY_RUN=0
STEPS=()

REPORT_DIR="${REPORT_DIR:-reports}"
REGISTRY="${REGISTRY:-localhost:30500}"
TRIVY_SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"

usage() {
  sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() { echo "build.sh: $*" >&2; exit 2; }
log() { printf '\n==> %s\n' "$*"; }

run() {
  echo "+ $*"
  if [ "$DRY_RUN" -eq 0 ]; then "$@"; fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    build|test|secure|measure|deploy|docs) STEPS+=("$1") ;;
    --java) STACK="java-maven" ;;
    --gradle) STACK="java-gradle" ;;
    --python) STACK="python" ;;
    --node) STACK="node" ;;
    --go) STACK="go" ;;
    --dotnet) STACK="dotnet" ;;
    --dir) shift; DIR="${1:?--dir needs a value}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" ;;
  esac
  shift
done

[ ${#STEPS[@]} -gt 0 ] || STEPS=(build test secure)
cd "$DIR" || die "cannot enter $DIR"

detect_stack() {
  if   [ -f pom.xml ]; then echo java-maven
  elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then echo java-gradle
  elif [ -f requirements.txt ] || [ -f pyproject.toml ]; then echo python
  elif [ -f go.mod ]; then echo go
  elif [ -f package.json ]; then echo node
  elif [ -n "$(find . -maxdepth 3 -name '*.csproj' -not -path './node_modules/*' | head -1)" ]; then echo dotnet
  else echo ""; fi
}

[ -n "$STACK" ] || STACK="$(detect_stack)"
# A docs-only run (build.sh docs) needs no language stack.
if [ -z "$STACK" ] && [ "${#STEPS[@]}" -eq 1 ] && [ "${STEPS[0]}" = "docs" ]; then STACK="none"; fi
[ -n "$STACK" ] || die "could not detect the stack in $(pwd) (looked for pom.xml, build.gradle, requirements.txt, pyproject.toml, go.mod, package.json, *.csproj)"

NAME="${IMAGE_NAME:-$(basename "$(pwd)")}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
IMAGE="$REGISTRY/$NAME:$TAG"
[ "$DRY_RUN" -eq 1 ] || mkdir -p "$REPORT_DIR"

echo "build.sh: stack=$STACK steps=${STEPS[*]} dir=$(pwd) image=$IMAGE dry-run=$DRY_RUN"

step_build() {
  log "build ($STACK)"
  case "$STACK" in
    java-maven)  run mvn -B -DskipTests package ;;
    java-gradle) run gradle --no-daemon assemble ;;
    python)
      run python3 -m venv .venv
      run .venv/bin/pip install -q -r "$( [ -f requirements-dev.txt ] && echo requirements-dev.txt || echo requirements.txt )" ;;
    node) run npm ci --no-audit --no-fund ;;
    go)   run go build ./... ;;
    dotnet) run dotnet build --nologo ;;
  esac
  if [ -f Dockerfile ] || [ -f Dockerfile.app ]; then
    local df="Dockerfile"; [ -f Dockerfile.app ] && df="Dockerfile.app"
    if [ -n "${BUILDKIT_HOST:-}" ] && command -v buildctl >/dev/null 2>&1; then
      run buildctl build --frontend dockerfile.v0 --local context=. --local dockerfile=. \
        --opt filename="$df" --output "type=image,name=$IMAGE,push=${PUSH:-false},registry.insecure=true"
    else
      run docker build -f "$df" -t "$IMAGE" .
    fi
  fi
}

step_test() {
  log "test ($STACK)"
  case "$STACK" in
    java-maven)  run mvn -B test
                 run cp -r target/surefire-reports "$REPORT_DIR/surefire" 2>/dev/null || true
                 run cp target/site/jacoco/jacoco.xml "$REPORT_DIR/jacoco.xml" 2>/dev/null || true ;;
    java-gradle) run gradle --no-daemon test jacocoTestReport ;;
    python)      run .venv/bin/pytest --cov=. --cov-report=term --cov-report=xml:"$REPORT_DIR/coverage.xml" --junitxml="$REPORT_DIR/junit.xml" ;;
    node)        run npm test ;;
    go)          run go test -cover -coverprofile="$REPORT_DIR/cover.out" ./... ;;
    dotnet)      run dotnet test --nologo --collect:"XPlat Code Coverage" --results-directory "$REPORT_DIR/dotnet" ;;
  esac
}

# measure: run the tests with coverage and print ONE JSON measurement document (capstone). With MEASURE_SHIP=1 it is also inserted into
# ClickHouse (CLICKHOUSE_URL / CLICKHOUSE_USER / CLICKHOUSE_PASSWORD from the environment, never from a file in git).
step_measure() {
  log "measure ($STACK)"
  local tool="${MEASURE_PY:-$SCRIPT_DIR/measure.py}"
  [ -f "$tool" ] || tool="$SCRIPT_DIR/../capstone/measure/measure.py"
  [ -f "$tool" ] || die "measure.py not found at $tool (copy capstone/measure/{measure,ship}.py next to build.sh, or run it from this repository)"
  local doc="$REPORT_DIR/measurement.json"
  run python3 "$tool" --dir . --report-dir "$REPORT_DIR" --out "$doc" ${RUN_ID:+--run-id "$RUN_ID"} ${ITERATION:+--iteration "$ITERATION"} ${AGENT_RUN_ID:+--agent-run-id "$AGENT_RUN_ID"}
  [ "$DRY_RUN" -eq 1 ] || cat "$doc"
  if [ "${MEASURE_SHIP:-0}" = "1" ]; then
    local ship="${SHIP_PY:-$SCRIPT_DIR/ship.py}"
    [ -f "$ship" ] || ship="$SCRIPT_DIR/../capstone/measure/ship.py"
    run python3 "$ship" --file "$doc"
  fi
}

step_secure() {
  log "secure ($STACK)"
  [ "$DRY_RUN" -eq 1 ] || command -v gitleaks >/dev/null 2>&1 || die "gitleaks is not installed (use the builder image, or install it)"
  [ "$DRY_RUN" -eq 1 ] || command -v trivy >/dev/null 2>&1 || die "trivy is not installed (use the builder image, or install it)"
  local failed=0
  # Secrets in the working tree AND in git history (history needs a full clone: fetch-depth 0 in CI).
  run gitleaks detect --source . --redact --no-banner --exit-code 1 \
    --report-format json --report-path "$REPORT_DIR/gitleaks.json" || failed=1
  # Known-vulnerable dependencies plus Trivy's own secret detection on the files.
  run trivy fs --scanners vuln,secret --severity "$TRIVY_SEVERITY" --exit-code 1 \
    --format json --output "$REPORT_DIR/trivy-fs.json" . || failed=1
  if [ "$failed" -ne 0 ]; then
    echo "build.sh: secure step found problems; see $REPORT_DIR/gitleaks.json and $REPORT_DIR/trivy-fs.json" >&2
    exit 1
  fi
}

step_deploy() {
  log "deploy"
  local script="${DEPLOY_SCRIPT:-$SCRIPT_DIR/deploy.sh}"
  [ -x "$script" ] || die "deploy script not found at $script (it is introduced in Day 15)"
  run "$script" "$IMAGE"
}

step_docs() {
  log "docs"
  # The gate: code changes must come with docs, or a "Docs: n/a <reason>" commit trailer (Day 28).
  local gate="${DOCS_GATE:-$SCRIPT_DIR/check-docs-touched.sh}"
  [ -x "$gate" ] || die "docs gate not found at $gate (copy tools/check-docs-touched.sh next to build.sh)"
  run "$gate" ${DOCS_BASE:+"$DOCS_BASE"}
  # A docs site in ./docs (Starlight or similar): its build also runs the link checker when the plugin is configured.
  if [ -f docs/package.json ]; then
    run npm --prefix docs ci --no-audit --no-fund
    run npm --prefix docs run build
  fi
}

for s in "${STEPS[@]}"; do
  "step_$s"
done

log "done: ${STEPS[*]} succeeded"
