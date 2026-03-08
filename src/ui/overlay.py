"""Overlay window for displaying text over the game."""
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
import json, os, sys, time

MSG_FILE = sys.argv[1]
POLL_MS = 200
HIDE_AFTER_S = 8

root = tk.Tk()
root.title("dcr_overlay")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.geometry("1x1+0+0")
root.wait_visibility(root)
root.attributes("-alpha", 0.85)

try:
    root.config(bg="black")
    root.wm_attributes("-transparentcolor", "black")
except tk.TclError:
    pass

frame = tk.Frame(root, bg="#111111", bd=2, relief="flat")
frame.pack(fill="both", expand=True, padx=0, pady=0)

text_widget = tk.Text(frame, font=("Arial", 14, "bold"), fg="white", bg="#111111",
                      wrap="word", borderwidth=0, highlightthickness=0,
                      padx=8, pady=6, state="disabled")
text_widget.pack(fill="both", expand=True)

# Color tags
text_widget.tag_configure("W", foreground="white")
text_widget.tag_configure("Y", foreground="#FFD700")
text_widget.tag_configure("G", foreground="#44DD44")
text_widget.tag_configure("R", foreground="#FF4444")
text_widget.tag_configure("B", foreground="#4488FF")
text_widget.tag_configure("O", foreground="#FF8800")

_last_mtime = 0
_show_time = 0
_visible = False

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
            _render(data.get("text", ""), data.get("x", 20), data.get("y", 20))
            _show_time = time.time()
            _visible = True
        elif _visible and time.time() - _show_time > HIDE_AFTER_S:
            root.withdraw()
            _visible = False
    except Exception:
        pass
    root.after(POLL_MS, _check_msg)

def _render(text, x, y):
    text_widget.config(state="normal")
    text_widget.delete("1.0", "end")
    # Parse color codes: ^R, ^G, ^W, ^Y, ^B, ^O
    tag = "W"
    i = 0
    while i < len(text):
        if text[i] == "^" and i + 1 < len(text) and text[i+1] in "RGWYBO":
            tag = text[i+1]
            i += 2
            continue
        # Find next color code or end
        j = i + 1
        while j < len(text):
            if text[j] == "^" and j + 1 < len(text) and text[j+1] in "RGWYBO":
                break
            j += 1
        text_widget.insert("end", text[i:j], tag)
        i = j
    text_widget.config(state="disabled")
    # Resize to fit
    lines = text.count("\n") + 1
    max_len = max((len(l) for l in text.split("\n")), default=10)
    w = min(max(max_len * 12, 250), 800)
    h = lines * 26 + 40
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.deiconify()

root.withdraw()
root.after(POLL_MS, _check_msg)
root.mainloop()
'''


def start_overlay():
    """Launch overlay as a separate process."""
    global _proc
    if _proc and _proc.poll() is None:
        return
    msg_path = _get_msg_path()
    # Clear stale message file
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


def show_text(text, x=20, y=20):
    """Send text to the overlay. Supports ^R ^G ^W ^Y ^B ^O color codes."""
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
    log.info("Overlay show_text: writing to %s", path)
    try:
        with open(path, "w") as f:
            json.dump({"text": text, "x": x, "y": y}, f)
    except Exception as e:
        log.warning("Overlay write failed: %s", e)
