"""Overlay window that tracks the PCSX2 game window cross-platform."""
import subprocess
import sys
import json
import tempfile
import os
import logging

log = logging.getLogger(__name__)

_proc = None
_msg_file = None


def _get_msg_path():
    global _msg_file
    if _msg_file is None:
        _msg_file = os.path.join(tempfile.gettempdir(), "dcr_overlay.json")
    return _msg_file


_OVERLAY_SCRIPT = r'''
import tkinter as tk
import tkinter.font
import json, os, sys, time, subprocess, platform

MSG_FILE = sys.argv[1]
POLL_MS = 200
TRACK_MS = 100
HIDE_AFTER_S = 8
FONT = ("Arial", 14, "bold")
FONT_SMALL = ("Arial", 10, "italic")
OUTLINE = 2
COLORS = {"W":"white","Y":"#FFD700","G":"#44DD44","R":"#FF4444","B":"#4488FF","O":"#FF8800"}
BG = "#111111"
ANCHOR_X = 10  # default offset from game window left
ANCHOR_Y = 10  # default offset from game window top

_os = platform.system()

def _find_pcsx2_window():
    """Return (x, y, w, h) of the PCSX2 game render window, or None."""
    try:
        if _os == "Darwin":
            script = 'tell application "System Events"\n'
            script += 'set pList to every process whose name contains "PCSX2"\n'
            script += 'if (count of pList) > 0 then\n'
            script += 'set wList to every window of (item 1 of pList)\n'
            script += 'repeat with w in wList\n'
            script += 'set t to name of w\n'
            script += 'if t does not contain "Reforged" then\n'
            script += 'set {x, y} to position of w\n'
            script += 'set {sw, sh} to size of w\n'
            script += 'return (x as text) & "," & (y as text) & "," & (sw as text) & "," & (sh as text)\n'
            script += 'end if\n'
            script += 'end repeat\n'
            script += 'end if\n'
            script += 'end tell'
            r = subprocess.run(["osascript", "-e", script],
                               capture_output=True, text=True, timeout=1)
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(",")
                if len(parts) == 4:
                    return tuple(int(p) for p in parts)
        elif _os == "Linux":
            r = subprocess.run(["xdotool", "search", "--name", "Dark Cloud"],
                               capture_output=True, text=True, timeout=1)
            if r.returncode == 0 and r.stdout.strip():
                for wid in r.stdout.strip().splitlines():
                    r2 = subprocess.run(["xdotool", "getwindowname", wid],
                                        capture_output=True, text=True, timeout=1)
                    if r2.returncode == 0 and "Reforged" in r2.stdout:
                        continue
                    r3 = subprocess.run(["xdotool", "getwindowgeometry", "--shell", wid],
                                        capture_output=True, text=True, timeout=1)
                    if r3.returncode == 0:
                        vals = {}
                        for line in r3.stdout.strip().splitlines():
                            if "=" in line:
                                k, v = line.split("=", 1)
                                vals[k] = int(v)
                        if "X" in vals and "Y" in vals:
                            return (vals["X"], vals["Y"],
                                    vals.get("WIDTH", 800), vals.get("HEIGHT", 600))
        elif _os == "Windows":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowTextW = user32.GetWindowTextW
            GetWindowRect = user32.GetWindowRect
            IsWindowVisible = user32.IsWindowVisible
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            result = [None]
            def cb(hwnd, _):
                if IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(256)
                    GetWindowTextW(hwnd, buf, 256)
                    if "Dark Cloud" in buf.value and "Reforged" not in buf.value:
                        rect = wintypes.RECT()
                        GetWindowRect(hwnd, ctypes.byref(rect))
                        result[0] = (rect.left, rect.top,
                                     rect.right - rect.left, rect.bottom - rect.top)
                        return False
                return True
            EnumWindows(WNDENUMPROC(cb), 0)
            return result[0]
    except Exception:
        pass
    return None

root = tk.Tk()
root.title("dcr_overlay")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.geometry("1x1+0+0")
root.wait_visibility(root)
root.attributes("-alpha", 0.85)
root.config(bg=BG)

if _os == "Darwin":
    # Transparent background on macOS
    try:
        root.attributes("-transparent", True)
        root.config(bg="systemTransparent")
    except Exception:
        pass

canvas = tk.Canvas(root, bg=BG, highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)

_last_mtime = 0
_show_time = 0
_visible = False
_game_rect = None  # (x, y, w, h)
_overlay_w = 1
_overlay_h = 1
_anchor_x = ANCHOR_X
_anchor_y = ANCHOR_Y

def _reposition():
    """Move overlay to anchor position relative to game window."""
    global _game_rect
    rect = _find_pcsx2_window()
    if rect:
        _game_rect = rect
    if _game_rect and _visible:
        gx, gy, gw, gh = _game_rect
        root.geometry(f"{_overlay_w}x{_overlay_h}+{gx + _anchor_x}+{gy + _anchor_y}")
    root.after(TRACK_MS, _reposition)

def _check_msg():
    global _last_mtime, _show_time, _visible
    try:
        if not os.path.exists(MSG_FILE):
            if _visible and time.time() - _show_time > HIDE_AFTER_S:
                root.withdraw()
                _visible = False
            root.after(POLL_MS, _check_msg)
            return
        mt = os.path.getmtime(MSG_FILE)
        if mt != _last_mtime:
            _last_mtime = mt
            with open(MSG_FILE, "r") as f:
                data = json.load(f)
            if data.get("hide"):
                root.withdraw()
                _visible = False
            else:
                _render(data.get("text", ""), data.get("ox", ANCHOR_X), data.get("oy", ANCHOR_Y))
                _show_time = time.time()
                _visible = True
        elif _visible and time.time() - _show_time > HIDE_AFTER_S:
            root.withdraw()
            _visible = False
    except Exception:
        pass
    root.after(POLL_MS, _check_msg)

def _outlined_text(cx, cy, txt, fill, font=FONT):
    for dx in range(-OUTLINE, OUTLINE+1):
        for dy in range(-OUTLINE, OUTLINE+1):
            if dx or dy:
                canvas.create_text(cx+dx, cy+dy, text=txt, font=font, fill="black", anchor="nw")
    canvas.create_text(cx, cy, text=txt, font=font, fill=fill, anchor="nw")

def _render(text, ox=ANCHOR_X, oy=ANCHOR_Y):
    global _overlay_w, _overlay_h, _anchor_x, _anchor_y
    _anchor_x = ox
    _anchor_y = oy
    canvas.delete("all")
    lines = []
    cur_line = []
    color = "W"
    small = False
    i = 0
    while i < len(text):
        if text[i] == "^" and i+1 < len(text) and text[i+1] in COLORS:
            color = text[i+1]; i += 2; continue
        if text[i] == "^" and i+1 < len(text) and text[i+1] == "s":
            small = True; i += 2; continue
        if text[i] == "\n":
            lines.append(cur_line); cur_line = []; i += 1; continue
        j = i+1
        while j < len(text) and text[j] != "\n" and not (text[j] == "^" and j+1 < len(text) and (text[j+1] in COLORS or text[j+1] == "s")):
            j += 1
        cur_line.append((text[i:j], color, small)); i = j
    lines.append(cur_line)
    pad = 8
    cy = pad
    max_w = 0
    for segs in lines:
        cx = pad
        line_h = 24
        for txt, c, sm in segs:
            f = FONT_SMALL if sm else FONT
            _outlined_text(cx, cy, txt, COLORS[c], f)
            cx += tk.font.Font(font=f).measure(txt)
            if sm:
                line_h = 18
        max_w = max(max_w, cx)
        cy += line_h
    _overlay_w = min(max(int(max_w) + pad*2, 250), 800)
    _overlay_h = cy + pad
    # Position relative to game window
    if _game_rect:
        gx, gy, gw, gh = _game_rect
        root.geometry(f"{_overlay_w}x{_overlay_h}+{gx + _anchor_x}+{gy + _anchor_y}")
    else:
        root.geometry(f"{_overlay_w}x{_overlay_h}+{_anchor_x}+{_anchor_y}")
    root.deiconify()

root.withdraw()
root.after(POLL_MS, _check_msg)
root.after(TRACK_MS, _reposition)
root.mainloop()
'''


