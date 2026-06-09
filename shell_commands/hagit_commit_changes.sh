#!/bin/bash
set -euo pipefail

REPO_DIR="/config"
BRANCH="main"

cd "$REPO_DIR"

if [ -n "$(git status --porcelain)" ]; then
  git checkout "$BRANCH"
  git add -A
  git commit -m "Sync repository state"
  git push
else
  echo "No changes to commit."
fi

exit 0
