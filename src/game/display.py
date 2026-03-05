"""Dungeon message display system. Ported from Dayuppy.DisplayMessage().

Encodes ASCII text into Dark Cloud's custom character format and writes
it to game memory for on-screen display.
"""

import logging
import threading
import time
from game import addresses as addr

log = logging.getLogger(__name__)

# ASCII → Dark Cloud character mapping
# normalCharTable[i] maps to dcCharTable[i]
_NORMAL = (
    list(range(0x41, 0x5B)) +  # A-Z
    list(range(0x61, 0x7B)) +  # a-z
    list(range(0x30, 0x3A)) +  # 0-9
    [0x27, 0x3D, 0x22, 0x21, 0x3F, 0x23, 0x26, 0x2B, 0x2D, 0x2A,
     0x28, 0x29, 0x40, 0x7C, 0x5E,  # ' = " ! ? # & + - * ( ) @ | ^
     0x3C, 0x3E, 0x7B, 0x7D, 0x5B, 0x5D,  # < > { } [ ]
     0x2E, 0x24, 0x0A, 0x20]  # . $ \n SPC
)

_DC = (
    list(range(0x21, 0x3B)) +  # A-Z
    list(range(0x3B, 0x55)) +  # a-z
    list(range(0x6F, 0x79)) +  # 0-9
    [0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E,
     0x61, 0x62, 0x63, 0x64, 0xFF,  # ' = " ! ? # & + - * ( ) @ | ^
     0x65, 0x66, 0x67, 0x68, 0x69, 0x6A,  # < > { } [ ]
     0x6D, 0x6E, 0x00, 0x02]  # . $ \n SPC
)

# Build lookup: ASCII byte → DC byte
_CHAR_MAP = {}
for n, d in zip(_NORMAL, _DC):
    _CHAR_MAP[n] = d

# Color code map: ^R=Red, ^W=White, ^Y=Yellow, ^B=Blue, ^G=Green, ^O=Orange
_COLOR_MAP = {
    ord('W'): 0x01,  # White
    ord('Y'): 0x02,  # Yellow
    ord('B'): 0x03,  # Blue
    ord('G'): 0x04,  # Green
    ord('O'): 0x06,  # Orange
    ord('R'): 0xFF,  # Red
}

# Message addresses
MSG_10 = 0x20998BB8
MSG_LAST_ENEMY = 0x20999EE8
MSG_DISPLAY = addr.DUN_MESSAGE if hasattr(addr, 'DUN_MESSAGE') else 0x21EA76B4
MSG_DURATION = addr.DUN_MESSAGE_DURATION if hasattr(addr, 'DUN_MESSAGE_DURATION') else 0x21EA7694
MSG_ITEM = 0x21CFCCEC


def encode_message(text):
    """Encode ASCII text to Dark Cloud byte pairs.

    Returns list of bytes (2 bytes per character).
    Special: \\n → [0x00, 0xFF], space → [0x02, 0xFF]
    Color: ^R → [0xFF, 0xFC], ^W → [0x01, 0xFC], etc.
    Normal: [dc_char, 0xFD]
    """
    raw = text.encode('mac_roman', errors='replace')
    out = []
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0x5E and i + 1 < len(raw):  # ^ color code
            color_byte = _COLOR_MAP.get(raw[i + 1])
            if color_byte is not None:
                i += 1  # skip the letter after ^
                out.extend([color_byte, 0xFC])
                i += 1
                continue
        if b == 0x0A:  # newline
            out.extend([0x00, 0xFF])
        elif b == 0x20:  # space
            out.extend([0x02, 0xFF])
        elif b in _CHAR_MAP:
            out.extend([_CHAR_MAP[b], 0xFD])
        else:
            out.extend([0x02, 0xFF])  # unknown → space
        i += 1
    return out


def display_message(mem, text, height=4, width=40, display_time=8000, is_clear_msg=False):
    """Write and display a message on the dungeon HUD.

    Args:
        mem: Memory instance
        text: Message string (supports \\n and ^R/^W/^B/^Y/^G/^O color codes)
        height: Number of lines
        width: Characters per line
        display_time: Duration in milliseconds
        is_clear_msg: True for floor-clear message (uses different address)
    """
    t = threading.Thread(
        target=_display_process,
        args=(mem, text, height, width, display_time, is_clear_msg),
        daemon=True)
    t.start()


def _display_process(mem, text, height, width, display_time, is_clear_msg):
    """Background thread for message display."""
    # Wait for any current message to finish
    _wait_for_available(mem)

    # Convert ms to frames (~60fps, 16.7ms per frame)
    frames = round(display_time / 16.7)

    # Encode
    encoded = encode_message(text)

    # Choose target address
    msg_addr = MSG_LAST_ENEMY if is_clear_msg else MSG_10

    # Clear existing message
    for i in range(len(text) * 2):
        try:
            mem.write_byte(msg_addr + i, 0xFD)
        except Exception:
            break

    # Write encoded message
    for i, b in enumerate(encoded):
        try:
            mem.write_byte(msg_addr + i, b)
        except Exception:
            break

    # Terminate
    try:
        end = msg_addr + len(encoded)
        mem.write_byte(end, 0x01)
        mem.write_byte(end + 1, 0xFF)
    except Exception:
        pass

    # Trigger display
    try:
        mem.write_int(MSG_DISPLAY, 0xFFFFFFFF)  # Clear
        time.sleep(0.05)
        msg_id = 3319 if is_clear_msg else 10
        mem.write_int(MSG_DISPLAY, msg_id)
        mem.write_int(MSG_DURATION, frames)
    except Exception:
        pass

    # For floor clear: restore HornHead string after brief delay
    if is_clear_msg:
        time.sleep(0.3)
        horn = [40,253,73,253,76,253,72,253,40,253,63,253,59,253,62,253,1,255]
        for i, b in enumerate(horn):
            try:
                mem.write_byte(MSG_LAST_ENEMY + i, b)
            except Exception:
                break


def _wait_for_available(mem, timeout=0.5):
    """Brief wait for message system to be ready."""
    elapsed = 0
    while elapsed < timeout:
        try:
            cur = mem.read_int(MSG_DISPLAY)
            if cur == 0xFFFFFFFF or cur == 171:
                return
        except Exception:
            return
        time.sleep(0.05)
        elapsed += 0.05