def start_overlay():
    """Launch overlay as a separate process."""
    global _proc
    if _proc and _proc.poll() is None:
        return
    msg_path = _get_msg_path()
    if os.path.exists(msg_path):
        try:
            os.remove(msg_path)
        except OSError:
            pass
    try:
        _proc = subprocess.Popen(
            [sys.executable, "-c", _OVERLAY_SCRIPT, msg_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        log.info("Overlay started (pid %d), msg_file=%s", _proc.pid, msg_path)
    except Exception as e:
        log.warning("Failed to start overlay: %s", e)


def stop_overlay():
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        _proc = None
    path = _get_msg_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def show_text(text, x=10, y=10):
    """Send text to the overlay. Supports ^R ^G ^W ^Y ^B ^O color codes.
    x/y are offsets relative to the game window's top-left corner."""
    global _proc
    if _proc and _proc.poll() is not None:
        err = ""
        try:
            err = _proc.stderr.read().decode(errors="replace")
        except Exception:
            pass
        log.warning("Overlay process died (rc=%s): %s", _proc.returncode, err[:500])
        _proc = None
        start_overlay()
    path = _get_msg_path()
    try:
        with open(path, "w") as f:
            json.dump({"text": text, "ox": x, "oy": y}, f)
    except Exception as e:
        log.warning("Overlay write failed: %s", e)


def hide_text():
    """Immediately hide the overlay."""
    path = _get_msg_path()
    try:
        with open(path, "w") as f:
            json.dump({"text": "", "hide": True}, f)
    except Exception:
        pass
