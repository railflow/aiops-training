#!/usr/bin/env bash
# gen_with_claude.sh: generate repos with a coding model in headless mode, in parallel.
#
#   ./gen_with_claude.sh spec.csv ./repos [PARALLEL]
#
# spec.csv columns: name,language,domain,seed   (a header row is skipped)
#
# NOT RUN by the course author: it spends real money. Check `claude --help` for your version's flags before you use it; the ones used here
# (-p, --output-format, --permission-mode, --allowedTools, --max-budget-usd, --no-session-persistence) exist in Claude Code 2.1.278.
# Start with ONE repo, read the bill, then scale. Every repo costs tokens; 100 repos at a few dollars each is a real budget decision.
set -euo pipefail
SPEC="${1:?spec.csv}"; OUT="${2:?output dir}"; PAR="${3:-3}"
PROMPT_FILE="$(cd "$(dirname "$0")" && pwd)/prompts/repo-generation.md"
BUDGET="${BUDGET_USD:-5}"            # per repo hard cap (--max-budget-usd, print mode only)
TARGET_LOC="${TARGET_LOC:-10000}"
mkdir -p "$OUT"

one() {
  IFS=, read -r name lang domain seed <<<"$1"
  dir="$OUT/$name"
  [ -d "$dir/.git" ] && { echo "skip $name (exists)"; return 0; }
  mkdir -p "$dir"
  prompt="$(sed -n '/^---$/,$p' "$PROMPT_FILE" | tail -n +2 \
    | sed -e "s/{{name}}/$name/g" -e "s/{{language}}/$lang/g" -e "s/{{domain}}/$domain/g" -e "s/{{seed}}/$seed/g" \
          -e "s/{{target_loc}}/$TARGET_LOC/g" -e "s/{{min_files}}/20/g" -e "s/{{min_bugs}}/6/g" -e "s/{{max_bugs}}/12/g" \
          -e "s/{{domain_description}}/a typical internal $domain service/g" -e "s/{{build_command}}/the standard build/g" -e "s/{{test_command}}/the standard test command/g")"
  ( cd "$dir" && git init -q -b main \
    && claude -p "$prompt" --output-format json --permission-mode acceptEdits --allowedTools "Write" "Edit" "Read" "Bash" \
         --max-budget-usd "$BUDGET" --no-session-persistence > "../$name.claude.json" 2> "../$name.claude.err" ) \
    || { echo "FAILED $name (see $OUT/$name.claude.err)"; return 1; }
  # The answer key must not travel with the repo.
  mkdir -p "$OUT/../answer-keys"
  [ -f "$dir/.planted-issues.json" ] && mv "$dir/.planted-issues.json" "$OUT/../answer-keys/$name.planted-issues.json"
  ( cd "$dir" && git add -A && git -c user.name=generator -c user.email=generator@example.com commit -q -m "Initial commit" )
  echo "done $name"
}
export -f one; export OUT PROMPT_FILE BUDGET TARGET_LOC
tail -n +2 "$SPEC" | xargs -P "$PAR" -I{} bash -c 'one "$@"' _ {}
