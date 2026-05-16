"""
paperclip.py — Triple-right-click context bookmark.

Tri-Click Mode tool. You triple-right-click anywhere. It hooks on the way in
and grabs URL + active window + active browser tab + timestamp via multiple
verification methods. A small paperclip floats on the desktop tracking the
session and nudges you back to the captured context on a configurable timer.

Windows 10/11. Python 3.10+.
    pip install pynput pystray pillow pywin32 psutil pyperclip mss
"""

from __future__ import annotations

import json
import os
import sys
import time
import threading
import tkinter as tk
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from pynput import mouse
from PIL import Image, ImageDraw, ImageTk
try:
    import pystray  # type: ignore
except Exception:
    pystray = None
try:
    import pyperclip  # type: ignore
except Exception:
    pyperclip = None
import mss

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    win32gui = None
    win32process = None
    psutil = None


APP_NAME = "paperclip"
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE = DATA_DIR / "sessions.json"
SHOTS_DIR = DATA_DIR / "shots"
SHOTS_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "triple_click_window_ms": 600,
    "nudge_min_minutes": 3,
    "nudge_max_minutes": 7,
    "auto_close_minutes": 45,
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}
        except Exception:
            pass
    SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2))
    return dict(DEFAULT_SETTINGS)


@dataclass
class Capture:
    timestamp: str
    window_title: str = ""
    process_name: str = ""
    url: str = ""
    browser_tab: str = ""
    clipboard: str = ""
    screenshot_path: str = ""
    verified_by: list = field(default_factory=list)


def grab_active_window() -> tuple[str, str]:
    if not win32gui:
        return ("", "")
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd) or ""
    proc = ""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid).name()
    except Exception:
        pass
    return title, proc


def grab_browser_url(window_title: str, process_name: str) -> tuple[str, str]:
    """Best-effort URL + tab grab. Browsers expose the tab title in window title.
    Real URL extraction uses UI Automation (optional)."""
    tab = ""
    url = ""
    name = (process_name or "").lower()
    if any(b in name for b in ("chrome", "msedge", "firefox", "brave", "opera")):
        tab = window_title.rsplit(" - ", 1)[0] if " - " in window_title else window_title
        try:
            from uiautomation import ControlFromHandle  # type: ignore
            hwnd = win32gui.GetForegroundWindow()
            ctrl = ControlFromHandle(hwnd)
            edit = ctrl.EditControl(searchDepth=20)
            if edit.Exists(0.3):
                url = edit.GetValuePattern().Value
        except Exception:
            pass
    return url, tab


def grab_screenshot() -> str:
    fname = SHOTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    try:
        with mss.mss() as sct:
            sct.shot(mon=-1, output=str(fname))
        return str(fname)
    except Exception:
        return ""


def grab_clipboard() -> str:
    if not pyperclip:
        return ""
    try:
        return (pyperclip.paste() or "")[:500]
    except Exception:
        return ""


def capture_context() -> Capture:
    c = Capture(timestamp=datetime.now().isoformat())
    title, proc = grab_active_window()
    c.window_title, c.process_name = title, proc
    if title or proc:
        c.verified_by.append("win32")
    url, tab = grab_browser_url(title, proc)
    c.url, c.browser_tab = url, tab
    if url:
        c.verified_by.append("uiautomation")
    if tab:
        c.verified_by.append("window-title")
    c.screenshot_path = grab_screenshot()
    if c.screenshot_path:
        c.verified_by.append("screenshot")
    c.clipboard = grab_clipboard()
    if c.clipboard:
        c.verified_by.append("clipboard")
    return c


def append_session(c: Capture) -> None:
    data = []
    if SESSIONS_FILE.exists():
        try:
            data = json.loads(SESSIONS_FILE.read_text())
        except Exception:
            data = []
    data.append(asdict(c))
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))


# ---------- Floating paperclip UI ----------

