#!/usr/bin/env bash
# Claude Code PostToolUse hook: after an edit to a docs file, warn about obvious problems (secret-looking strings, TODO/TBD).
# The hook receives the tool call as JSON on stdin (field names: check the Claude Code hooks docs for your version).
# Exit 0 = fine. Exit 2 = send stderr back to Claude so it fixes the file.
set -uo pipefail
file="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -n "$file" ] || exit 0
case "$file" in *.md|*.mdx) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0
problems=""
if grep -nEi '(password|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*[^[:space:]<$]{8,}' "$file" >/dev/null; then
  problems+="possible secret value in $file (document where it lives, not what it is)\n"
fi
if grep -nE '\b(TODO|TBD|FIXME)\b' "$file" >/dev/null; then
  problems+="TODO/TBD left in $file (open an issue and link it)\n"
fi
if [ -n "$problems" ]; then printf "%b" "$problems" >&2; exit 2; fi
exit 0
