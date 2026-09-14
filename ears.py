# ============================================================
#  ears.py  -  THE MICROPHONE. LISTENS FOR "HEY BUDDY".
# ============================================================
#  This runs forever in the background, waiting to hear the wake
#  word. When it hears it, it listens to your full sentence and
#  hands the words back to main.py.
#
#  THE CLEVER BIT (please read, it is the heart of this app)
#  ---------------------------------------------------------
#  Vosk is NOT a wake-word machine. It is a "write down every sound
#  you hear" machine. If you let it write down everything it will
#  hear the TV, your friends, songs... and your code will either
#  find "hey buddy" inside all that noise by mistake, or miss you
#  completely when you actually say it.
#
#  So we use Vosk's GRAMMAR mode.
#
#  A grammar is just a list of the ONLY words Vosk is allowed to
#  hear. Anything else becomes "[unk]" (unknown) and gets thrown away.
#
#      "hey buddy"          -> recognised
#      "how are you today"  -> "[unk] [unk] [unk] [unk]" -> ignored
#
#  Result: far fewer false alarms, far better accuracy on your wake
#  word, and much less CPU used. This matters a LOT when you are on
#  a built-in laptop microphone rather than a good headset.
#
#  WE USE TWO LISTENING MODES
#  --------------------------
#    MODE 1 "wake"  - tiny word list. Always on. Almost no CPU.
#                     It can ONLY hear the wake word plus a few
#                     instant commands like "check battery".
#
#    MODE 2 "open"  - full vocabulary. Switched on for a few seconds
#                     AFTER you say the wake word, so you can ask
#                     anything you like. Then it drops back to mode 1.
#
#  That is the trick that keeps it both fast and flexible.
# ============================================================

import array
import json
import math
import os
import queue
import time

import config


# ============================================================
#  THE WORD LIST FOR MODE 1
# ============================================================
#  These are the only things the mic hears while the app is idling.
#  Add or remove words freely, it is just a list.
#
#  THE WAKE WORD IS SINGLE AND CONFIG-DRIVEN.
#  There is exactly one wake phrase - the one in config.ini
#  (currently "hey buddy"; once the product is named it becomes
#  "hey <app-name>", no code change needed). The VARIANTS are not
#  extra wake phrases: they are just forgiving spellings of the SAME
#  phrase, because a small model plus a laptop mic sometimes
#  mis-hears it. Real commercial assistants do the same thing.
#  Edit them (or switch them off) in config.ini -> wake_word_variants.
# ============================================================
WAKE_WORDS = [config.WAKE_WORD] + [
    variant for variant in config.WAKE_WORD_VARIANTS
    if variant and variant != config.WAKE_WORD
]

INSTANT_COMMANDS = [
    "open vscode",
    "open vs code",
    "open chrome",
    "open notepad",
    "open calculator",
    "open file explorer",
    "check battery",
    "battery level",
    "what is the time",
    "what time is it",
    "what is the date",
    "what is the weather",
    "mute",
    "volume up",
    "volume down",
    "system info",
    "shut down",
    "restart",
    "lock the computer",
    "what can you do",
    "exit",
    "quit",
]

# Clean up: lowercase, no blanks, no duplicates. Vosk needs lowercase.
WAKE_LIST = sorted(set(
    [w.lower().strip() for w in WAKE_WORDS + INSTANT_COMMANDS if w.strip()]
))

# The grammar = our words, plus "[unk]" which means "anything else".
GRAMMAR = json.dumps(WAKE_LIST + ["[unk]"])


# ============================================================
#  SOUND SETTINGS
# ============================================================
SAMPLE_RATE = 16000    # Vosk needs 16000 samples a second. Do not change.
BLOCK_SIZE = 4000      # A quarter second of sound per chunk.

model = None
wake_recognizer = None
open_recognizer = None
audio_queue = None
stream = None


