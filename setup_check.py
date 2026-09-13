# ============================================================
#  setup_check.py  -  DOCTOR FOR YOUR APP
# ============================================================
#  Run this BEFORE main.py, and any time something misbehaves:
#
#       python setup_check.py
#
#  It tests every single part of TorexAssist one by one and tells
#  you exactly what is broken and how to fix it. No guessing.
# ============================================================

import os
import sys

import config


PASS = "  [ OK ]    "
FAIL = "  [FAIL]    "
WARN = "  [WARN]    "

problems = 0


def heading(text):
    print("\n" + "-" * 64)
    print("  " + text)
    print("-" * 64)


def ok(text):
    print(PASS + text)


def bad(text, fix_lines):
    global problems
    problems += 1
    print(FAIL + text)
    for line in fix_lines:
        print("            " + line)


def warn(text, fix_lines):
    print(WARN + text)
    for line in fix_lines:
        print("            " + line)


print("=" * 64)
print("   TOREX ASSIST  -  SETUP CHECK")
print("=" * 64)


# ------------------------------------------------------------
# 1. WINDOWS
# ------------------------------------------------------------
heading("1. Operating system")
if sys.platform == "win32":
    ok("You are on Windows.")
else:
    warn("You are NOT on Windows (detected: " + sys.platform + ").",
         ["The voice and some commands are written for Windows.",
          "The AI parts will still work for testing."])


# ------------------------------------------------------------
# 2. PYTHON VERSION
# ------------------------------------------------------------
heading("2. Python version")
version = sys.version_info
shown = str(version.major) + "." + str(version.minor) + "." + str(version.micro)

if version.major != 3:
    bad("This is Python " + shown + ", not Python 3.",
        ["Install Python 3 from https://www.python.org/downloads/"])
elif version.minor in (11, 12, 13, 14):
    ok("Python " + shown + " - good.")
    if version.minor >= 13:
        print("            Note: 3.13 and 3.14 are very new, so a library could")
        print("            still lag behind. Every package this app needs already")
        print("            ships a 3.14 wheel, so you should be fine.")
        print("            If one ever fails to install, install Python 3.12")
        print("            ALONGSIDE this one (do not uninstall 3.14) and then")
        print("            run everything with:   py -3.12 main.py")
elif version.minor == 10:
    warn("Python " + shown + " - works, but 3.11 or newer is better.",
         ["Upgrade from https://www.python.org/downloads/ if you can."])
else:
    bad("Python " + shown + " is too old.",
        ["Install Python 3.11 or newer from https://www.python.org/downloads/",
         "Tick 'Add python.exe to PATH' during install."])


# ------------------------------------------------------------
# 3. LIBRARIES
# ------------------------------------------------------------
heading("3. Python libraries")

needed = [
    ("vosk",         "pip install vosk",          "the ears (speech to text)"),
    ("sounddevice",  "pip install sounddevice",   "the microphone"),
    ("requests",     "pip install requests",      "talking to the internet"),
    ("psutil",       "pip install psutil",        "battery and system info"),
    ("win32com.client", "pip install pywin32",    "the voice (Windows SAPI)"),
    ("win32api",     "pip install pywin32",       "volume keys"),
]

for name, install_command, purpose in needed:
    try:
        __import__(name)
        ok(name + "  -  " + purpose)
    except ImportError:
        bad(name + " is missing  -  " + purpose, ["Run:  " + install_command])

# The Gemini library is optional - the app works without it.
try:
    from google import genai
    ok("google-genai  -  the cloud brain")
except ImportError:
    warn("google-genai is missing. Online mode will not work.",
         ["Run:  pip install google-genai",
          "The app will still run, using Ollama only."])


# ------------------------------------------------------------
# 4. VOSK MODEL
# ------------------------------------------------------------
heading("4. Listening model (Vosk)")
if os.path.exists(config.MODEL_FOLDER):
    ok("Model folder found.")
    # Check the important file inside it actually exists
    final_file = os.path.join(config.MODEL_FOLDER, "am", "final.mdl")
    if os.path.exists(final_file):
        ok("Model files look complete.")
    else:
        bad("The folder is there but looks empty or half-unzipped.",
            ["Re-download and unzip it properly.",
             "Expected: " + final_file])
else:
    bad("Model folder NOT found.",
        ["Expected here:",
         "  " + config.MODEL_FOLDER,
         "Download 'vosk-model-small-en-us-0.15' from:",
         "  https://alphacephei.com/vosk/models",
         "Unzip it into: " + os.path.join(config.BASE_DIR, "models")])


# ------------------------------------------------------------
# 5. MICROPHONE
# ------------------------------------------------------------
heading("5. Microphone")
try:
    import sounddevice
    devices = sounddevice.query_devices(kind="input")
    count = 0
    for item in devices:
        if int(item.get("max_input_channels", 0)) > 0:
            count += 1
    if count > 0:
        ok("Found " + str(count) + " input device(s).")
        print("\n        Your microphones:")
        for index, item in enumerate(devices):
            if int(item.get("max_input_channels", 0)) > 0:
                print("          [" + str(index) + "] " + str(item["name"]))
        print("        Default one is used unless you set device_index in config.ini\n")
    else:
        bad("No microphone found at all.",
            ["Plug one in, or check Windows Settings -> System -> Sound."])
