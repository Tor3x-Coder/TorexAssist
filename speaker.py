# ============================================================
#  speaker.py  -  MAKES YOUR LAPTOP TALK
# ============================================================
#  This uses the voice that is ALREADY inside Windows.
#  No internet needed. No download needed. No cost.
#
#  How other files use it:
#
#       import speaker
#       speaker.say("Good morning Torex")
#
#  WHY WE DO NOT USE pyttsx3:
#  pyttsx3 is popular but it breaks a lot on new Python versions
#  (the famous "KeyError: sapi5" error). Talking to Windows
#  directly is fewer moving parts, so fewer things can go wrong.
# ============================================================

import threading
import time

import config


# ------------------------------------------------------------
#  THE SPEAKING FLAG   (very important!)
# ------------------------------------------------------------
#  While the laptop is talking, it must NOT listen.
#  If it listens to its own voice it will answer itself forever.
#
#  ears.py checks this flag. When it is True, the mic is ignored.
# ------------------------------------------------------------
is_speaking = False


# Try to connect to the Windows voice engine.
# If pywin32 is not installed we keep engine = None and the app
# still runs, it just prints words on screen instead of speaking.
engine = None

try:
    import win32com.client
    engine = win32com.client.Dispatch("SAPI.SpVoice")
except Exception:
    engine = None


# Remember the voice we picked so we only set it once.
_voice_ready = False


def _setup_voice():
    """Pick which Windows voice to use, and how fast it talks."""
    global _voice_ready

    if engine is None:
        return

    # --- Speed ---
    # Windows uses -10 (very slow) to +10 (very fast). 0 is normal.
    try:
        engine.Rate = config.SPEECH_RATE
    except Exception:
        pass

    # --- Which voice ---
    # Only change it if the user wrote a name in config.ini.
    if config.VOICE_NAME:
        try:
            voices = engine.GetVoices()
            for i in range(voices.Count):
                description = voices.Item(i).GetDescription()
                # We match loosely: if the name is anywhere inside the
                # description, we use that voice.
                if config.VOICE_NAME.lower() in description.lower():
                    engine.Voice = voices.Item(i)
                    break
        except Exception:
            pass  # If it fails, just keep the default voice.

    _voice_ready = True


def list_voices():
    """Print all the voices installed on this Windows machine."""
    if engine is None:
        print("Windows voice engine is not available.")
        return

    voices = engine.GetVoices()
    print("\nVoices installed on this computer:")
    for i in range(voices.Count):
        print("   " + voices.Item(i).GetDescription())
    print()


# ------------------------------------------------------------
#  The real talking function (runs inside its own thread)
# ------------------------------------------------------------
def _speak_worker(text):
    global is_speaking

    is_speaking = True

    try:
        if engine is not None:
            if not _voice_ready:
                _setup_voice()
            engine.Speak(text)
        else:
            # No voice engine. Show the words instead so you can
            # still test the app.
            print("\n[WOULD SAY] " + text + "\n")
    except Exception as error:
        print("Speaking failed: " + str(error))

    # Small pause after talking.
    # This gives the sound time to fade away so the mic does not
    # pick up the last echo of our own voice.
    time.sleep(0.35)

    is_speaking = False


# ------------------------------------------------------------
#  say()  -  the function you will actually call
# ------------------------------------------------------------
#  wait=True   -> the app stops and waits until talking finishes.
#                 Use this for greetings and answers.
#  wait=False  -> it talks in the background and your code keeps
#                 going. Rarely needed.
# ------------------------------------------------------------
def say(text, wait=True):
    # Always show what it said in the console too. Helps with debugging.
    print("TorexAssist: " + str(text))

    thread = threading.Thread(target=_speak_worker, args=(str(text),))
    thread.start()

    if wait:
        thread.join()
