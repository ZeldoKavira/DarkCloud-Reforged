#!/usr/bin/env bash
# Generate changelog entry from git commits since last tag.
# Usage: ./scripts/gen-changelog.sh v0.3.0
#   Appends new entry to src/core/changelog.py
set -euo pipefail

NEW_TAG="${1:?Usage: gen-changelog.sh <new-tag>}"
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
CL_FILE="src/core/changelog.py"

if [[ -z "$LAST_TAG" ]]; then
    COMMITS=$(git log --oneline --no-merges --pretty=format:"%s")
else
    COMMITS=$(git log --oneline --no-merges --pretty=format:"%s" "${LAST_TAG}..HEAD")
fi

if [[ -z "$COMMITS" ]]; then
    echo "No commits found since $LAST_TAG"
    exit 1
fi

echo "Generating changelog for $NEW_TAG (since $LAST_TAG):"
echo ""

# Build the Python dict entry
ENTRY="    \"${NEW_TAG}\": ["
while IFS= read -r msg; do
    # Skip fixup/wip/merge commits
    [[ "$msg" =~ ^(fixup|squash|wip|Merge) ]] && continue
    # Escape quotes
    msg="${msg//\"/\\\"}"
    ENTRY+=$'\n'"        \"${msg}\","
    echo "  - $msg"
done <<< "$COMMITS"
ENTRY+=$'\n'"    ],"

# Insert after CHANGELOG = { line
python3 -c "
import re
with open('$CL_FILE') as f:
    content = f.read()
entry = '''$ENTRY'''
# Insert after 'CHANGELOG = {' line
content = content.replace('CHANGELOG = {', 'CHANGELOG = {\n' + entry, 1)
with open('$CL_FILE', 'w') as f:
    f.write(content)
"

echo ""
echo "Updated $CL_FILE — review and edit entries before committing."
