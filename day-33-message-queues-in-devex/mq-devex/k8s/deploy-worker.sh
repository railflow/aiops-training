#!/usr/bin/env bash
# Publish the code as a ConfigMap and (re)deploy one worker.   ./deploy-worker.sh uitest lab2-pipeline/uitest.py [args...]
# Render only (no cluster needed):                             RENDER_ONLY=1 ./deploy-worker.sh uitest lab2-pipeline/uitest.py
# Extra env for the pod:                                       EXTRA="UITEST_SECONDS=20 ACK_WAIT=15" ./deploy-worker.sh uitest lab2-pipeline/uitest.py
# State (the processed-ids table) lives in an emptyDir, so a pod restart forgets it. Fine for a lab; use a PVC or a database for real.
# Needs: bash, python3, and (unless RENDER_ONLY=1) kubectl. On Windows run it from Git Bash or WSL.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
NAME="${1:?worker name}"
SRC="${2:?path under mq-devex, e.g. lab2-pipeline/uitest.py}"
shift 2 || true
SCRIPT="$(basename "$SRC")"
ARGS="$*"
EXTRA_ENV=""
for kv in ${EXTRA:-}; do
  EXTRA_ENV+="            - {name: ${kv%%=*}, value: \"${kv#*=}\"}"$'\n'
done
PIP="${PIP:-nats-py==2.16.0 pyyaml}"
export NAME SCRIPT ARGS EXTRA_ENV PIP
render() {
  python3 -c '
import os, string, sys
print(string.Template(open(sys.argv[1]).read()).substitute(os.environ))
' "$HERE/worker.yaml.tpl"
}
if [ "${RENDER_ONLY:-0}" = 1 ]; then render; exit 0; fi
files=()
for f in "$ROOT"/lib/devbus.py "$ROOT"/lab*/*.py "$ROOT"/lab*/*.yaml; do
  [ -f "$f" ] && files+=("--from-file=$(basename "$f")=$f")
done
kubectl apply -f "$HERE/00-namespace.yaml"
kubectl -n mq-devex create configmap mq-devex-code "${files[@]}" --dry-run=client -o yaml | kubectl apply -f -
render | kubectl apply -f -
kubectl -n mq-devex rollout restart deploy/"$NAME" >/dev/null
echo "deployed $NAME; logs: kubectl -n mq-devex logs -f deploy/$NAME"