except Exception as error:
    bad("Could not check the microphone.", [str(error)])

# The Windows privacy setting cannot be read from here, so just remind.
print("  REMINDER:  Windows Settings -> Privacy and security -> Microphone")
print("             -> turn ON 'Let desktop apps access your microphone'.")
print("             If this is OFF you get SILENCE with no error message.")


# ------------------------------------------------------------
# 6. VOICE
# ------------------------------------------------------------
heading("6. Voice")
try:
    import speaker
    if speaker.engine is not None:
        ok("Windows voice engine is available.")
        speaker.list_voices()
        answer = input("        Type 'y' and press Enter to hear a test sentence: ")
        if answer.strip().lower() == "y":
            speaker.say("Hello " + config.USER_NAME + ", my voice is working.")
            ok("Test spoken.")
    else:
        bad("Windows voice engine is not available.",
            ["Run:  pip install pywin32"])
except Exception as error:
    bad("Voice test failed.", [str(error)])


# ------------------------------------------------------------
# 7. INTERNET
# ------------------------------------------------------------
heading("7. Internet")
import internet as net
if net._do_one_check():
    ok("You are connected to the internet.")
else:
    warn("No internet right now.",
         ["That is fine - the app will use Ollama.",
          "But you cannot get a Gemini API key until you are online."])


# ------------------------------------------------------------
# 8. GEMINI KEY
# ------------------------------------------------------------
heading("8. Cloud brain (Google Gemini)")
if config.gemini_ready():
    ok("An API key is present in config.ini (" + str(len(config.GEMINI_API_KEY)) + " characters).")
    try:
        from google import genai
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        reply = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents="Reply with exactly the word: ready",
        )
        ok("Gemini answered. Model '" + config.GEMINI_MODEL + "' works.")
    except Exception as error:
        bad("Gemini rejected the key or the model name.",
            [str(error)[:160],
             "Check the key at https://aistudio.google.com/apikey",
             "And check the model name in config.ini (free tier changes over time)."])
else:
    warn("No Gemini API key in config.ini yet.",
         ["Get a free one:  https://aistudio.google.com/apikey",
          "Paste it into config.ini like this:",
          "    gemini_api_key = AIza...yourkey...",
          "Until you do, only the offline brain will be used."])


# ------------------------------------------------------------
# 9. OLLAMA
# ------------------------------------------------------------
heading("9. Offline brain (Ollama)")
import requests
try:
    requests.get(config.OLLAMA_ADDRESS, timeout=2)
    ok("Ollama is running.")

    # Is the model downloaded?
    try:
        listing = requests.get(config.OLLAMA_ADDRESS + "/api/tags", timeout=5).json()
        names = [m.get("name", "") for m in listing.get("models", [])]
        wanted = config.OLLAMA_MODEL
        found = any(wanted in n or n.startswith(wanted.split(":")[0]) for n in names)
        if found:
            ok("Model '" + wanted + "' is downloaded.")
        else:
            bad("Model '" + wanted + "' is NOT downloaded.",
                ["Run this once:   ollama pull " + wanted,
                 "Models you do have: " + (", ".join(names) if names else "none")])
    except Exception as error:
        warn("Could not list Ollama models.", [str(error)[:120]])

except Exception:
    bad("Ollama is NOT running.",
        ["1. Install it from  https://ollama.com/download/windows",
         "2. Then run once:   ollama pull " + config.OLLAMA_MODEL,
         "3. Start it:        ollama serve",
         "   (main.py will also try to start it automatically)"])


# ------------------------------------------------------------
# 10. SETTINGS
# ------------------------------------------------------------
heading("10. Your settings")
print("        Name          : " + config.USER_NAME)
print("        Wake word     : " + config.WAKE_WORD)
print("        Speech rate   : " + str(config.SPEECH_RATE))
print("        Voice         : " + (config.VOICE_NAME or "(Windows default)"))
print("        City (weather): " + (config.CITY or "(auto-detect from internet)"))
print("        Listen timeout: " + str(config.LISTEN_TIMEOUT) + " seconds")
print("        Mic sensitivity: " + str(config.ENERGY_THRESHOLD) + "  (lower = more sensitive)")
ok("Settings file loaded.")


# ------------------------------------------------------------
# FINAL VERDICT
# ------------------------------------------------------------
print("\n" + "=" * 64)
if problems == 0:
    print("   ALL GOOD. Run the app with:")
    print("       python main.py")
else:
    print("   " + str(problems) + " problem(s) need fixing. See the [FAIL] lines above.")
print("=" * 64 + "\n")

input("Press Enter to close...")
