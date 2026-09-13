# ============================================================
#  config.py  -  READS YOUR SETTINGS FILE
# ============================================================
#  Every other file does:   import config
#  and then uses:           config.USER_NAME , config.WAKE_WORD ...
#
#  You do NOT need to edit this file. Edit config.ini instead.
# ============================================================

import os
import configparser


# Find the folder this file lives in.
# We do this so the app works no matter where you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Full path to the settings file, e.g. C:\TorexAssist\config.ini
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")


# --- A little helper that reads one setting safely --------------
# If the setting is missing it just gives back the fallback value,
# so the app never crashes because of a typo in config.ini.
def read_setting(section, key, fallback=""):
    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE)
    try:
        return parser.get(section, key).strip()
    except Exception:
        return fallback


def read_number(section, key, fallback):
    """Same as above but for numbers (like 300 or 8)."""
    text = read_setting(section, key, "")
    try:
        return int(text)
    except Exception:
        return fallback


def read_true_false(section, key, fallback=True):
    """Same as above but for true / false."""
    text = read_setting(section, key, "").lower()
    if text in ("true", "yes", "1", "on"):
        return True
    if text in ("false", "no", "0", "off"):
        return False
    return fallback


# ============================================================
#  THE SETTINGS, LOADED ONCE, READY TO USE
# ============================================================

# About you
USER_NAME = read_setting("USER", "name", "Torex")
WAKE_WORD = read_setting("USER", "wake_word", "hey buddy").lower()

# Voice
SPEECH_RATE = read_number("VOICE", "rate", 2)
VOICE_NAME = read_setting("VOICE", "voice_name", "")

# Online brain (Gemini)
GEMINI_API_KEY = read_setting("AI", "gemini_api_key", "").strip('"').strip("'")
GEMINI_MODEL = read_setting("AI", "gemini_model", "gemini-2.5-flash-lite")

# Offline brain (Ollama)
OLLAMA_MODEL = read_setting("AI", "ollama_model", "llama3.2:1b")
OLLAMA_ADDRESS = "http://127.0.0.1:11434"

# Weather
CITY = read_setting("WEATHER", "city", "")

# Listening
LISTEN_TIMEOUT = read_number("LISTENING", "listen_timeout", 8)
ENERGY_THRESHOLD = read_number("LISTENING", "energy_threshold", 300)
DEVICE_INDEX = read_number("LISTENING", "device_index", -1)

# Safety
CONFIRM_DANGEROUS = read_true_false("COMMANDS", "confirm_dangerous", True)

# Folder where the Vosk listening model lives
MODEL_FOLDER = os.path.join(BASE_DIR, "models", "vosk-model-small-en-us-0.15")


# Quick sanity check so you get a clear message instead of a weird crash.
def gemini_ready():
    """Returns True only if the user actually pasted a real key."""
    return len(GEMINI_API_KEY) > 20
