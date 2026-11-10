#!/usr/bin/env bash
# Creates a throwaway git repository that contains FAKE secrets, so scanners have something to find.
# The values are documented examples or obviously invented; none of them is a real credential.
# The secrets are generated at run time on purpose: they never live in the course repository itself.
#
# Usage: seed-demo.sh [target-dir]      (default: ~/heyjob-labs/secrets-demo)
set -euo pipefail

TARGET="${1:-$HOME/heyjob-labs/secrets-demo}"
[ ! -e "$TARGET" ] || { echo "seed-demo.sh: $TARGET already exists; remove it first" >&2; exit 2; }
mkdir -p "$TARGET/app"
cd "$TARGET"
git init -q -b main
git config user.email "student@example.com"
git config user.name "Student"

cat > README.md <<'EOT'
# Secrets demo (fake values only)
EOT
git add README.md && git commit -q -m "Add README"

cat > app/config.py <<'EOT'
import os

# Oops: credentials pasted straight into the source file.
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
DB_PASSWORD = "Sup3rS3cret-demo-password!"
api_key = "k8s-demo-4f9a7c1e2b6d8035a1c4e7f90b2d6a38"
EOT
git add app/config.py && git commit -q -m "Add application config"

cat > app/config.py <<'EOT'
import os

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
api_key = os.environ["API_KEY"]
EOT
git add app/config.py && git commit -q -m "Read credentials from the environment instead"

echo "Created $TARGET with 3 commits."
echo "The current files are clean, but the secrets are still in the history (git log -p)."
