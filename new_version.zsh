#!/usr/bin/env zsh
# -------------------------------------------------------------
# create a new version tag
# Github will trigger an action (see pypi.yml)
#
# 2025-11-28
# -------------------------------------------------------------
set -euo pipefail

CONFIG_FILE=pyproject.toml 

function warn {
  GREEN='\033[0;32m'
  NORMAL='\033[0m'
  echo -e "${GREEN}$1${NORMAL}"
}


# Define helper command for toml-cli
toml_get() {
  uv run toml get --toml-path $CONFIG_FILE "$@"
}

# Fail if repo is dirty
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Repository is dirty. Commit or stash changes before tagging."
  exit 1
fi

# Use the defined command
VERSION=$(toml_get project.version)
TAG="v$VERSION"

warn "Creating git tag $TAG from $CONFIG_FILE"
git tag -a "$TAG" -m "Release version $VERSION"

warn "Pushing..."
git push origin main
git push origin "$TAG"
warn "Done!"

