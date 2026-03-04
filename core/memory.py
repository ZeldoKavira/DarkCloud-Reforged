"""Memory abstraction layer over PINE IPC.
Mirrors the C# Memory class — provides typed read/write with auto-reconnect.
"""

import struct
import logging
from core.pine_ipc import PineIPC, PineError

log = logging.getLogger(__name__)


class Memory:
    def __init__(self, ipc: PineIPC):
        self.ipc = ipc

    @property
    def connected(self):
        return self.ipc.connected

    def connect(self):
        return self.ipc.connect()

    def disconnect(self):
        self.ipc.disconnect()

    def _safe(self, fn, *args, default=None):
        """Call fn with auto-reconnect. Returns default on failure."""
        try:
            return fn(*args)
        except (OSError, ConnectionError, PineError) as e:
            log.debug("Memory op failed: %s", e)
            self.ipc.disconnect()
            return default

    # --- Reads ---

    def read_byte(self, addr) -> int:
        return self._safe(self.ipc.read8, addr, default=0)

    def read_short(self, addr) -> int:
        return self._safe(self.ipc.read16, addr, default=0)

    def read_int(self, addr) -> int:
        return self._safe(self.ipc.read32, addr, default=0)

    def read_float(self, addr) -> float:
        raw = self._safe(self.ipc.read32, addr, default=0)
        return struct.unpack("<f", struct.pack("<I", raw))[0]

    # --- Writes ---

    def write_byte(self, addr, val):
        return self._safe(self.ipc.write8, addr, val)

    def write_short(self, addr, val):
        return self._safe(self.ipc.write16, addr, val)

    def write_int(self, addr, val):
        return self._safe(self.ipc.write32, addr, val)

    def write_float(self, addr, val):
        raw = struct.unpack("<I", struct.pack("<f", val))[0]
        return self._safe(self.ipc.write32, addr, raw)

    # --- Info ---

    def status(self) -> int:
        return self._safe(self.ipc.status, default=2)

    def game_title(self) -> str:
        return self._safe(self.ipc.game_title, default="")

    def game_id(self) -> str:
        return self._safe(self.ipc.game_id, default="")
