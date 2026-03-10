#!/usr/bin/env bash
# Stamp the current git tag into src/core/_build_version.py before building.
set -euo pipefail
TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown")
cat > src/core/_build_version.py <<EOF
BUILD_VERSION = "$TAG"
EOF
echo "Stamped version: $TAG"
