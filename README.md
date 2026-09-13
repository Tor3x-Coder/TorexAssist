# 🎙️ TorexAssist

A voice assistant for Windows 11 that:

- greets you when you log in, using the voice already built into Windows
- listens in the background for **"hey buddy"**
- runs PC commands instantly (open apps, check battery, weather, volume…)
- talks to **Google Gemini** when you have internet
- **silently switches to Ollama** running on your own laptop when you don't

No error messages when the internet dies. It just changes brain and keeps going.

---

## 📁 The files (one job each, so nothing is confusing)

| File | What it is, in plain words |
|---|---|
| `main.py` | **The app. Start here.** Runs the forever-loop. |
| `config.ini` | **Your settings.** The only file you normally edit. |
| `config.example.ini` | A blank copy of the settings, for reference. |
| `config.py` | Reads `config.ini` for the other files. |
| `speaker.py` | The **mouth**. Makes Windows talk. |
| `ears.py` | The **ears**. Microphone + wake word listening. |
| `commands.py` | The **hands**. Opens apps, checks battery, etc. |
| `brain.py` | The **brain switch**. Gemini ⇄ Ollama. |
| `internet.py` | Quietly checks if you're online, in the background. |
| `weather.py` | Fetches **real** weather (free, no API key). |
| `setup_check.py` | **The doctor.** Tests everything and tells you what's broken. |
| `requirements.txt` | The list of libraries to install. |
| `run_assistant.bat` | Double-click launcher. |
| `models/` | Where you put the Vosk model folder. |

---

## 🚀 SETUP — follow these in order

### Step 0 — Get the code onto your laptop

⚠️ **Read this or you will end up with an empty folder.**

The code currently lives on a **branch**, not on `main`. If you run a plain
`git clone`, you will download *only the README* and wonder where everything went.

Open a terminal in the place you want the project (for example `C:\Users\akach`)
and run this **exact** command, which asks for the right branch:

```
git clone -b arena/01a09bd2-torexassist https://github.com/Tor3x-Coder/TorexAssist.git
```

Then move into it:

```
cd TorexAssist
dir
```

You should see `main.py`, `ears.py`, `brain.py`, `commands.py`, `speaker.py`
and the rest. If you only see `README.md`, the `-b` part was missing — delete
the folder and run the clone command again with `-b`.

> **Don't use git / prefer clicking?** On the GitHub page, switch the branch
> dropdown to `arena/01a09bd2-torexassist`, then **Code → Download ZIP**, and
> unzip it. Same result.

---

### Step 1 — Check your Python

Open a terminal (`Win` key → type `cmd` → Enter) and run:

```
python --version
```

You want **Python 3.11, 3.12, 3.13 or 3.14**. All of them work — every library
this app needs already ships a wheel for 3.14, so you do **not** need to
downgrade or reinstall anything.

> This app deliberately avoids `pyttsx3` and `audioop`, which are the two things
> that normally break on newer Python. That is why 3.14 is fine here.

If you have no Python at all, or it is older than 3.11: install it from
<https://www.python.org/downloads/> and **tick the box that says
"Add python.exe to PATH"**. If you forget that box, nothing works and the
error messages are confusing.

> 🛟 **If one library ever refuses to install on 3.14:** install Python 3.12
> *alongside* it (do not uninstall 3.14 — Windows happily keeps both), then run
> everything with `py -3.12` instead of `python`.

### Step 2 — Install Ollama + the offline model

1. Install Ollama from <https://ollama.com/download/windows>
2. Open a terminal (press `Win`, type `cmd`, press Enter) and run:

```
ollama pull llama3.2:1b
```

That downloads about 1.3 GB. You only do it once.

> 💡 Your laptop can also handle `ollama pull llama3.2:3b` (about 2 GB), which is
> noticeably smarter offline. If you want it, change `ollama_model` in `config.ini`.

### Step 3 — Install the Python libraries

Open a terminal **inside the TorexAssist folder** and run:

```
pip install -r requirements.txt
```

### Step 4 — Download the listening model (the ears)

1. Go to <https://alphacephei.com/vosk/models>
2. Download **`vosk-model-small-en-us-0.15`** (about 40 MB)
3. Unzip it
4. Put the unzipped folder inside the `models` folder, so you end up with:

```
TorexAssist/
└── models/
    └── vosk-model-small-en-us-0.15/
        ├── am/
        ├── conf/
        ├── graph/
        └── ...
```

> ⚠️ Common mistake: unzipping gives you `vosk-model-small-en-us-0.15` *inside*
> another folder, so you end up with `models/vosk-model.../vosk-model.../`.
> The folder name must be **directly** inside `models`.

