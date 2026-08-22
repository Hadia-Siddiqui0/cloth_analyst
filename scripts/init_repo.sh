#!/usr/bin/env bash
# Day 4: initialize the repo and push to GitHub.
# Run this once, from the project root (clothing-business-analytics/).
#
# Branch strategy:
#   main               -- always deployable, protected, no direct pushes
#   feature/<name>      -- one branch per roadmap day/task, e.g. feature/auth-signup
# Merge via PR into main even working solo -- it's a free changelog of
# what each day actually shipped, and costs nothing extra.

set -e

if [ -d .git ]; then
  echo "Already a git repo -- skipping init."
else
  git init
  git branch -M main
fi

git add .
git commit -m "Day 4-5: FastAPI scaffold, auth, multi-tenant models, ingestion engine" || echo "Nothing to commit."

echo ""
echo "Next steps:"
echo "1. Create an empty repo on GitHub named 'clothing-business-analytics' (no README/gitignore -- you already have one)."
echo "2. git remote add origin git@github.com:<your-username>/clothing-business-analytics.git"
echo "3. git push -u origin main"
echo ""
echo "For each new roadmap day going forward:"
echo "   git checkout -b feature/<short-task-name>"
echo "   ...do the work, commit..."
echo "   git push -u origin feature/<short-task-name>"
echo "   open a PR into main, merge it, delete the branch"