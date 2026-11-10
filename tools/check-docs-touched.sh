#!/usr/bin/env bash
# Docs gate: a change that touches code must also touch docs, or say why not.
#   check-docs-touched.sh [BASE_REF]
# Compares BASE_REF...HEAD (default: origin/main, else HEAD~1). Passes when
#   * no code path changed, or
#   * at least one docs path changed, or
#   * a commit in the range carries a trailer:   Docs: n/a <reason>
# Exit codes: 0 pass, 1 gate failed, 2 usage or git problem.
# Tuning (environment):
#   DOCS_CODE_RE   extended regex of paths that count as "code"   (default below)
#   DOCS_DOCS_RE   extended regex of paths that count as "docs"   (default below)
set -euo pipefail

CODE_RE="${DOCS_CODE_RE:-^(src|app|cmd|internal|pkg|lib|python|java|go|k8s|deploy|charts|helm)/|\.(py|java|go|cs|ts|js|rs)$|(^|/)Dockerfile$}"
DOCS_RE="${DOCS_DOCS_RE:-^docs/|(^|/)README(\.md)?$|(^|/)CHANGELOG(\.md)?$|(^|/)runbook\.md$|^adr/|\.mdx?$}"

git rev-parse --git-dir >/dev/null 2>&1 || { echo "check-docs-touched: not inside a git repository" >&2; exit 2; }

BASE="${1:-}"
if [ -z "$BASE" ]; then
  if git rev-parse --verify -q origin/main >/dev/null; then BASE="origin/main"
  elif git rev-parse --verify -q HEAD~1 >/dev/null; then BASE="HEAD~1"
  else echo "check-docs-touched: no base ref to compare with (pass one as an argument)" >&2; exit 2; fi
fi
git rev-parse --verify -q "$BASE" >/dev/null || { echo "check-docs-touched: unknown ref $BASE" >&2; exit 2; }

changed="$(git diff --name-only "$BASE"...HEAD 2>/dev/null || git diff --name-only "$BASE" HEAD)"
code="$(printf '%s\n' "$changed" | grep -E "$CODE_RE" | grep -vE "$DOCS_RE" || true)"
docs="$(printf '%s\n' "$changed" | grep -E "$DOCS_RE" || true)"

if [ -z "$code" ]; then echo "docs gate: no code changes, nothing to check"; exit 0; fi
if [ -n "$docs" ]; then echo "docs gate: code and docs both changed ($(printf '%s\n' "$docs" | wc -l | tr -d ' ') docs file(s))"; exit 0; fi

waiver="$(git log --format=%B "$BASE"..HEAD | grep -iE '^Docs: n/a( .+)?$' || true)"
if [ -n "$waiver" ]; then
  echo "docs gate: waived by trailer: $(printf '%s\n' "$waiver" | head -1)"
  exit 0
fi

{
  echo "docs gate FAILED: code changed but no documentation did."
  echo "Changed code files:"; printf '%s\n' "$code" | sed 's/^/  - /'
  echo "Fix: update the README, runbook, ADR or docs page that describes this change."
  echo "If no doc is needed, add a commit trailer with a reason, for example:  Docs: n/a refactor with no behaviour change"
} >&2
exit 1
