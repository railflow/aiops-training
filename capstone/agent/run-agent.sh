#!/usr/bin/env bash
# run-agent.sh: the entrypoint of the agent Job. Clone, run ONE headless agent session, run quick local checks, push a branch, print a RESULT line.
# It never merges and never touches main: a trusted evaluate job and a human decide what happens next.
#
# Environment (all set by the Job template): REPO (org/name), FORGEJO_URL, FORGEJO_TOKEN, ANTHROPIC_API_KEY, AGENT_RUN_ID, TASK (coverage|fix-issue),
# TARGET_COVERAGE, FOCUS, ISSUE_NUMBER, MAX_BUDGET_USD, MODEL (optional), OPEN_PR (1/0), PROMPT_VERSION.
set -uo pipefail
export WORK="${WORK_DIR:-/work}"
: "${REPO:?}" "${FORGEJO_URL:?}" "${FORGEJO_TOKEN:?}" "${AGENT_RUN_ID:?}"
TASK="${TASK:-coverage}"; MAX_BUDGET_USD="${MAX_BUDGET_USD:-3}"; PROMPT_VERSION="${PROMPT_VERSION:-v1}"
export TARGET_COVERAGE="${TARGET_COVERAGE:-60}" FOCUS="${FOCUS:-the modules with the lowest coverage}" ISSUE_NUMBER="${ISSUE_NUMBER:-}" PROMPT_VERSION AGENT_RUN_ID
export HOME="${HOME:-/tmp/home}"; mkdir -p "$HOME" "$WORK/repo"
PROMPTS="${PROMPTS_DIR:-${AGENT_DIR:-/opt/agent}/prompts}"
START=$(date +%s)
# The token travels in the environment, never in the remote URL, argv or .git/config.
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader GIT_CONFIG_VALUE_0="Authorization: token $FORGEJO_TOKEN" GIT_TERMINAL_PROMPT=0
GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-capstone-agent}"; GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-agent@capstone.local}"
export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

result() {   # result OUTCOME [PR_URL]
  local outcome="$1" pr="${2:-}"
  python3 - "$outcome" "$pr" "$START" <<'PY'
import json, os, subprocess, sys, time
outcome, pr, start = sys.argv[1], sys.argv[2], int(sys.argv[3])
cj = {}
try:
    cj = json.load(open(os.environ["WORK"] + "/claude.json"))
except Exception:
    pass
def tool(v):
    try: return subprocess.run(v, capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
    except Exception: return "unknown"
usage = cj.get("usage") or {}
commits = 0
try: commits = int(subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"], cwd=os.environ["WORK"] + "/repo", capture_output=True, text=True).stdout.strip() or 0)
except Exception: pass
print("RESULT " + json.dumps({
    "agent_run_id": os.environ["AGENT_RUN_ID"], "repo": os.environ["REPO"], "task": os.environ.get("TASK", "coverage"), "outcome": outcome,
    "branch": os.environ.get("BRANCH", ""), "pr_url": pr, "commits": commits, "duration_s": int(time.time()) - start,
    # Field names of Claude Code's JSON output are from its docs as I remember them: verify against `claude -p --output-format json` for your version.
    "cost_usd": cj.get("total_cost_usd"), "turns": cj.get("num_turns"), "is_error": cj.get("is_error"),
    "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
    "model": os.environ.get("MODEL", "default"), "prompt_version": os.environ.get("PROMPT_VERSION", ""),
    "tool_versions": {"claude": tool(["claude", "--version"]), "git": tool(["git", "--version"])}}))
PY
}

cd "$WORK" || exit 1
git clone --quiet "${FORGEJO_URL%/}/$REPO.git" repo || { echo "clone failed"; result "clone-failed"; exit 0; }
cd repo || exit 1
git fetch --quiet origin main
BRANCH="ai/$([ "$TASK" = coverage ] && echo coverage || echo "fix-$ISSUE_NUMBER")-$AGENT_RUN_ID"; export BRANCH
git checkout --quiet -b "$BRANCH"

if [ "$TASK" = fix-issue ]; then
  curl -sf -H "Authorization: token $FORGEJO_TOKEN" "${FORGEJO_URL%/}/api/v1/repos/$REPO/issues/$ISSUE_NUMBER" | python3 -c 'import json,sys; i=json.load(sys.stdin); print("# "+i["title"]+"\n\n"+i["body"])' > ISSUE.md \
    || { result "issue-unreadable"; exit 0; }
  echo "ISSUE.md" >> .git/info/exclude
fi

PROMPT="$(cat "$PROMPTS/system-rules.md"; echo; echo ---; echo; python3 - "$PROMPTS/$( [ "$TASK" = coverage ] && echo coverage || echo fix-issue ).md" <<'PY'
import os, string, sys
print(string.Template(open(sys.argv[1]).read()).safe_substitute(os.environ))
PY
)"

# Flags verified against `claude --help` of Claude Code 2.1.278. There is no --max-turns in that list: the cost cap and the Job's activeDeadlineSeconds are the brakes.
# --permission-mode acceptEdits lets it edit files; Bash is allowed because it must run tests: the Job's NetworkPolicy and read-only root are what contain it.
T=(); command -v timeout >/dev/null 2>&1 && T=(timeout "${AGENT_TIMEOUT_S:-1500}")   # macOS has no timeout; the Job image does
${T[@]+"${T[@]}"} claude -p "$PROMPT" --output-format json --permission-mode acceptEdits \
  --allowedTools "Read" "Edit" "Write" "Bash" --disallowedTools "WebFetch" "WebSearch" \
  --max-budget-usd "$MAX_BUDGET_USD" --no-session-persistence ${MODEL:+--model "$MODEL"} > "$WORK/claude.json" 2> "$WORK/claude.err"
rc=$?
[ $rc -eq 0 ] || echo "claude exited $rc: $(tail -c 300 "$WORK/claude.err")" >&2

git add -A
git diff --cached --quiet || git commit --quiet -m "Agent changes (run $AGENT_RUN_ID)"
if [ -z "$(git rev-list origin/main..HEAD)" ]; then result "no-changes"; exit 0; fi

NOSRC=""; [ "$TASK" = coverage ] && NOSRC="--no-src-changes"
python3 "${AGENT_DIR:-/opt/agent}"/integrity_check.py --base origin/main $NOSRC || { echo "integrity check failed: not pushing"; result "integrity-failed"; exit 0; }
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-banner --redact --log-opts "origin/main..HEAD" >/dev/null 2>&1 || { echo "gitleaks found a secret in the agent's commits: not pushing"; result "secret-in-diff"; exit 0; }
fi
git push --quiet -u origin "$BRANCH" || { result "push-failed"; exit 0; }
PR=""
if [ "${OPEN_PR:-1}" = 1 ]; then
  PR="$(curl -sf -X POST -H "Authorization: token $FORGEJO_TOKEN" -H 'Content-Type: application/json' "${FORGEJO_URL%/}/api/v1/repos/$REPO/pulls" \
      -d "$(python3 -c 'import json,os; print(json.dumps({"head": os.environ["BRANCH"], "base": "main", "title": "AI: "+os.environ.get("TASK","coverage")+" ("+os.environ["AGENT_RUN_ID"]+")", "body": "Automated change. Run `"+os.environ["AGENT_RUN_ID"]+"`. A human must review and merge; CI and the evaluate job report separately."}))')" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("html_url",""))' 2>/dev/null)"
fi
result "pushed" "$PR"
