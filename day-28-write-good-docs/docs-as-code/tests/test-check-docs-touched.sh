#!/usr/bin/env bash
# Tests for tools/check-docs-touched.sh against throwaway git repositories. No network, no installs.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$HERE/../../tools/check-docs-touched.sh"
pass=0; fail=0
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.com GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.com

new_repo() { rm -rf "$T/r"; mkdir -p "$T/r/src" "$T/r/docs"; cd "$T/r"; git init -q -b main; echo a > src/app.py; echo a > docs/guide.md; git add -A; git commit -q -m base; git checkout -q -b feature; }
expect() { # name expected-exit command...
  local name="$1" want="$2"; shift 2
  "$@" >/tmp/cdt.out 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then pass=$((pass+1)); echo "ok   $name"; else fail=$((fail+1)); echo "FAIL $name (exit $got, wanted $want)"; sed 's/^/     /' /tmp/cdt.out; fi
}

new_repo; echo b >> src/app.py; git commit -qam "change code only"
expect "code only fails" 1 "$SCRIPT" main

new_repo; echo b >> src/app.py; echo b >> docs/guide.md; git commit -qam "code and docs"
expect "code and docs passes" 0 "$SCRIPT" main

new_repo; echo b >> docs/guide.md; git commit -qam "docs only"
expect "docs only passes" 0 "$SCRIPT" main

new_repo; echo b >> src/app.py; git commit -q -am "refactor" -m "Docs: n/a pure refactor, no behaviour change"
expect "waiver trailer passes" 0 "$SCRIPT" main

new_repo; echo b >> src/app.py; git commit -q -am "mentions docs" -m "I forgot the docs: n/a is not a trailer here"
expect "prose mention is not a waiver" 1 "$SCRIPT" main

new_repo; echo x > notes.txt; git add -A; git commit -qm "non-code file"
expect "non-code change passes" 0 "$SCRIPT" main

expect "unknown ref is a usage error" 2 "$SCRIPT" no-such-ref

echo "passed=$pass failed=$fail"; [ "$fail" -eq 0 ]
