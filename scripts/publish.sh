#!/bin/bash
# =============================================================================
# publish.sh — put the previewed site online (https://frarent.github.io).
# Shows what will change, asks for confirmation, commits, merges into master
# if you are on another branch, and pushes. GitHub Pages rebuilds in ~1 min.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

branch=$(git rev-parse --abbrev-ref HEAD)

# 1. Show pending changes
echo "== Branch: $branch"
git status --short
git diff --stat HEAD | tail -1 || true
[ -f UPDATE_REPORT.md ] && { echo; cat UPDATE_REPORT.md; }

# 2. Confirm
echo
read -r -p "Publish these changes to https://frarent.github.io ? [y/N] " ok
[[ "$ok" =~ ^[Yy]$ ]] || { echo "Nothing published."; exit 0; }

# 3. Commit local changes (generated data, CV, edits)
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "Site update $(date +%F)"
fi

# 4. Bring the branch into master if needed
if [ "$branch" != "master" ]; then
  git checkout -q master
  git pull -q --ff-only origin master
  git merge --no-edit "$branch"
fi

# 5. Sync with GitHub (picks up edits made on github.com) and push
git pull -q --rebase origin master
git push origin master
echo "Published. Live in about a minute: https://frarent.github.io"
