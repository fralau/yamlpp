#!/usr/bin/env zsh
set -euo pipefail

# Define helper command for toml-cli
toml_get() {
  uv run toml get --toml-path pyproject.toml "$@"
}

# Fail if repo is dirty
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Repository is dirty. Commit or stash changes before tagging."
  exit 1
fi

# Use the defined command
VERSION=$(toml_get project.version)
TAG="v$VERSION"

echo "Creating git tag $TAG from pyproject.toml"

git tag -a "$TAG" -m "Release version $VERSION"
git push origin "$TAG"