class FloatingClip:
    """Small always-on-top paperclip that shows captured sessions and nudges."""

    def __init__(self, root: tk.Tk, settings: dict):
        self.root = root
        self.settings = settings
        self.captures: list[Capture] = []
        self.queue: Queue = Queue()
        self._build()
        self.root.after(200, self._drain)
        self._schedule_nudge()
        self._schedule_autoclose()

    def _build(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.geometry("+40+40")
        self.root.configure(bg="#1e1e1e")

        self.icon_img = _paperclip_image(48)
        self.tk_img = ImageTk.PhotoImage(self.icon_img)
        self.btn = tk.Label(self.root, image=self.tk_img, bg="#1e1e1e", cursor="hand2")
        self.btn.pack(padx=4, pady=4)
        self.badge = tk.Label(self.root, text="0", fg="white", bg="#c0392b",
                              font=("Segoe UI", 8, "bold"))
        self.badge.place(x=36, y=2)

        self.btn.bind("<Button-1>", lambda e: self._toggle_panel())
        self.btn.bind("<B1-Motion>", self._drag)
        self.btn.bind("<ButtonPress-1>", self._drag_start)

        self.panel = None

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag(self, e):
        x = self.root.winfo_pointerx() - self._dx
        y = self.root.winfo_pointery() - self._dy
        self.root.geometry(f"+{x}+{y}")

    def add(self, c: Capture):
        self.queue.put(c)

    def _drain(self):
        try:
            while True:
                c = self.queue.get_nowait()
                self.captures.append(c)
        except Empty:
            pass
        self.badge.config(text=str(len(self.captures)))
        self.root.after(200, self._drain)

    def _toggle_panel(self):
        if self.panel and self.panel.winfo_exists():
            self.panel.destroy()
            self.panel = None
            return
        self.panel = tk.Toplevel(self.root)
        self.panel.overrideredirect(True)
        self.panel.attributes("-topmost", True)
        self.panel.configure(bg="#252525")
        x = self.root.winfo_x() + 60
        y = self.root.winfo_y()
        self.panel.geometry(f"380x320+{x}+{y}")
        tk.Label(self.panel, text="Paperclip — captured contexts",
                 fg="#eee", bg="#252525", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        frame = tk.Frame(self.panel, bg="#252525")
        frame.pack(fill="both", expand=True, padx=8, pady=4)
        if not self.captures:
            tk.Label(frame, text="(nothing pinned yet — triple-right-click anywhere)",
                     fg="#888", bg="#252525").pack(anchor="w")
        for i, c in enumerate(reversed(self.captures[-15:])):
            label = c.browser_tab or c.window_title or c.process_name or "(unknown)"
            ts = c.timestamp.split("T")[1][:8]
            row = tk.Label(frame, text=f"• {ts}  {label[:48]}",
                           fg="#ddd", bg="#252525", anchor="w", justify="left")
            row.pack(fill="x", anchor="w")

    def nudge(self):
        if not self.captures:
            return
        last = self.captures[-1]
        label = last.browser_tab or last.window_title or "your last context"
        note = tk.Toplevel(self.root)
        note.overrideredirect(True)
        note.attributes("-topmost", True)
        note.configure(bg="#2c3e50")
        x = self.root.winfo_x() + 60
        y = self.root.winfo_y() + 60
        note.geometry(f"320x80+{x}+{y}")
        tk.Label(note, text="Hey — remember you were working on:",
                 fg="#bdc3c7", bg="#2c3e50", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(8, 0))
        tk.Label(note, text=label[:60], fg="white", bg="#2c3e50",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8)
        note.after(8000, note.destroy)

    def _schedule_nudge(self):
        import random
        lo = self.settings["nudge_min_minutes"] * 60_000
        hi = self.settings["nudge_max_minutes"] * 60_000
        delay = random.randint(lo, hi)
        self.root.after(delay, self._do_nudge)

    def _do_nudge(self):
        self.nudge()
        self._schedule_nudge()

    def _schedule_autoclose(self):
        self.root.after(self.settings["auto_close_minutes"] * 60_000, self._autoclose)

    def _autoclose(self):
        self.captures.clear()
        self.badge.config(text="0")
        self._schedule_autoclose()


def _paperclip_image(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 6
    d.rounded_rectangle((pad, pad, size - pad, size - pad // 2),
                        radius=size // 4, outline="#ecf0f1", width=3)
    d.rounded_rectangle((pad + 6, pad + 6, size - pad - 6, size - pad // 2 - 4),
                        radius=size // 5, outline="#ecf0f1", width=3)
    return img


# ---------- Triple-right-click listener ----------

class TripleRightClick:
    def __init__(self, window_ms: int, on_triple):
        self.window = window_ms / 1000.0
        self.on_triple = on_triple
        self.times: list[float] = []

    def __call__(self, x, y, button, pressed):
        if button != mouse.Button.right or not pressed:
            return
        now = time.time()
        self.times = [t for t in self.times if now - t <= self.window]
        self.times.append(now)
        if len(self.times) >= 3:
            self.times.clear()
            threading.Thread(target=self.on_triple, daemon=True).start()


# ---------- System tray ----------

def build_tray(on_quit, on_show_folder):
    if not pystray:
        return None
    img = _paperclip_image(64)
    menu = pystray.Menu(
        pystray.MenuItem("Open data folder", lambda *_: on_show_folder()),
        pystray.MenuItem("Quit", lambda icon, _: (icon.stop(), on_quit())),
    )
    return pystray.Icon(APP_NAME, img, "Paperclip", menu)


# ---------- Main ----------

def main():
    settings = load_settings()
    root = tk.Tk()
    clip = FloatingClip(root, settings)

    def on_triple():
        c = capture_context()
        append_session(c)
        clip.add(c)

    listener = mouse.Listener(on_click=TripleRightClick(settings["triple_click_window_ms"], on_triple))
    listener.daemon = True
    listener.start()

    def show_folder():
        try:
            os.startfile(str(DATA_DIR))  # type: ignore[attr-defined]
        except Exception:
            pass

    tray = build_tray(on_quit=root.quit, on_show_folder=show_folder)
    if tray is not None:
        threading.Thread(target=tray.run, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()
