#!/usr/bin/env bash
# Sync the web build into the Pavlovia GitLab repo and push.
#
# Layout (per Pavlovia's current docs and the WP1 port): index.html and its assets sit at
# the REPO ROOT on branch `master`. Pavlovia git-pulls the repo to
# https://run.pavlovia.org/<user>/<project>/ when the study is PILOTING/RUNNING and
# creates its own `data/` folder there — never delete it. Never add a folder named `lib/`:
# Pavlovia symlinks its own lib into the run location and the deploy breaks.
#
#   ./tools/deploy_pavlovia.sh [pavlovia-repo-path] ["commit message"]
#
# Source of truth is experiment/web/ in THIS repo. Never edit the Pavlovia copy directly.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/experiment/web"
DEST="${1:-$HOME/Desktop/PhD/Experiments/wp3-pavlovia}"
MSG="${2:-Update WP3 web build}"

[ -d "$DEST/.git" ] || { echo "ERROR: $DEST is not a git repository (see experiment/web/PAVLOVIA.md)"; exit 1; }

for f in index.html engine.js motion_pool.bin motion_pool.json; do
  [ -f "$SRC/$f" ] || { echo "ERROR: missing $SRC/$f"; exit 1; }
  cp "$SRC/$f" "$DEST/$f"
  printf '  %-18s %s\n' "$f" "$(du -h "$SRC/$f" | cut -f1)"
done

cd "$DEST"
[ "$(git branch --show-current)" = "master" ] || { echo "ERROR: Pavlovia expects branch 'master' (current: $(git branch --show-current))"; exit 1; }
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "no changes to deploy"; exit 0
fi
git add index.html engine.js motion_pool.bin motion_pool.json
git commit -q -m "$MSG"
git push -q origin master
echo "pushed to $(git remote get-url origin)"
echo "then: pavlovia.org → Dashboard → the experiment → hard-reload the run URL (Cmd+Shift+R)"