# ============================================================
#  HELPER: how loud is this chunk of sound?
# ============================================================
def loudness(audio_bytes):
    """
    Returns the average loudness (0 = silence, bigger = louder).
    We use it to notice when you have stopped talking.

    Written by hand on purpose: the easy library for this (audioop)
    is being removed from newer Python versions, and we do not want
    your app to break next year.
    """
    try:
        samples = array.array("h")          # "h" = 16-bit sound samples
        samples.frombytes(audio_bytes)
        if len(samples) == 0:
            return 0
        total = 0
        for sample in samples:
            total += sample * sample
        return int(math.sqrt(total / len(samples)))
    except Exception:
        return 9999     # if this ever fails, assume it is loud so we listen


def list_microphones():
    """Print every microphone Windows can see."""
    try:
        import sounddevice
        print("\nMicrophones on this computer:")
        print(sounddevice.query_devices(kind="input"))
        print("\nTo force one, set device_index in config.ini\n")
    except Exception as error:
        print("Could not list microphones: " + str(error))


# ============================================================
#  START UP
# ============================================================
def setup():
    """
    Load the Vosk model and open the microphone.
    Called once when the app starts. Returns True if all is well.
    """
    global model, wake_recognizer, open_recognizer, audio_queue, stream

    # ---------- 1. Is the model folder there? ----------
    if not os.path.exists(config.MODEL_FOLDER):
        print("=" * 64)
        print("  ERROR: I cannot find the Vosk listening model.")
        print("=" * 64)
        print("  I looked here:")
        print("    " + config.MODEL_FOLDER)
        print()
        print("  How to fix it:")
        print("    1. Go to  https://alphacephei.com/vosk/models")
        print("    2. Download a model, e.g. 'vosk-model-small-en-us-0.15'")
        print("       (about 40 MB) or the bigger, better-hearing")
        print("       'vosk-model-en-us-0.22' (about 1.8 GB).")
        print("    3. Unzip it.")
        print("    4. Move the unzipped folder into:")
        print("         " + os.path.join(config.BASE_DIR, "models"))
        print("    5. Point model_folder in config.ini at the folder, e.g.:")
        print("         model_folder = models/vosk-model-small-en-us-0.15")
        print("=" * 64)
        return False

    # ---------- 2. Load Vosk ----------
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)      # hide Vosk's own technical messages
    except ImportError:
        print("ERROR: the vosk library is not installed.")
        print("Fix with:   pip install vosk")
        return False

    print("[ears] Loading the listening model, give me a few seconds...")
    try:
        model = Model(config.MODEL_FOLDER)
    except Exception as error:
        print("ERROR: the model folder is there but will not load.")
        print(str(error))
        return False

    # Two recognizers sharing ONE model, so we do not use double memory.
    #   wake_recognizer : limited to our word list. Always on. Light.
    #   open_recognizer : full vocabulary. Used only while you speak.
    wake_recognizer = KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)
    open_recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    # ---------- 3. Open the microphone ----------
    try:
        import sounddevice
    except ImportError:
        print("ERROR: sounddevice is not installed.")
        print("Fix with:   pip install sounddevice")
        return False

    device = config.DEVICE_INDEX
    if device == -1:
        device = None       # None = "use the Windows default microphone"

    # Sound arrives on its own thread, so we drop it in a queue and
    # our main loop picks it up safely. This is the normal, simple way
    # to move data between two threads.
    audio_queue = queue.Queue()

    def on_audio(data, frames, time_info, status):
        """sounddevice calls this every quarter second with fresh sound."""
        audio_queue.put(bytes(data))

    try:
        stream = sounddevice.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            device=device,
            dtype="int16",     # 16-bit sound, which is what Vosk wants
            channels=1,        # mono
            callback=on_audio,
        )
        stream.start()
    except Exception as error:
        print("=" * 64)
        print("  ERROR: I cannot open the microphone.")
        print("=" * 64)
        print("  " + str(error))
        print()
        print("  The usual causes, most likely first:")
        print("    1. Windows Settings -> Privacy and security -> Microphone")
        print("       -> turn ON 'Let desktop apps access your microphone'.")
        print("       THIS IS THE NUMBER ONE CAUSE. Windows shows NO error,")
        print("       the microphone just returns pure silence.")
        print("    2. Zoom / Teams / Discord is holding the mic.")
        print("    3. Wrong mic selected. Run:  python setup_check.py")
        print("=" * 64)
        return False

    print("[ears] Microphone is live. Waiting to hear: " + config.WAKE_WORD)
    return True


