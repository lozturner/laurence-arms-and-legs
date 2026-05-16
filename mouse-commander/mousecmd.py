"""
MouseCommander — Redragon MMO Mouse Button Mapper
Part of the Laurence Arms & Legs suite.

Stage 1: Listens to all mouse + keyboard events, surfaces unknown/extra buttons.
Stage 2: Maps captured buttons to user-defined actions, applied as system overrides.
Hosts a local admin UI at http://localhost:7477
"""

import sys
import os
import json
import time
import threading
import subprocess
import webbrowser
import queue
import ctypes
from pathlib import Path
from datetime import datetime

# ── Dependency check ──────────────────────────────────────────────────────────
MISSING = []
HAS_INPUT = True
HAS_TRAY = True

try:
    from flask import Flask, jsonify, request, Response, send_from_directory
except ImportError:
    MISSING.append("flask")

try:
    from pynput import mouse, keyboard
    from pynput.keyboard import Key, KeyCode, Controller as KeyController
    from pynput.mouse import Button, Controller as MouseController
    # Validate a display is available by doing a lightweight probe
    import pynput._util
except Exception:
    HAS_INPUT = False

try:
    import pystray
    from pystray import MenuItem as item
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if MISSING:
    print(f"Missing packages: {', '.join(MISSING)}")
    print(f"Run: pip install {' '.join(MISSING)}")
    sys.exit(1)

HEADLESS = not HAS_INPUT
if HEADLESS:
    print("[MouseCommander] No display detected — running in headless mode (web UI only).")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
CONFIG_FILE = BASE_DIR / "mousecmd_config.json"
PORT = 7477

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "mappings": {},        # "button_id": { "label": str, "action_type": str, "action_value": str }
    "learn_mode": True,    # Stage 1: surface all events
    "override_active": False,
    "ui_theme": "dark",
    "first_run": True,
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
                # merge with defaults for any missing keys
                for k, v in DEFAULT_CONFIG.items():
                    cfg.setdefault(k, v)
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

config = load_config()
config_lock = threading.Lock()

# ── Event bus (SSE) ───────────────────────────────────────────────────────────
event_subscribers = []
event_subscribers_lock = threading.Lock()

def broadcast_event(data: dict):
    payload = f"data: {json.dumps(data)}\n\n"
    dead = []
    with event_subscribers_lock:
        for q in event_subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for q in dead:
            event_subscribers.remove(q)

# ── Input capture ─────────────────────────────────────────────────────────────
if HAS_INPUT:
    EXTRA_MOUSE_BUTTONS = {
        Button.x1: "mouse_x1",
        Button.x2: "mouse_x2",
    }
    STANDARD_BUTTONS = {Button.left, Button.middle, Button.right}
else:
    EXTRA_MOUSE_BUTTONS = {}
    STANDARD_BUTTONS = set()

# Known Redragon side-button key mappings (varies by model/profile)
REDRAGON_KEYS = {
    "Key.f13": "F13", "Key.f14": "F14", "Key.f15": "F15",
    "Key.f16": "F16", "Key.f17": "F17", "Key.f18": "F18",
    "Key.f19": "F19", "Key.f20": "F20", "Key.f21": "F21",
    "Key.f22": "F22", "Key.f23": "F23", "Key.f24": "F24",
    "'\\x00'": "Null", "'\\x01'": "SOH", "'\\x02'": "STX",
}

captured_buttons = {}       # button_id -> { count, last_seen, label }
captured_lock = threading.Lock()

def register_button(button_id: str, source: str, raw: str):
    with captured_lock:
        if button_id not in captured_buttons:
            captured_buttons[button_id] = {
                "id": button_id,
                "source": source,
                "raw": raw,
                "count": 0,
                "last_seen": None,
                "label": config.get("mappings", {}).get(button_id, {}).get("label", button_id),
            }
        captured_buttons[button_id]["count"] += 1
        captured_buttons[button_id]["last_seen"] = datetime.now().isoformat()

    broadcast_event({
        "type": "button_press",
        "button_id": button_id,
        "source": source,
        "raw": raw,
        "mapped": button_id in config.get("mappings", {}),
        "ts": datetime.now().isoformat(),
    })

    if config.get("override_active") and button_id in config.get("mappings", {}):
        mapping = config["mappings"][button_id]
        threading.Thread(target=execute_action, args=(mapping,), daemon=True).start()

