#!/bin/bash
set -euo pipefail

# Configuration
git config --global init.defaultBranch main
git config --global user.name "HAGit"
git config --global user.email "hagit@homeassistant.local"

REPO_DIR="/config"
REMOTE_REPO="git@github.com:mdjdev/homeassistant-config.git"
SSH_KEY="$REPO_DIR/.ssh/id_rsa_github"
BRANCH="main"

cd "$REPO_DIR"

# Init repo if needed
if [ ! -d .git ]; then
  git init
fi

# Ensure/normalize remote
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_REPO"
else
  git remote add origin "$REMOTE_REPO"
fi

# Use dedicated SSH key in this repo; disable signing prompts
git config core.sshCommand "ssh -i $SSH_KEY -F /dev/null"
git config commit.gpgsign false

# Ensure target branch exists locally
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
fi

# Commit all local changes if present (initial or subsequent)
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "Init repository state"
fi

# Detect if remote branch exists (remote may be empty)
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  # Remote has the branch: rebase local commits on top, preferring local in conflicts
  git pull --rebase -X theirs origin "$BRANCH"
fi

# One push to set upstream (creates remote branch if needed)
git push --set-upstream origin "$BRANCH"

exit 0
