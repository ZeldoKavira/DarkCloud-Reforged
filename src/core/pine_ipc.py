"""PINE IPC client for PCSX2.
Implements the PINE protocol over TCP (Windows) or Unix sockets (macOS/Linux).
Supports batched commands to reduce round-trips.
"""

import os
import socket
import struct
import sys
import threading

# Opcodes
MSG_READ8 = 0x00
MSG_READ16 = 0x01
MSG_READ32 = 0x02
MSG_READ64 = 0x03
MSG_WRITE8 = 0x04
MSG_WRITE16 = 0x05
MSG_WRITE32 = 0x06
MSG_WRITE64 = 0x07
MSG_VERSION = 0x08
MSG_TITLE = 0x0B
MSG_ID = 0x0C
MSG_STATUS = 0x0F

IPC_OK = 0x00
IPC_FAIL = 0xFF

PINE_PORT = 28011

# Response sizes per opcode (excluding the status byte)
_RESP_SIZES = {
    MSG_READ8: 1, MSG_READ16: 2, MSG_READ32: 4, MSG_READ64: 8,
    MSG_WRITE8: 0, MSG_WRITE16: 0, MSG_WRITE32: 0, MSG_WRITE64: 0,
}


class PineError(Exception):
    pass


class PineIPC:
    def __init__(self, port=PINE_PORT):
        self.port = port
        self.sock = None
        self._lock = threading.Lock()

    @property
    def connected(self):
        return self.sock is not None

    def connect(self):
        """Attempt to connect to PCSX2's PINE socket. Returns True on success."""
        with self._lock:
            if self.sock is not None:
                return True
            try:
                if sys.platform == "win32":
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect(("127.0.0.1", self.port))
                else:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(2)
                    if sys.platform == "darwin":
                        runtime = os.environ.get("TMPDIR", "/tmp")
                    else:
                        runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
                    sock_path = os.path.join(runtime, "pcsx2.sock")
                    s.connect(sock_path)
                # Set recv timeout after connect so reads don't hang forever
                s.settimeout(5)
                self.sock = s
                return True
            except (OSError, socket.error):
                self.sock = None
                return False

    def disconnect(self):
        with self._lock:
            if self.sock:
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None

    def _recv_exact(self, n):
        """Must be called while holding self._lock."""
        s = self.sock
        if not s:
            raise ConnectionError("Not connected")
        data = b""
        while len(data) < n:
            chunk = s.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Socket closed")
            data += chunk
        return data

    def _send_recv(self, payload):
        """Send IPC message, receive and validate reply. Thread-safe."""
        with self._lock:
            s = self.sock
            if not s:
                raise ConnectionError("Not connected")
            msg = struct.pack("<I", len(payload) + 4) + payload
            s.sendall(msg)
            header = self._recv_exact(4)
            total = struct.unpack("<I", header)[0]
            body = self._recv_exact(total - 4)
            if body[0] == IPC_FAIL:
                raise PineError("IPC command failed")
            return body

    # --- Read operations ---

    def read8(self, addr):
        resp = self._send_recv(struct.pack("<BI", MSG_READ8, addr))
        return resp[1]

    def read16(self, addr):
        resp = self._send_recv(struct.pack("<BI", MSG_READ16, addr))
        return struct.unpack("<H", resp[1:3])[0]

    def read32(self, addr):
        resp = self._send_recv(struct.pack("<BI", MSG_READ32, addr))
        return struct.unpack("<I", resp[1:5])[0]

    def read64(self, addr):
        resp = self._send_recv(struct.pack("<BI", MSG_READ64, addr))
        return struct.unpack("<Q", resp[1:9])[0]

    # --- Write operations ---

    def write8(self, addr, val):
        self._send_recv(struct.pack("<BIB", MSG_WRITE8, addr, val & 0xFF))

    def write16(self, addr, val):
        self._send_recv(struct.pack("<BIH", MSG_WRITE16, addr, val & 0xFFFF))

    def write32(self, addr, val):
        self._send_recv(struct.pack("<BII", MSG_WRITE32, addr, val & 0xFFFFFFFF))

    def write64(self, addr, val):
        self._send_recv(struct.pack("<BIQ", MSG_WRITE64, addr, val & 0xFFFFFFFFFFFFFFFF))

    # --- Batch operations ---

    def batch(self, commands):
        """Send multiple commands in one IPC message.

        commands: list of (opcode, addr, [value]) tuples
        Returns list of results (read values or None for writes).
        """
        payload = b""
        for cmd in commands:
            op = cmd[0]
            addr = cmd[1]
            if op == MSG_READ8:
                payload += struct.pack("<BI", op, addr)
            elif op == MSG_READ16:
                payload += struct.pack("<BI", op, addr)
            elif op == MSG_READ32:
                payload += struct.pack("<BI", op, addr)
            elif op == MSG_READ64:
                payload += struct.pack("<BI", op, addr)
            elif op == MSG_WRITE8:
                payload += struct.pack("<BIB", op, addr, cmd[2] & 0xFF)
            elif op == MSG_WRITE16:
                payload += struct.pack("<BIH", op, addr, cmd[2] & 0xFFFF)
            elif op == MSG_WRITE32:
                payload += struct.pack("<BII", op, addr, cmd[2] & 0xFFFFFFFF)
            elif op == MSG_WRITE64:
                payload += struct.pack("<BIQ", op, addr, cmd[2] & 0xFFFFFFFFFFFFFFFF)

        resp = self._send_recv(payload)
        # Parse results
        results = []
        off = 0
        for cmd in commands:
            op = cmd[0]
            status = resp[off]; off += 1
            if status == IPC_FAIL:
                results.append(None)
                continue
            sz = _RESP_SIZES.get(op, 0)
            if sz == 0:
                results.append(None)
            elif sz == 1:
                results.append(resp[off])
            elif sz == 2:
                results.append(struct.unpack("<H", resp[off:off+2])[0])
            elif sz == 4:
                results.append(struct.unpack("<I", resp[off:off+4])[0])
            elif sz == 8:
                results.append(struct.unpack("<Q", resp[off:off+8])[0])
            off += sz
        return results

    # --- Info operations ---

    def status(self):
        """Returns 0=Running, 1=Paused, 2=Shutdown."""
        resp = self._send_recv(struct.pack("<B", MSG_STATUS))
        return struct.unpack("<I", resp[1:5])[0]

    def _read_string_cmd(self, opcode):
        resp = self._send_recv(struct.pack("<B", opcode))
        str_len = struct.unpack("<I", resp[1:5])[0]
        return resp[5:5 + str_len].decode("utf-8", errors="replace")

    def version(self):
        return self._read_string_cmd(MSG_VERSION)

    def game_title(self):
        return self._read_string_cmd(MSG_TITLE)

    def game_id(self):
        return self._read_string_cmd(MSG_ID)
