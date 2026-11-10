#!/usr/bin/env bash
# make-samples.sh [COUNT] [SEED]: generate COUNT (default 5) tiny seeded repos into capstone/work/, one per language, plus repos.csv and the answer keys.
# Deterministic: the same COUNT and SEED give byte-identical repos and identical commit SHAs. work/ is git-ignored (nested repos).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/../work}"
mkdir -p "$WORK" && WORK="$(cd "$WORK" && pwd)"
COUNT="${1:-5}"; SEED="${2:-42}"
[ -e "$WORK/repos" ] && { echo "make-samples.sh: $WORK/repos exists; remove $WORK first to regenerate" >&2; exit 1; }
python3 "$HERE/generate.py" --out "$WORK/repos" --keys-dir "$WORK/answer-keys" --csv "$WORK/repos.csv" --count "$COUNT" --seed "$SEED" --filler "${FILLER:-24}"
echo "next: python3 $HERE/../measure/measure.py --dir $WORK/repos/<name>"
