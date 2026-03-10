#!/usr/bin/env bash
# Release script: generate changelog, stamp version, commit, tag, push.
# Usage: ./scripts/release.sh [v0.3.0]  (auto-increments minor if omitted)
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -n "${1:-}" ]]; then
    NEW_TAG="$1"
else
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    # Parse vMAJOR.MINOR.PATCH and increment minor
    IFS='.' read -r major minor patch <<< "${LAST_TAG#v}"
    NEW_TAG="v${major}.${minor}.$((patch + 1))"
    echo "Auto-calculated version: $NEW_TAG (previous: $LAST_TAG)"
fi

echo "=== Releasing $NEW_TAG ==="
echo ""

# 1. Generate changelog
echo "Generating changelog..."
bash "$SCRIPTS_DIR/gen-changelog.sh" "$NEW_TAG"
echo ""

# 2. Let user edit
read -rp "Edit changelog now? [Y/n] " EDIT </dev/tty
if [[ ! "$EDIT" =~ ^[Nn]$ ]]; then
    ${EDITOR:-nano} src/core/changelog.py
fi

# Show final changelog entry
echo ""
echo "=== Final changelog for $NEW_TAG ==="
python3 -c "
import sys; sys.path.insert(0, 'src')
from core.changelog import CHANGELOG
entry = CHANGELOG.get('$NEW_TAG', [])
for e in entry:
    print('  -', e)
"
echo ""

read -rp "Continue with release? [y/N] " CONFIRM </dev/tty
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# 3. Stamp version
echo "Stamping version..."
bash "$SCRIPTS_DIR/stamp-version.sh"

# 4. Commit
echo "Committing..."
git add src/core/changelog.py src/core/_build_version.py
git commit -m "Release $NEW_TAG"

# 5. Tag
echo "Tagging $NEW_TAG..."
git tag "$NEW_TAG"

# 6. Push
echo "Pushing..."
git push && git push --tags

echo ""
echo "=== $NEW_TAG released! ==="
