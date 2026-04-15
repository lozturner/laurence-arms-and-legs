# 🦾 Laurence: Arms and Legs

> *"An extension of himself in every which way."*

This is the story of a suite of tools built for one person — **Laurence** — a brilliant mind navigating the world through whatever combination of eyes, hands, mouth, and brain was available to him on any given day.

---

## 🧠 The Four Modes

The suite was built around a simple truth: **Laurence's ability varied.** Not his intelligence. Never that. But the physical and cognitive channels he could use to express it — those shifted. So we built a tool for every combination.

---

### 🎙️ Mic Mode — *"I have my mouth"*

**When:** Hands-free. Body doing other things. Mouth is the only open channel.

Laurence had his voice. That was it. These tools let him operate his whole computer by speaking — no hands, no keyboard, no clicks needed.

- 🎤 `voicesort.py` — Sorts, organises, and routes files by spoken command
- ✍️ `scribe.py` — Voice-to-structured-text with smart formatting
- 🕐 `aitimer.py` — Spoken timers, reminders, countdown sequences

> *"He was physically limited to just his mouth. We made his mouth enough."*

---

### ✍️ Writing Mode — *"I have my hands and my eyes"*

**When:** One part of the brain was online. He had hands. He had eyes. The words existed, they just needed scaffolding to get out.

These tools reduce friction between thought and output. They catch, structure, and scaffold ideas the moment they arrive.

- 🧩 `mermaidbot.py` — Describe any idea in plain English → instant flowchart diagram
- 📝 `niggly.py` — IFTTT-style focus rules; keeps distractions minimised automatically
- 📋 `windowbranch.py` — Full radial tree of every open window and browser tab
- 🎯 `tiles.py` — Every window as a draggable tile; named zones on a full-screen canvas

> *"He had hands. He had eyes. We kept going that way."*

---

### 🖱️ Tri-Click Mode — *"I have eyes, mouth, hands — but not the words"*

**When:** He could see. He could point. He could click. But the language pathways were down. The words weren't coming.

These tools work with gesture, proximity, and prediction — the minimum possible input to navigate the maximum possible space.

- 🔥 `hot_corner.py` — Move mouse to any corner → trigger any action. Zero clicks needed.
- 🌊 `floatbar.py` — Always-on-top bar: ← back to last window, → forward to next
- 🔍 `windowbot.py` — Window search and switcher with near-zero input
- 🎪 `hub.py` — Master launchpad with one visual per tool

> *"He had his eyes. He had his mouth. He had his hands. We didn't have his brain that day — so we built a brain."*

---

## 🗂️ The Full Suite

| Tool | Repo | What It Does |
|------|------|-------------|
| 🧩 MermaidBot | [→](https://github.com/lozturner/lawrence-mermaidbot) | Natural language → flowchart diagram |
| 🌊 FloatBar | [→](https://github.com/lozturner/lawrence-floatbar) | Floating always-on-top window nav bar |
| 📌 Niggly | [→](https://github.com/lozturner/lawrence-niggly) | Auto-minimise distracting windows |
| 🏁 Window Tiles | [→](https://github.com/lozturner/lawrence-window-tiles) | Sidebar + canvas of all open windows |
| 🌳 Window Branch | [→](https://github.com/lozturner/lawrence-window-branch) | Radial tree of all open windows + tabs |
| 🔥 Hot Corners | [→](https://github.com/lozturner/lawrence-hot-corners) | Mouse corner triggers any action |
| 🧹 SelfClean | [→](https://github.com/lozturner/lawrence-selfclean) | Single-instance enforcer (shared util) |
| 📦 Move In (full) | [→](https://github.com/lozturner/lawrence-move-in) | All scripts in one place |

---

## 🛠️ Technical Architecture

Every tool in the suite follows the same rules:

```
✓ Python 3.10+  ✓ Windows 10/11  ✓ No cloud dependencies
✓ System tray icon  ✓ Single-instance (via selfclean.py)
✓ Borderless or minimal chrome  ✓ Always-on-top where needed
✓ Kill-on-relaunch self-management
```

**Shared stack:** `tkinter` · `pystray` · `Pillow` · `pywin32` · `psutil`

**AI integration** (MermaidBot): Claude Code CLI bridge — uses your Max subscription, no separate API key needed.

---

## 💻 Running the Suite

```bash
# Install dependencies
pip install psutil pystray pillow pywin32 keyboard

# Launch everything
pythonw launch_all.pyw
```

Or drop a shortcut to `launch_all.pyw` in your Windows Startup folder.

---

## 📖 The Story

Lawrence didn't want accommodations. He wanted **tools** — things that felt like extensions of himself rather than workarounds for what he'd lost.

So we built them.

Some days he had everything. Some days he had almost nothing. The tools met him wherever he was, and made sure something was always possible.

This suite exists because brilliance doesn't disappear when the body changes. It just needs a different door.

---

## 🤖 Built With

These tools were built in collaboration with **Claude** (Anthropic) via Claude Code — an AI pair-programmer that wrote, debugged, and iterated on every script in this repo.

The human provided the vision, the lived experience, and the feedback.
The AI provided the speed, the code, and the patience to iterate until it worked exactly right.

---

*For Randy Cannon — and everyone else who's ever had more going on inside than the outside could show.*

*Built with love. Loz + Claude, 2024–2026.*

---

**→ Start a new session with Claude Code:** `claude` in your terminal, or open Claude Code and load this project.
