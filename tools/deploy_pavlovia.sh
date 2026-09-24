#!/usr/bin/env bash
# Sync the web build into a Pavlovia GitLab repo and push.
#
# Pavlovia serves the contents of an `html/` folder at the repo root: it git-pulls that
# folder to https://run.pavlovia.org/<user>/<study>/ when the study is ACTIVATED.
# Pavlovia also creates its own `data/` folder in the repo — never delete it.
#
#   ./tools/deploy_pavlovia.sh ~/path/to/pavlovia-repo "optional commit message"
#
# The source of truth stays experiment/web/ in THIS repo. Never edit the Pavlovia copy.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/experiment/web"
DEST="${1:?usage: deploy_pavlovia.sh <pavlovia-repo-path> [message]}"
MSG="${2:-Update WP3 web build}"

[ -d "$DEST/.git" ] || { echo "ERROR: $DEST is not a git repository"; exit 1; }

mkdir -p "$DEST/html"
for f in index.html engine.js motion_pool.bin motion_pool.json; do
  [ -f "$SRC/$f" ] || { echo "ERROR: missing $SRC/$f"; exit 1; }
  cp "$SRC/$f" "$DEST/html/$f"
  printf '  %-20s %s\n' "$f" "$(du -h "$SRC/$f" | cut -f1)"
done

cd "$DEST"
if git diff --quiet && git diff --cached --quiet; then
  echo "no changes to deploy"; exit 0
fi
git add html
git commit -q -m "$MSG"
git push -q origin HEAD
echo "pushed to $(git remote get-url origin)"
echo "activate / reload the study at https://pavlovia.org/dashboard?tab=1"
