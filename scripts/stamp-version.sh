#!/usr/bin/env bash
# Stamp version into src/core/_build_version.py.
# Usage: stamp-version.sh [tag]  (auto-detects from git if omitted)
set -euo pipefail
if [[ -n "${1:-}" ]]; then
    TAG="$1"
else
    TAG=$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1)
    [[ -z "$TAG" ]] && TAG="unknown"
fi
cat > src/core/_build_version.py <<EOF
BUILD_VERSION = "$TAG"
EOF
echo "Stamped version: $TAG"
