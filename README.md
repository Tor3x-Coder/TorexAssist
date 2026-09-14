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

Open a terminal in the place you want the project (for example `C:\Users\akach`)
and run:

```
git clone https://github.com/Tor3x-Coder/TorexAssist.git
cd TorexAssist
dir
```

You should see `main.py`, `ears.py`, `brain.py`, `commands.py`, `speaker.py`
and the rest.

> **Don't use git / prefer clicking?** On the GitHub page click
> **Code → Download ZIP**, and unzip it. Same result.

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
2. Download a model. Two good choices:
   - **`vosk-model-small-en-us-0.15`** (about 40 MB) — light and quick
   - **`vosk-model-en-us-0.22`** (about 1.8 GB) — hears noticeably better
3. Unzip it
4. Put the unzipped folder inside the `models` folder, so you end up with e.g.:

```
TorexAssist/
└── models/
    └── vosk-model-small-en-us-0.15/
        ├── am/
        ├── conf/
        ├── graph/
        └── ...
```

5. Tell the app which folder to use in `config.ini`:

```ini
[LISTENING]
model_folder = models/vosk-model-small-en-us-0.15
```

Any Vosk English model works — the folder name does not have to be anything
special, because `model_folder` points at it. Absolute paths like
`C:\models\my-vosk` work too.

> ⚠️ Common mistake: unzipping gives you the model folder *inside*
> another folder, so you end up with `models/vosk-model.../vosk-model.../`.
> The model folder must be **directly** inside `models`
> (or point `model_folder` at wherever it really is).

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

There is exactly **one** wake word. It is set in `config.ini` (`wake_word`),
so when the product gets its real name it becomes *"hey <app-name>"* with no
code change. A few forgiving spellings of that same phrase (so a noisy mic is
forgiven) live in `wake_word_variants`.

### Instant PC commands (these never touch the AI — they're immediate and work offline)

| Say this | What happens |
|---|---|
| "open chrome" / "open vscode" / "open blender" | Opens that app — see **opening apps** below |
| "check battery" | Reads your real battery % and time left |
| "what is the time" / "what is the date" | Tells you |
| "what is the weather" | **Real** live weather (see note below) |
| "mute" / "volume up" / "volume down" | Presses the volume keys for you |
| "system info" | Memory and CPU usage |
| "my ip address" | Your local IP |
| "search google for nigeria news" | Opens the search in your browser |
| "play afrobeats on youtube" | Opens YouTube search |
| "lock the computer" | Locks Windows (**keeps listening** — see lifecycle) |
| "shut down" / "restart" / "sleep" | **Asks "are you sure?" first** |
| "what can you do" | Reads out the full list |
| "forget everything" / "start over" | Clears the conversation memory |
| "exit" / "quit" / "I am done with you" / "go offline" | Closes the assistant |

### Opening apps — no hardcoded list

There is **no fixed app list** to edit. When you say "open …", TorexAssist
auto-discovers what you have installed:

1. It scans every shortcut in your **Start Menu** (yours + all users) and
   resolves what each one really launches.
2. It merges in every program on your **PATH**.
3. It asks Windows for the full **All-apps list** (`Get-StartApps`) — this
   is the only place Microsoft Store apps like WhatsApp or Snapchat show
   up, because Store apps leave no shortcuts behind.
4. It fuzzy-matches what you said, so "open chome" still finds Chrome and
   "open vs code" still finds Visual Studio Code.

If it genuinely can't find the app, it tells you — *"I couldn't find an app
called X"* — instead of running a guess and popping up an empty black window.

To add or override an app it didn't spot, put one line in the `[APPS]`
section of `config.ini`:

```ini
[APPS]
blender = C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
my notes = notepad C:\Users\You\notes.txt
```

### The follow-up window — just keep talking

After the assistant answers, it **keeps listening for about 8 seconds**
without needing the wake word again. So you can have a real back-and-forth:

> you: "hey buddy" … *"what is the weather?"*
> assistant: *"It is 31 degrees and sunny."*
> you: *"and tomorrow?"* ← no wake word needed

Each new answer opens a fresh window; a few seconds of silence drops you back
to wake-word mode. Change the length (or set it to `0` to turn it off) with
`follow_up_window` in `config.ini`.

### Big ears mode (Whisper) — for noisy rooms

If the built-in mic + Vosk mis-hears you too much, switch on the **big ears**:

```
pip install faster-whisper
```
```ini
[LISTENING]
ears_backend = whisper
whisper_model = small
```

This uses OpenAI's pre-trained **Whisper** model through `faster-whisper`.
It is downloaded **once**, then runs 100% offline — your voice never leaves
the laptop, so the privacy promise holds. It hears dramatically better than
Vosk in noise, TV mush and laptop-mic echo. The price: it writes down what
you said *after* you stop talking (a 1-2 second pause). The wake word still
uses the light Vosk model, so idling stays cheap. If `small` feels slow on
your PC, set `whisper_model = base`.

---

## 🔌 Lifecycle — what each power word actually does

These four sound similar but do very different things. Knowing the difference
stops a careless phrase from killing your work.

| You say | Scope | What actually happens |
|---|---|---|
| "exit" / "quit" / "I am done with you" / "go offline" | **the assistant** | Full close of TorexAssist itself. The mic is released and the program ends. Your PC keeps running. |
| "go to sleep" / "sleep mode" | **the machine** | The laptop sleeps. The assistant just **pauses** with it and carries on when you wake. |
| "lock the computer" | **the screen** | Windows locks. The assistant **keeps listening** on the lock screen, so you can call it right back. |
| "shut down" / "restart" | **the machine** | Machine power-off / reboot. Always confirms first, because a mic mis-hear must never kill your work. |

