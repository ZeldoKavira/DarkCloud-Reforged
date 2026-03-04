"""Memory abstraction layer over PINE IPC.
Mirrors the C# Memory class — provides typed read/write with auto-reconnect.
"""

import struct
import logging
import time
from core.pine_ipc import PineIPC, PineError, MSG_READ8, MSG_READ32, MSG_WRITE8, MSG_WRITE32

log = logging.getLogger(__name__)

_RECONNECT_COOLDOWN = 1.0  # seconds between reconnect attempts


class Memory:
    def __init__(self, ipc: PineIPC):
        self.ipc = ipc
        self._last_reconnect = 0

    @property
    def connected(self):
        return self.ipc.connected

    def connect(self):
        return self.ipc.connect()

    def disconnect(self):
        self.ipc.disconnect()

    def _ensure_connected(self):
        """Reconnect if disconnected, with cooldown to avoid spam."""
        if self.ipc.connected:
            return True
        now = time.monotonic()
        if now - self._last_reconnect < _RECONNECT_COOLDOWN:
            return False
        self._last_reconnect = now
        if self.ipc.connect():
            log.info("PINE reconnected")
            return True
        return False

    def _safe(self, fn, *args, default=None):
        """Call fn with auto-reconnect on failure."""
        if not self._ensure_connected():
            return default
        try:
            return fn(*args)
        except (ConnectionError, OSError, PineError, AttributeError) as e:
            log.debug("PINE op failed: %s", e)
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

    # --- Bulk operations ---

    def read_bytes(self, addr, length):
        """Read a block of bytes. Uses batched 32-bit reads + tail byte reads."""
        if not self._ensure_connected():
            return b'\x00' * length

        # Read in chunks of 32-bit words via batch, max ~500 per batch
        result = bytearray()
        offset = 0
        BATCH = 500
        try:
            while offset < length:
                cmds = []
                chunk_end = min(offset + BATCH * 4, length)
                pos = offset
                while pos + 4 <= chunk_end:
                    cmds.append((MSG_READ32, addr + pos))
                    pos += 4
                # Tail bytes
                while pos < chunk_end:
                    cmds.append((MSG_READ8, addr + pos))
                    pos += 1

                vals = self.ipc.batch(cmds)
                for i, cmd in enumerate(cmds):
                    v = vals[i] if vals[i] is not None else 0
                    if cmd[0] == MSG_READ32:
                        result.extend(struct.pack("<I", v))
                    else:
                        result.append(v & 0xFF)
                offset = chunk_end
        except (ConnectionError, OSError, PineError) as e:
            log.warning("Bulk read failed at offset %d: %s", offset, e)
            self.ipc.disconnect()
            result.extend(b'\x00' * (length - len(result)))

        return bytes(result[:length])

    def write_bytes(self, addr, data):
        """Write a block of bytes. Uses batched 32-bit writes + tail byte writes."""
        if not self._ensure_connected():
            return

        offset = 0
        BATCH = 500
        try:
            while offset < len(data):
                cmds = []
                chunk_end = min(offset + BATCH * 4, len(data))
                pos = offset
                while pos + 4 <= chunk_end:
                    val = struct.unpack("<I", data[pos:pos+4])[0]
                    cmds.append((MSG_WRITE32, addr + pos, val))
                    pos += 4
                while pos < chunk_end:
                    cmds.append((MSG_WRITE8, addr + pos, data[pos]))
                    pos += 1

                self.ipc.batch(cmds)
                offset = chunk_end
        except (ConnectionError, OSError, PineError) as e:
            log.warning("Bulk write failed at offset %d: %s", offset, e)
            self.ipc.disconnect()

    # --- Info ---

    def status(self) -> int:
        return self._safe(self.ipc.status, default=2)

    def game_title(self) -> str:
        return self._safe(self.ipc.game_title, default="")

    def game_id(self) -> str:
        return self._safe(self.ipc.game_id, default="")
