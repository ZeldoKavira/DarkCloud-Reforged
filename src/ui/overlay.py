"""Overlay window that tracks the PCSX2 game window cross-platform."""
import subprocess
import platform
import time
import threading
import queue
import tkinter as tk
import tkinter.font
import logging

log = logging.getLogger(__name__)

_os = platform.system()
_win = None
_canvas = None
_root = None
_visible = False
_show_time = 0
_game_rect = None
_queue = queue.Queue()

TRACK_MS = 250
POLL_MS = 50
HIDE_AFTER_S = 8
FONT = ("Arial", 14, "bold")
FONT_SMALL = ("Arial", 10, "italic")
OUTLINE = 2
COLORS = {"W": "white", "Y": "#FFD700", "G": "#44DD44", "R": "#FF4444",
          "B": "#4488FF", "O": "#FF8800"}
BG = "#111111"


def _find_pcsx2_window():
    try:
        if _os == "Darwin":
            script = ('tell application "System Events"\n'
                      'set pList to every process whose name contains "PCSX2"\n'
                      'if (count of pList) > 0 then\n'
                      'set wList to every window of (item 1 of pList)\n'
                      'repeat with w in wList\n'
                      'set t to name of w\n'
                      'if t does not contain "Reforged" then\n'
                      'set {x, y} to position of w\n'
                      'set {sw, sh} to size of w\n'
                      'return (x as text) & "," & (y as text) & "," & (sw as text) & "," & (sh as text)\n'
                      'end if\nend repeat\nend if\nend tell')
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
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            result = [None]
            def cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(hwnd, buf, 256)
                    if "Dark Cloud" in buf.value and "Reforged" not in buf.value:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        result[0] = (rect.left, rect.top,
                                     rect.right - rect.left, rect.bottom - rect.top)
                        return False
                return True
            user32.EnumWindows(WNDENUMPROC(cb), 0)
            return result[0]
    except Exception:
        pass
    return None


def _outlined_text(cx, cy, txt, fill, font=FONT):
    for dx in range(-OUTLINE, OUTLINE + 1):
        for dy in range(-OUTLINE, OUTLINE + 1):
            if dx or dy:
                _canvas.create_text(cx + dx, cy + dy, text=txt, font=font,
                                    fill="black", anchor="nw")
    _canvas.create_text(cx, cy, text=txt, font=font, fill=fill, anchor="nw")


def _render(text, ox=10, oy=10):
    global _visible, _show_time
    if not text or not text.strip():
        if _visible:
            _win.withdraw()
            _visible = False
        return
    _canvas.delete("all")
    lines = []
    cur_line = []
    color = "W"
    small = False
    i = 0
    while i < len(text):
        if text[i] == "^" and i + 1 < len(text) and text[i + 1] in COLORS:
            color = text[i + 1]; i += 2; continue
        if text[i] == "^" and i + 1 < len(text) and text[i + 1] == "s":
            small = True; i += 2; continue
        if text[i] == "\n":
            lines.append(cur_line); cur_line = []; i += 1; continue
        j = i + 1
        while j < len(text) and text[j] != "\n" and not (
                text[j] == "^" and j + 1 < len(text) and (text[j + 1] in COLORS or text[j + 1] == "s")):
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
    ow = min(max(int(max_w) + pad * 2, 250), 800)
    oh = cy + pad
    _canvas.configure(width=ow, height=oh)
    rect = _game_rect
    if rect:
        gx, gy = rect[0], rect[1]
        _win.geometry(f"{ow}x{oh}+{gx + ox}+{gy + oy}")
    else:
        _win.geometry(f"{ow}x{oh}+{ox}+{oy}")
    _win.deiconify()
    _visible = True
    _show_time = time.time()


def _tracker_thread():
    global _game_rect
    while True:
        _game_rect = _find_pcsx2_window()
        time.sleep(TRACK_MS / 1000.0)


def _main_poll():
    """Runs on main Tk thread — drains the queue and handles auto-hide/reposition."""
    global _visible
    if _win is None or _root is None:
        if _root is not None:
            _root.after(POLL_MS, _main_poll)
        return
    # Drain queue, only use latest message
    msg = None
    try:
        while True:
            msg = _queue.get_nowait()
    except queue.Empty:
        pass
    if msg is not None:
        if msg[0] == "show":
            _render(msg[1], msg[2], msg[3])
        elif msg[0] == "hide":
            if _visible:
                _win.withdraw()
                _visible = False
    # Auto-hide
    if _visible and time.time() - _show_time > HIDE_AFTER_S:
        _win.withdraw()
        _visible = False
    # Reposition
    if _visible and _game_rect:
        try:
            gx, gy = _game_rect[0], _game_rect[1]
            _win.geometry(f"+{gx + 10}+{gy + 10}")
        except Exception:
            pass
    _root.after(POLL_MS, _main_poll)


def start_overlay(root=None):
    global _root, _win, _canvas
    if _win is not None:
        return
    if root is None:
        root = tk._default_root
    if root is None:
        log.warning("No Tk root available for overlay")
        return
    _root = root
    _win = tk.Toplevel(_root)
    _win.title("dcr_overlay")
    _win.overrideredirect(True)
    _win.attributes("-topmost", True)
    _win.geometry("1x1+0+0")
    try:
        _win.attributes("-alpha", 0.85)
    except Exception:
        pass
    _win.config(bg=BG)
    _canvas = tk.Canvas(_win, bg=BG, highlightthickness=0, bd=0)
    _canvas.pack(fill="both", expand=True)
    _win.withdraw()
    _root.after(POLL_MS, _main_poll)
    t = threading.Thread(target=_tracker_thread, daemon=True)
    t.start()
    log.info("Overlay started (in-process Toplevel)")


def stop_overlay():
    global _win, _canvas, _root, _visible
    if _win is not None:
        try:
            _win.destroy()
        except Exception:
            pass
    _win = None
    _canvas = None
    _visible = False


def show_text(text, x=10, y=10):
    """Thread-safe. Queues text for the overlay."""
    _queue.put(("show", text, x, y))


def hide_text():
    """Thread-safe. Queues a hide command."""
    _queue.put(("hide",))
