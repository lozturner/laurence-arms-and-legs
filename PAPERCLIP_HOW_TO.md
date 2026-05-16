# 📎 Paperclip — How To Use It

**On your Windows 10 computer. That's it. Five steps.**

---

## STEP 1 — Install Python (one time, ever)

1. Go to https://www.python.org/downloads/
2. Click the big yellow **Download Python** button.
3. Run the file it downloads.
4. **TICK THE BOX** that says *"Add Python to PATH"* at the bottom.
5. Click **Install Now**. Wait. Click **Close**.

---

## STEP 2 — Get Paperclip onto your computer

1. Make a folder on your Desktop called `paperclip`.
2. Download these two files into it (from this repo):
   - `paperclip.py`
   - `launch_paperclip.pyw`

---

## STEP 3 — Install the bits Paperclip needs (one time, ever)

1. Press the **Windows key**, type `cmd`, press **Enter**. A black box opens.
2. Copy this line. Paste it in the black box. Press **Enter**:

```
pip install pynput pystray pillow pywin32 psutil pyperclip mss uiautomation
```

3. Wait until it stops printing stuff and you see the prompt again.
4. Close the black box.

---

## STEP 4 — Run it

1. Go to your `paperclip` folder on the Desktop.
2. **Double-click `launch_paperclip.pyw`**.

**What you will see:**
- A small grey paperclip icon appears in the **top-left corner** of your screen.
- A red dot on it says `0`. That is how many things it has saved.
- Down in your **system tray** (bottom-right, next to the clock — you may need to click the little `^` arrow to see hidden icons) there is also a paperclip icon. That's the settings/quit menu.

**If you don't see the system tray icon:** click the `^` arrow next to the clock. It's hiding there. Right-click it → **drag it onto the visible tray** so it stays out.

---

## STEP 5 — Use it

**Whenever you realise you've drifted off-task:**

👉 **Right-click three times fast** anywhere on screen.

That's it. Don't think. Don't type. Don't name it. Just click click click.

**What happens:**
- The red number on the floating paperclip goes up by 1.
- Paperclip silently grabbed: the window you were in, the browser tab, the URL, a screenshot, and the time.

**To see what you saved:** click the floating paperclip. A small dark panel opens listing everything you've pinned this session.

**Every few minutes (between 3 and 7) a small dark note pops up:**
> *"Hey — remember you were working on: [whatever you pinned]"*

It disappears on its own after 8 seconds. You don't have to do anything.

**After 45 minutes of you not pinning anything new**, the list clears itself and starts fresh. (So old stuff doesn't haunt you forever.)

---

## To quit it

Right-click the paperclip in the system tray (bottom-right) → **Quit**.

---

## To make it start automatically when Windows starts

1. Press **Windows key + R**. A little box opens.
2. Type: `shell:startup` — press **Enter**. A folder opens.
3. Right-click `launch_paperclip.pyw` in your Desktop paperclip folder → **Create shortcut**.
4. Drag the shortcut into the `shell:startup` folder.

Done. It will run every time your computer turns on.

---

## To change the timings

Open this file in Notepad:

```
%APPDATA%\paperclip\settings.json
```

(Paste that into the Windows search bar, press Enter.)

You'll see:

```json
{
  "triple_click_window_ms": 600,    ← how fast the 3 clicks must be (milliseconds)
  "nudge_min_minutes": 3,           ← earliest a nudge can pop up
  "nudge_max_minutes": 7,           ← latest a nudge can pop up
  "auto_close_minutes": 45          ← how long until the session list clears
}
```

Change the numbers. Save. Restart Paperclip (quit from tray, double-click the launcher again).

---

## Where your saved stuff lives

```
%APPDATA%\paperclip\sessions.json   ← every pin you've ever made
%APPDATA%\paperclip\shots\          ← every screenshot
```

You can open that folder from the **system tray icon → Open data folder**.

---

That's the whole thing. Click three times when you're slipping. Paperclip catches you.
