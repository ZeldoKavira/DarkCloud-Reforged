"""Changelog entries keyed by version tag."""

CHANGELOG = {
    "v0.2.3": [
        "* Add Version changelog system",
        "* Add Version Overlay",
        "* Add Map and MC cheats",
    ],
    "v0.2.1": [
        "Added overlay settings (Fishing, Attachments, Georama)",
        "Added Start with Map / Magical Crystal options",
        "Added Disable Character Doors option",
        "Fixed shop corruption bug (dialogue ID write in Toan path)",
        "Fixed FP Exchange attachment stat detection",
        "Overlay now runs in-process (no Python dependency)",
    ],
    "v0.2.0": [
        "Attachment stat overlay for customize menu and shops",
        "Fishing overlay with pond status and progressive attract",
        "Georama request display (L3 in dungeon)",
        "House ID display in Location panel",
    ],
}

# Ordered newest first
VERSIONS = sorted(CHANGELOG.keys(), reverse=True)


def get_changes_since(old_version, include_current=None):
    """Return changelog text for all versions newer than old_version.
    If include_current is set, always include that version's entry.
    If old_version is None/empty, shows the latest 3 versions."""
    lines = []
    count = 0
    # Always include current version first if it has an entry
    if include_current and include_current in CHANGELOG:
        lines.append(f"^Y{include_current}")
        for entry in CHANGELOG[include_current]:
            lines.append(f"^W- {entry}")
        count += 1
    for ver in VERSIONS:
        if count >= 3:
            break
        if ver == include_current:
            continue
        if old_version and ver <= old_version:
            break
        lines.append(f"^Y{ver}")
        for entry in CHANGELOG[ver]:
            lines.append(f"^W- {entry}")
        count += 1
    if not lines:
        return None
    lines.append("^s^WFull changelog at github.com/ZeldoKavira/DarkCloud-Reforged")
    return "\n".join(lines)
