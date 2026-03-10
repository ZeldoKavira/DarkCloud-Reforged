"""Changelog entries keyed by version tag."""

CHANGELOG = {
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


def get_changes_since(old_version):
    """Return changelog text for all versions newer than old_version."""
    if not old_version or old_version == "unknown":
        return None
    lines = []
    for ver in VERSIONS:
        if ver <= old_version:
            break
        lines.append(f"^Y{ver}")
        for entry in CHANGELOG[ver]:
            lines.append(f"^W- {entry}")
    return "\n".join(lines) if lines else None