### Step 5 — Get your free Gemini key

1. Go to <https://aistudio.google.com/apikey>
2. Sign in with a Google account, click **Create API key**, copy it
3. Open `config.ini` in Notepad and paste it in:

```ini
gemini_api_key = AIzaSyD...your_actual_key_here...
```

> 🔒 **Never share this key.** It's like your ATM PIN.
> That's why `config.ini` is in `.gitignore` — git will never upload it.
>
> **Optional:** skip this step entirely and the app still works, using only Ollama.

### Step 6 — Turn on Windows microphone permission ⚠️ IMPORTANT

**Windows Settings → Privacy & security → Microphone**

Turn **ON**:
- "Microphone access"
- "**Let desktop apps access your microphone**"

> 🚨 If the second one is off, your app gets **pure silence with NO error message**.
> This is the #1 reason people think their code is broken. It isn't.

### Step 7 — Run the doctor

```
python setup_check.py
```

It tests all 10 parts and prints `[ OK ]` or `[FAIL]` with the exact fix.
**Get everything green before you continue.**

### Step 8 — Run the app

```
python main.py
```

…or just double-click `run_assistant.bat`.

Say: **"hey buddy"**, wait for *"Yes?"*, then speak.

---

## 🗣️ What you can say

### Wake it up
> "hey buddy"

### Instant PC commands (these never touch the AI — they're immediate and work offline)

| Say this | What happens |
|---|---|
| "open vscode" / "open chrome" / "open notepad" | Opens that app |
| "check battery" | Reads your real battery % and time left |
| "what is the time" / "what is the date" | Tells you |
| "what is the weather" | **Real** live weather (see note below) |
| "mute" / "volume up" / "volume down" | Presses the volume keys for you |
| "system info" | Memory and CPU usage |
| "my ip address" | Your local IP |
| "search google for nigeria news" | Opens the search in your browser |
| "play afrobeats on youtube" | Opens YouTube search |
| "lock the computer" | Locks Windows |
| "shut down" / "restart" / "sleep" | **Asks "are you sure?" first** |
| "what can you do" | Reads out the full list |
| "forget everything" | Clears the conversation memory |
| "exit" | Closes the assistant |

### Anything else → the AI
> "hey buddy" … *"tell me a joke"*
> "hey buddy" … *"explain what RAM does"*
> "hey buddy" … *"what's the difference between TCP and UDP"*

---

## ⚠️ The weather thing (please read)

The **free** Gemini API **cannot look things up on the internet**. Google keeps that
feature ("Grounding with Google Search") for paying customers.

So if you asked free Gemini *"what's the weather?"* it wouldn't say "I don't know" —
it would **invent a confident wrong answer** and your laptop would say it out loud.