def execute_action(mapping: dict):
    action_type = mapping.get("action_type", "")
    value = mapping.get("action_value", "")
    try:
        if action_type == "hotkey":
            kb = KeyController()
            keys = parse_hotkey(value)
            for k in keys:
                kb.press(k)
            time.sleep(0.05)
            for k in reversed(keys):
                kb.release(k)
        elif action_type == "type_text":
            kb = KeyController()
            kb.type(value)
        elif action_type == "open_url":
            webbrowser.open(value)
        elif action_type == "run_command":
            subprocess.Popen(value, shell=True)
        elif action_type == "open_file":
            os.startfile(value) if sys.platform == "win32" else subprocess.Popen(["xdg-open", value])
        elif action_type == "media":
            kb = KeyController()
            key_map = {
                "play_pause": Key.media_play_pause,
                "next": Key.media_next,
                "prev": Key.media_previous,
                "volume_up": Key.media_volume_up,
                "volume_down": Key.media_volume_down,
                "mute": Key.media_volume_mute,
            }
            if value in key_map:
                kb.press(key_map[value])
                kb.release(key_map[value])
    except Exception as e:
        broadcast_event({"type": "action_error", "error": str(e), "mapping": mapping})

def parse_hotkey(hotkey_str: str):
    kb = KeyController()
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    keys = []
    key_map = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift, "alt": Key.alt,
        "cmd": Key.cmd, "win": Key.cmd, "super": Key.cmd,
        "enter": Key.enter, "return": Key.enter,
        "space": Key.space, "tab": Key.tab,
        "esc": Key.esc, "escape": Key.esc,
        "backspace": Key.backspace, "delete": Key.delete,
        "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
        "home": Key.home, "end": Key.end, "pgup": Key.page_up, "pgdn": Key.page_down,
    }
    for p in parts:
        if p in key_map:
            keys.append(key_map[p])
        elif p.startswith("f") and p[1:].isdigit():
            keys.append(getattr(Key, p, KeyCode.from_char(p)))
        elif len(p) == 1:
            keys.append(KeyCode.from_char(p))
    return keys

# ── Mouse listener ────────────────────────────────────────────────────────────
def on_mouse_click(x, y, button, pressed):
    if not pressed:
        return
    if button in STANDARD_BUTTONS:
        return
    raw = str(button)
    bid = EXTRA_MOUSE_BUTTONS.get(button, f"mouse_{raw.replace('Button.', '')}")
    register_button(bid, "mouse", raw)

# ── Keyboard listener ─────────────────────────────────────────────────────────
WATCH_KEY_PREFIXES = ("Key.f13", "Key.f14", "Key.f15", "Key.f16",
                      "Key.f17", "Key.f18", "Key.f19", "Key.f20",
                      "Key.f21", "Key.f22", "Key.f23", "Key.f24")

_suppress_next = set()
_suppress_lock = threading.Lock()

def on_key_press(key):
    raw = str(key)

    # F13–F24 always treated as extra mouse button candidates
    if raw.startswith(("Key.f13", "Key.f14", "Key.f15", "Key.f16",
                        "Key.f17", "Key.f18", "Key.f19", "Key.f20",
                        "Key.f21", "Key.f22", "Key.f23", "Key.f24")):
        label = REDRAGON_KEYS.get(raw, raw.replace("Key.", ""))
        bid = f"key_{label.lower()}"
        register_button(bid, "keyboard", raw)
        if config.get("override_active") and bid in config.get("mappings", {}):
            return False  # suppress original key event

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(STATIC_DIR))

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route("/api/config", methods=["GET"])
def api_get_config():
    with config_lock:
        return jsonify(config)

@app.route("/api/config", methods=["POST"])
def api_set_config():
    global config
    data = request.json
    with config_lock:
        config.update(data)
        save_config(config)
    broadcast_event({"type": "config_updated", "config": config})
    return jsonify({"ok": True})

@app.route("/api/buttons", methods=["GET"])
def api_buttons():
    with captured_lock:
        return jsonify(list(captured_buttons.values()))

@app.route("/api/mapping", methods=["POST"])
def api_set_mapping():
    data = request.json
    button_id = data.get("button_id")
    if not button_id:
        return jsonify({"error": "button_id required"}), 400
    with config_lock:
        if "mappings" not in config:
            config["mappings"] = {}
        if data.get("delete"):
            config["mappings"].pop(button_id, None)
        else:
            config["mappings"][button_id] = {
                "label": data.get("label", button_id),
                "action_type": data.get("action_type", ""),
                "action_value": data.get("action_value", ""),
            }
        save_config(config)
    with captured_lock:
        if button_id in captured_buttons:
            captured_buttons[button_id]["label"] = data.get("label", button_id)
    broadcast_event({"type": "mapping_updated", "button_id": button_id})
    return jsonify({"ok": True})