def shutdown():
    """
    Close the microphone cleanly when the app exits.
    Swallows EVERYTHING - including Ctrl+C - so the very last thing
    the app does is always a calm exit, never a traceback.
    """
    global stream
    try:
        if stream is not None:
            stream.stop()
            stream.close()
    except KeyboardInterrupt:
        pass        # Ctrl+C during shutdown: just keep going
    except Exception:
        pass
    stream = None


# ============================================================
#  THE "AM I TALKING?" GUARD
# ============================================================
def wait_until_quiet():
    """
    While the laptop is speaking, we must NOT listen.

    If it listens to its own voice it will hear itself, answer
    itself, hear that answer, answer again... forever. This is the
    single most common bug in home-made voice assistants.

    So we throw audio away until the voice has finished, plus a tiny
    extra moment for the echo to fade out of the room.
    """
    import speaker

    while speaker.is_speaking:
        drain_queue()
        time.sleep(0.05)

    drain_queue()


def drain_queue():
    """Empty the sound queue so stale audio is not processed later."""
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except Exception:
            break


def grab_audio():
    """Get the next quarter second of sound."""
    return audio_queue.get()


# ============================================================
#  MODE 1  -  WAIT FOR THE WAKE WORD  (runs forever)
# ============================================================
def wait_for_wake_word():
    """
    Sits here until it hears the wake word or an instant command.
    Returns the phrase it heard.
    """
    wake_recognizer.Reset()

    while True:
        wait_until_quiet()

        audio = grab_audio()

        # IMPORTANT: we feed EVERY chunk to Vosk, even quiet ones.
        # Speech recognition needs a continuous stream of sound.
        # If you feed it only the loud bits it gets confused and
        # accuracy drops. The loudness check is only used to skip
        # the (more expensive) result-reading step.
        finished = wake_recognizer.AcceptWaveform(audio)

        if not finished:
            # You are still mid-sentence. Peek at the partial result so
            # the wake word feels instant instead of waiting for silence.
            partial = json.loads(wake_recognizer.PartialResult())
            text = partial.get("partial", "").lower()
        else:
            result = json.loads(wake_recognizer.Result())
            text = result.get("text", "").lower()

        # Strip out the "unknown" marker before looking for our phrases.
        text = text.replace("[unk]", " ")
        text = " ".join(text.split())      # tidy up double spaces

        if not text:
            continue

        for phrase in WAKE_LIST:
            if phrase in text:
                wake_recognizer.Reset()
                return phrase


# ============================================================
#  MODE 2  -  LISTEN TO YOUR FULL SENTENCE
# ============================================================
def listen_for_command(timeout=None):
    """
    Called right after the wake word, and also during the follow-up
    window. Uses the FULL vocabulary so you can ask anything at all.

    Stops when you finish speaking, or after `timeout` seconds of
    nothing (default: config.LISTEN_TIMEOUT).
    Returns your words, or "" if it heard nothing.
    """
    if timeout is None:
        timeout = config.LISTEN_TIMEOUT

    wait_until_quiet()

    open_recognizer.Reset()
    drain_queue()

    collected = ""
    started_at = time.time()
    last_sound_at = time.time()

    while True:
        # Safety: never listen forever
        if time.time() - started_at > timeout + 6:
            break

        # You have been quiet too long
        if time.time() - last_sound_at > timeout:
            break

        audio = grab_audio()

        if loudness(audio) >= config.ENERGY_THRESHOLD:
            last_sound_at = time.time()

        finished = open_recognizer.AcceptWaveform(audio)

        if finished:
            result = json.loads(open_recognizer.Result())
            piece = result.get("text", "").strip()
            if piece:
                collected = (collected + " " + piece).strip()
                # You paused and we have words - good enough.
                # Feeling instant beats catching every last syllable.
                break
        else:
            # Show live what it is hearing. Hugely useful while testing.
            partial = json.loads(open_recognizer.PartialResult())
            piece = partial.get("partial", "").strip()
            if piece:
                print("\r  hearing: " + piece[:70].ljust(70), end="", flush=True)

    print("\r" + " " * 82 + "\r", end="")     # wipe the live "hearing:" line
    return collected.strip()