**That's why `weather.py` exists.** It fetches the real numbers from
[Open-Meteo](https://open-meteo.com) — free, no account, no key — and hands them to
the AI to phrase nicely. Always accurate, never hallucinated.

Set your city in `config.ini` for best results:
```ini
[WEATHER]
city = Lagos
```
Leave it blank and it guesses from your internet connection (usually right, sometimes wrong on mobile data).

---

## 🔁 How the online/offline switch actually works

The internet check in `internet.py` is only a **hint**. The real logic is in `brain.py`:

```
You ask something
      │
      ▼
Is it a PC command?  ──yes──►  run it instantly, no AI at all
      │no
      ▼
Try Gemini  ──works──►  answer
      │fails (ANY reason: blackout, wifi login page, rate limit,
      │        bad key, Google down, slow network…)
      ▼
Ollama on your laptop  ──►  answer
      │fails
      ▼
"Sorry, both my brains are down"  (never a crash, never a traceback)
```

You will never see an exception. The worst case is a slightly less clever answer.

---

## 🖥️ What PC do you need?

| | Minimum | Comfortable (you are here ✅) |
|---|---|---|
| CPU | 8th gen i5 / Ryzen 5 | **i5 ✔** |
| RAM | 8 GB | **16 GB ✔** |
| Disk | 20 GB free | plenty ✔ |
| Storage type | SSD (important!) | SSD |
| GPU | **not needed** | not needed |

**Memory used while running:** roughly 3–4 GB on top of Windows itself
(Vosk small model ~300 MB, Ollama + llama3.2:1b ~2 GB, Python ~500 MB).
You have plenty of headroom.

**CPU used:** Vosk idling is about 1–3% of one core — you won't notice it.
Ollama will use most cores for the 5–20 seconds it's generating an answer
(fan will spin up). That's normal, not a fault.

---

## 🚀 Start it automatically when you log in

### Option A — Task Scheduler (recommended, no window flashes)

1. Press `Win`, type **Task Scheduler**, open it
2. Right side → **Create Task…**
3. **General** tab: name it `TorexAssist`
4. **Triggers** tab → New → *Begin the task:* **At log on**
5. **Actions** tab → New →
   - Program/script: `pythonw.exe`  ← the `w` version, so no black window
   - Add arguments: `"C:\full\path\to\TorexAssist\main.py"`
   - Start in: `C:\full\path\to\TorexAssist`
6. **Conditions** tab → untick *"Start only if on AC power"* (important on a laptop!)
7. OK

To find your exact paths, run this in a terminal:
```
where pythonw
```
and right-click `main.py` → Properties → copy the location.

### Option B — the easy way
Press `Win + R`, type `shell:startup`, press Enter.
Drop a shortcut to `run_assistant.bat` in that folder.
(Downside: a console window stays open.)

### About "when the laptop unlocks"
That's harder than "when I log in" — it needs either tricky Windows
session-message code, or running the app as Administrator (which we avoid,
because then any bug has power over your whole PC). Get login working first;
unlock can be added later.

---

## 🩺 Troubleshooting

| Symptom | Cause / fix |
|---|---|
| **It never hears me at all** | Windows mic privacy setting. Step 6 above. Almost always this. |
| **It never hears "hey buddy"** | Built-in laptop mics are weak. Move closer, speak clearly, or lower `energy_threshold` in `config.ini` to `200`. Best fix: any cheap headset mic. |
| **It wakes up by itself / from the TV** | Raise `energy_threshold` to `500`, and remove loose spellings from `WAKE_WORDS` in `ears.py`. |
| **It answers itself in a loop** | Shouldn't happen — `speaker.is_speaking` mutes the mic. If it does, increase the pause at the bottom of `speaker._speak_worker`. |
| **`KeyError: 'sapi5'`** | You're on Python 3.13+. Install 3.11 or 3.12. (This app doesn't use pyttsx3, so you should not see this at all.) |
| **No sound but no error** | Wrong output device, or the app started before Windows audio was ready. There's already a 1-second delay in `main.py`. |
| **`ModuleNotFoundError: No module named 'vosk'`** | You have more than one Python. Run `py -3.11 -m pip install -r requirements.txt` then `py -3.11 main.py`. |
| **First offline answer takes 15 seconds** | Normal. Ollama is loading the model off disk. There's a beep so you know it's thinking. |
| **Gemini says the model doesn't exist** | Google renames free models. Check <https://ai.google.dev/gemini-api/docs/models> and update `gemini_model` in `config.ini`. |
| **"Open vscode" does nothing** | `code` isn't on your PATH. Put the full path in `APP_LIST` in `commands.py`. |
| **Ollama connection refused** | It isn't running. `main.py` tries to start it; if that fails, run `ollama serve` manually once. |

---

## ✏️ How to add your own command

Open `commands.py`.

**To add an app**, just add a line to `APP_LIST`:
```python
APP_LIST = {
    "vs code": "code",
    "blender": r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    #  ^ the r before the quote matters on Windows paths
}
```

**To add a new action**, copy any block in `try_command()` and change the words:
```python
if "open my notes" in words:
    run_hidden(r"notepad C:\Users\You\notes.txt")
    return True, "Opening your notes."
```

That's it. No other file needs touching.

---

## 🔒 Privacy notes

- **Vosk** (the ears) is 100% offline. Your voice never leaves the laptop.
- **Ollama** (the offline brain) is 100% offline.
- **Gemini** sends your text to Google. On the **free tier Google may use your
  prompts to improve their products**, including human review. So don't tell it
  passwords, bank details, or anything private.
- Your API key lives in `config.ini`, which git is told to never upload.

---

## 🗺️ Where to go next (once this all works)

1. **Nicer voice** — download [Piper](https://github.com/rhasspy/piper) for a
   natural-sounding offline voice instead of Microsoft David.
2. **Detect unlock, not just login** — needs `pywin32` session messages.
3. **Bigger offline brain** — `ollama pull llama3.2:3b` and change one line in `config.ini`.
4. **Better ears** — `faster-whisper` is much more accurate than Vosk (at the cost
   of a ~1 second delay, since it transcribes after you stop talking).
5. **System tray icon** — so you can always see whether it's listening.

---

Made to be read and edited. Every file is commented like a tutorial on purpose. 🛠️