@app.route("/api/test_action", methods=["POST"])
def api_test_action():
    data = request.json
    threading.Thread(target=execute_action, args=(data,), daemon=True).start()
    return jsonify({"ok": True})

@app.route("/api/events")
def api_events():
    q = queue.Queue(maxsize=50)
    with event_subscribers_lock:
        event_subscribers.append(q)

    def generate():
        yield "data: {\"type\": \"connected\"}\n\n"
        while True:
            try:
                msg = q.get(timeout=20)
                yield msg
            except queue.Empty:
                yield ": heartbeat\n\n"
            except GeneratorExit:
                break

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/status")
def api_status():
    return jsonify({
        "running": True,
        "headless": HEADLESS,
        "learn_mode": config.get("learn_mode"),
        "override_active": config.get("override_active"),
        "buttons_seen": len(captured_buttons),
        "mappings_count": len(config.get("mappings", {})),
    })

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Inject a synthetic button press — useful for testing/demo in headless mode."""
    data = request.json or {}
    bid = data.get("button_id", "sim_button")
    source = data.get("source", "simulated")
    register_button(bid, source, f"sim:{bid}")
    return jsonify({"ok": True, "button_id": bid})

# ── Tray icon ─────────────────────────────────────────────────────────────────
def make_tray_icon(active=False):
    if not HAS_PIL:
        return None
    try:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = (80, 200, 120) if active else (100, 120, 200)
        d.ellipse([4, 4, 60, 60], fill=color)
        d.ellipse([22, 22, 42, 42], fill=(255, 255, 255, 200))
        return img
    except Exception:
        return None

tray_icon = None

def open_ui(icon=None, item=None):
    webbrowser.open(f"http://localhost:{PORT}")

def toggle_learn(icon=None, item=None):
    with config_lock:
        config["learn_mode"] = not config.get("learn_mode", True)
        save_config(config)
    broadcast_event({"type": "config_updated", "config": config})

def toggle_override(icon=None, item=None):
    with config_lock:
        config["override_active"] = not config.get("override_active", False)
        save_config(config)
    broadcast_event({"type": "config_updated", "config": config})
    if tray_icon:
        tray_icon.icon = make_tray_icon(config.get("override_active"))

def quit_app(icon=None, item=None):
    if tray_icon:
        tray_icon.stop()
    os._exit(0)

def reset_captures(icon=None, item=None):
    with captured_lock:
        captured_buttons.clear()
    broadcast_event({"type": "reset"})

def build_tray():
    global tray_icon
    if not HAS_TRAY:
        return
    try:
        menu = pystray.Menu(
            item("Open Admin UI", open_ui, default=True),
            pystray.Menu.SEPARATOR,
            item(lambda t: f"{'✓ ' if config.get('learn_mode') else ''}Learn Mode", toggle_learn),
            item(lambda t: f"{'✓ ' if config.get('override_active') else ''}Override Active", toggle_override),
            pystray.Menu.SEPARATOR,
            item("Reset Captures", reset_captures),
            pystray.Menu.SEPARATOR,
            item("Quit", quit_app),
        )
        icon_img = make_tray_icon()
        if icon_img:
            tray_icon = pystray.Icon("MouseCommander", icon_img, "MouseCommander", menu)
            tray_icon.run()
    except Exception as e:
        print(f"[MouseCommander] Tray unavailable: {e}")

# ── Main ───────────────────────────────────────────────────────────────────────
def start_flask():
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False)

def main():
    print(f"[MouseCommander] Starting on http://localhost:{PORT}")
    if HEADLESS:
        print("[MouseCommander] Headless mode: mouse/keyboard listeners and system tray disabled.")
        print("[MouseCommander] On your Windows machine with a display, all features will activate.")

    # Flask in background
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    if not HEADLESS:
        # Mouse listener
        try:
            mouse_listener = mouse.Listener(on_click=on_mouse_click)
            mouse_listener.start()
        except Exception as e:
            print(f"[MouseCommander] Mouse listener failed: {e}")

        # Keyboard listener
        try:
            kb_listener = keyboard.Listener(on_press=on_key_press)
            kb_listener.start()
        except Exception as e:
            print(f"[MouseCommander] Keyboard listener failed: {e}")

    if not HEADLESS:
        # Tray blocks the main thread (required by pystray on most platforms)
        build_tray()
    else:
        # Headless: block on Flask thread
        print(f"[MouseCommander] Web UI ready → http://localhost:{PORT}")
        flask_thread.join()

if __name__ == "__main__":
    main()
