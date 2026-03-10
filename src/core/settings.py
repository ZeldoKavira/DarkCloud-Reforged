"""Mod settings persisted to dark-cloud-reforged.json next to the mod."""

import json
import os
import logging

log = logging.getLogger(__name__)

_DEFAULTS = {
    "overlay_fishing": True,
    "overlay_attachments": True,
    "overlay_georama": True,
}

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "dark-cloud-reforged.json")

_settings = None


def _load():
    global _settings
    if _settings is not None:
        return
    _settings = dict(_DEFAULTS)
    if os.path.exists(_PATH):
        try:
            with open(_PATH) as f:
                _settings.update(json.load(f))
            log.info("Settings loaded from %s", _PATH)
        except Exception as e:
            log.warning("Failed to load settings: %s", e)


def get(key):
    _load()
    return _settings.get(key, _DEFAULTS.get(key))


def set(key, value):
    _load()
    _settings[key] = value
    try:
        with open(_PATH, 'w') as f:
            json.dump(_settings, f, indent=2)
    except Exception as e:
        log.warning("Failed to save settings: %s", e)


def all_settings():
    _load()
    return dict(_settings)