> 💡 The subtle one: **"go to sleep"** sleeps the *machine*, while
> **"go to sleep now"** (and the other exit phrases) closes the *assistant*.

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
| **It wakes up by itself / from the TV** | Raise `energy_threshold` to `500`, and empty `wake_word_variants` in `config.ini` so only the exact wake word is accepted. |
| **It answers itself in a loop** | Shouldn't happen — `speaker.is_speaking` mutes the mic. If it does, increase the pause at the bottom of `speaker._speak_worker`. |
| **`KeyError: 'sapi5'`** | You're on Python 3.13+. Install 3.11 or 3.12. (This app doesn't use pyttsx3, so you should not see this at all.) |
| **No sound but no error** | Wrong output device, or the app started before Windows audio was ready. There's already a 1-second delay in `main.py`. |
| **`ModuleNotFoundError: No module named 'vosk'`** | You have more than one Python. Run `py -3.11 -m pip install -r requirements.txt` then `py -3.11 main.py`. |
| **First offline answer takes 15 seconds** | Normal. Ollama is loading the model off disk. There's a beep so you know it's thinking. |
| **Gemini says the model doesn't exist** | Google renames free models. Check <https://ai.google.dev/gemini-api/docs/models> and update `gemini_model` in `config.ini`. |
| **"Open X" says it can't find the app** | It isn't in your Start Menu or PATH. Add it under `[APPS]` in `config.ini` (full path on the right). |
| **"Open X" opens the wrong app** | The fuzzy match guessed. Say the app's exact shortcut name, or add the exact name under `[APPS]` in `config.ini`. |
| **Ollama connection refused** | It isn't running. `main.py` tries to start it; if that fails, run `ollama serve` manually once. |

---

## ✏️ How to add your own command

**To add an app**, you normally don't need to touch any code — apps are
auto-discovered from your Start Menu and PATH. If one is missing, add a line
to the `[APPS]` section of `config.ini`:
```ini
[APPS]
blender = C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
#  The left side is what you SAY, the right side is what RUNS.
#  Right side can be a full path, a plain command, or a windows: URI.
```

**To add a new action**, open `commands.py`, copy any block in
`try_command()` and change the words:
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

## 🗺️ The master plan, in order

**Already shipped and working on the laptop today:** wake-word listening +
follow-up window, auto-discovered app opening (Start Menu + PATH + Store
apps), instant PC commands, real weather, the Gemini cloud brain with
conversation memory, silent online/offline design, config-driven everything,
and the setup doctor. Functionally it is already an assistant; the list below
is what turns "a folder of scripts" into a real product.

The remaining work, in the order we agreed to do it:

1. **Name the product** — everything else hangs off the name: the wake word
   becomes "hey \<name>" (already config-driven), plus icon and window title.
   *(tiny, no download)*
2. **Buddy-tone replies** — a personality pass on the brain's instruction
   (system prompt) so answers sound like your mate, not a customer-service
   robot. *(tiny, no download)*
3. **First-run wizard** — on first launch: ask your name out loud, run a mic
   self-test (quality gate), and write everything to `config.ini`. If the mic
   fails the bar, recommend a cheap headset mic before continuing.
   *(small, no download)*
4. **Grammar-capable big ears** — the plain `vosk-model-en-us-0.22` ignores
   the wake-word word-list trick ("Runtime graphs are not supported"), so the
   idle ear listens with the full vocabulary and false wakes go up. Fix:
   swap to `vosk-model-en-us-0.22-lgraph`, or run TWO models (small one
   idling on the wake word, big one while you talk). *(download or medium code)*
5. **Never-die hardening** — a log file (so debugging doesn't need
   copy-pasting the console) plus auto-restart on crash, and mic recovery
   after the laptop sleeps or the mic gets stolen by Zoom/Teams. *(small)*
6. **System tray icon** — always see whether it is listening; right-click for
   mute / exit. *(small)*
7. **Nicer voice** — swap the built-in SAPI voice for
   [Piper](https://github.com/rhasspy/piper) neural voices, with a voice
   picker. *(medium, download)*
8. **Settings window (GUI)** — edit settings without Notepad. *(medium)*
9. **Real installer** — one double-click installer (PyInstaller + Inno):
   app icon, Start Menu shortcut, start-at-login, uninstaller. THIS is the
   moment it becomes a "real app" for Windows. *(medium)*
10. **Updater** — get new versions without `git pull`. *(small-medium)*
11. **Ollama offline brain** — guided install for the blackout brain once
    there is enough data (~2.7 GB). *(download)*
12. **Better ears (SHIPPED, optional)** — `faster-whisper` backend
    (`ears_backend = whisper` in config.ini): open, pre-trained Whisper
    ears that run fully **offline** and hear about as well as the
    commercial assistants in noisy rooms — no mic upgrade required, no
    audio ever leaves the laptop. Trade-off: a 1-2 second think-pause
    after you stop talking. The wake word stays on light Vosk, so you
    get the best of both.
13. **Live-news tool** — real headlines, since free Gemini cannot browse the
    web and declines honestly. *(small)*

---

Made to be read and edited. Every file is commented like a tutorial on purpose. 🛠️
