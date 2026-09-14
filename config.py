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


# --- Little helpers that read settings safely -------------------
# If a setting is missing they just give back the fallback value,
# so the app never crashes because of a typo in config.ini.
# interpolation=None means a literal % in a value (a Windows path,
# say) cannot be mis-read as a variable.
def _make_parser():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(CONFIG_FILE)
    return parser


def read_setting(section, key, fallback=""):
    parser = _make_parser()
    try:
        return parser.get(section, key).strip()
    except Exception:
        return fallback


def has_setting(section, key):
    """True if the key actually exists in config.ini (even if blank)."""
    parser = _make_parser()
    try:
        return parser.has_option(section, key)
    except Exception:
        return False


def read_number(section, key, fallback):
    """Same as read_setting but for numbers (like 400 or 8)."""
    text = read_setting(section, key, "")
    try:
        return int(text)
    except Exception:
        return fallback


def read_true_false(section, key, fallback=True):
    """Same as read_setting but for true / false."""
    text = read_setting(section, key, "").lower()
    if text in ("true", "yes", "1", "on"):
        return True
    if text in ("false", "no", "0", "off"):
        return False
    return fallback


def read_section(section):
    """Every key = value pair of a whole section, as a dict."""
    parser = _make_parser()
    try:
        return {key: value.strip() for key, value in parser.items(section)}
    except Exception:
        return {}


# ============================================================
#  THE SETTINGS, LOADED ONCE, READY TO USE
# ============================================================

# About you
USER_NAME = read_setting("USER", "name", "Torex")

# THE wake word. Single, and config-driven: once the product gets a
# name, this becomes "hey <app-name>" with zero code changes.
WAKE_WORD = read_setting("USER", "wake_word", "hey buddy").lower()

# Extra spellings of the SAME wake word (a small model plus a laptop
# mic sometimes mis-hears it). This is config-driven too:
#   * key missing        -> sensible defaults for "hey buddy"
#   * key present, empty -> no variants at all, exact phrase only
#   * key present, list  -> exactly your list (comma separated)
_DEFAULT_WAKE_VARIANTS = ["hey body", "hey budi", "hey brody", "hey buddy buddy"]
if has_setting("USER", "wake_word_variants"):
    WAKE_WORD_VARIANTS = [
        v.strip().lower()
        for v in read_setting("USER", "wake_word_variants").split(",")
        if v.strip()
    ]
else:
    WAKE_WORD_VARIANTS = list(_DEFAULT_WAKE_VARIANTS)

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

# 400 is a good default for a built-in laptop mic. Lower (200) if it
# never hears you, higher (500+) if it wakes up by itself.
ENERGY_THRESHOLD = read_number("LISTENING", "energy_threshold", 400)

DEVICE_INDEX = read_number("LISTENING", "device_index", -1)

# After every answer, keep listening for this many seconds WITHOUT
# needing the wake word again. 0 turns the follow-up window off.
FOLLOW_UP_WINDOW = read_number("LISTENING", "follow_up_window", 8)

# Folder where the Vosk listening model lives. Any Vosk English model
# works - the small one is fast, vosk-model-en-us-0.22 hears better.
# Relative paths are read next to this file, absolute paths as-is.
_model_folder_raw = read_setting("LISTENING", "model_folder", "")
if _model_folder_raw:
    if os.path.isabs(_model_folder_raw):
        MODEL_FOLDER = _model_folder_raw
    else:
        MODEL_FOLDER = os.path.join(BASE_DIR, _model_folder_raw)
else:
    MODEL_FOLDER = os.path.join(BASE_DIR, "models", "vosk-model-small-en-us-0.15")

# Safety
CONFIRM_DANGEROUS = read_true_false("COMMANDS", "confirm_dangerous", True)

# App overrides / additions for "open <name>" - see [APPS] in
# config.ini. Keys are spoken names (lowercased automatically).
APP_OVERRIDES = read_section("APPS")


# Quick sanity check so you get a clear message instead of a weird crash.
def gemini_ready():
    """Returns True only if the user actually pasted a real key."""
    return len(GEMINI_API_KEY) > 20
