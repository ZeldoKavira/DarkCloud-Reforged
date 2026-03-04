"""Ruby element texture swap. Ported from Dayuppy.CheckElements() + Resources.cs.

Loads 5 pre-baked texture blobs and writes them to PCSX2 memory when
Ruby changes her weapon element, so her model colour matches.
"""

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# PyInstaller extracts bundled data to sys._MEIPASS; fall back to source tree
_BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
_TEX_DIR = _BASE / "resources" / "ruby_tex"
_ELEMENT_FILES = {0: "Fire", 1: "Ice", 2: "Thunder", 3: "Wind", 4: "Holy"}
_POINTER_ADDR = 0x202A2DDC
_OFFSET = 0x20000000

_textures = {}  # element_id → bytes


def load_textures():
    """Load Ruby texture blobs from disk. Call once at startup."""
    for eid, name in _ELEMENT_FILES.items():
        p = _TEX_DIR / name
        if p.exists():
            _textures[eid] = p.read_bytes()
            log.debug("Loaded Ruby %s texture (%d bytes)", name, len(_textures[eid]))
        else:
            log.warning("Missing Ruby texture: %s", p)


def check_elements(mem, element_id):
    """Write Ruby's element texture to PCSX2 memory.

    Reads the texture pointer from 0x202A2DDC, adds 0x20000000,
    and writes the full texture blob there.
    """
    if element_id not in _textures:
        return
    ptr = mem.read_int(_POINTER_ADDR) + _OFFSET
    mem.write_bytes(ptr, _textures[element_id])
    log.debug("Wrote Ruby %s texture to 0x%08X", _ELEMENT_FILES[element_id], ptr)
