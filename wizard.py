# ============================================================
#  wizard.py  -  THE FIRST-RUN WIZARD
# ============================================================
#  The very first time Buddy runs on a fresh laptop (no config.ini
#  yet), it should not just start - it should INTRODUCE ITSELF:
#
#     1. Ask your name out loud and write it into config.ini.
#     2. Run a tiny MIC SELF-TEST: you read one sentence, we grade
#        how clearly you came in. Pass -> "your mic is good".
#        Fail -> "a cheap headset mic would transform me" (the app
#        still works either way - advice, not a wall).
#
#  It only runs when config.ini does not exist. Existing users are
#  never bothered. After it finishes, main.py restarts the app so
#  every module reads the fresh settings cleanly.
# ============================================================

import os
import shutil
import time

import config


def first_run_needed():
    """True only when there is no config.ini at all (brand-new install)."""
    return not os.path.exists(config.CONFIG_FILE)


# ---------------------------------------------------------------
#  NAME CAPTURE
# ---------------------------------------------------------------
_NAME_FILLERS = (
    "my name is ", "name is ", "i am ", "im ", "i'm ",
    "it is ", "its ", "it's ", "call me ", "this is ",
)


def clean_name(heard):
    """Turn 'my name is torex' into 'Torex'. '' if nothing usable."""
    h = (heard or "").strip().lower()
    if not h:
        return ""
    for filler in _NAME_FILLERS:
        if h.startswith(filler):
            h = h[len(filler):]
            break
    # Keep letters and a few safe characters only.
    h = "".join(ch for ch in h if ch.isalpha() or ch in " '-")
    name = " ".join(h.split()[:2]).strip()     # first two words max
    if not name:
        return ""
    return name[:24].capitalize()


# ---------------------------------------------------------------
#  MIC SELF-TEST  (the quality gate)
# ---------------------------------------------------------------
def mic_test():
    """
    The user reads one sentence; we measure how much of the time we
    actually heard them and how loud the peak was. Returns True/False.
    """
    import speaker
    import ears

    speaker.say("Quick microphone check. Please read this out loud: "
                "the quick brown fox jumps over the lazy dog.")
    time.sleep(0.5)
    ears.drain_queue()

    loud_chunks = 0
    total = 0
    peak = 0
    started_at = time.time()
    while time.time() - started_at < 6:
        audio = ears.grab_audio()
        level = ears.loudness(audio)
        total += 1
        if level >= config.ENERGY_THRESHOLD:
            loud_chunks += 1
        if level > peak:
            peak = level

    if total == 0:
        return False
    speech_ratio = loud_chunks / total
    passed = speech_ratio >= 0.35 and peak >= config.ENERGY_THRESHOLD * 2
    return passed


# ---------------------------------------------------------------
#  WRITE THE SETTINGS FILE
# ---------------------------------------------------------------
def _write_config(name):
    """
    Create config.ini from the commented example (so the new user
    keeps all the friendly comments), then stamp their name in.
    """
    example = os.path.join(config.BASE_DIR, "config.example.ini")
    shutil.copyfile(example, config.CONFIG_FILE)

    with open(config.CONFIG_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # Only the [USER] line is exactly "name = Torex"; the [APP] line is
    # "name = Buddy", so this cannot touch it.
    text = text.replace("name = Torex\n", "name = " + name + "\n", 1)

    with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------
#  THE WIZARD ITSELF
# ---------------------------------------------------------------
def run():
    """Talk the new user through name + mic test. Called once, ever."""
    import speaker
    import ears

    print("=" * 64)
    print("   FIRST RUN - let's get to know each other")
    print("=" * 64)

    speaker.say("Hey! I am " + config.APP_NAME +
                ". I don't think we have met. What is your name? "
                "Just say it after I go quiet.")

    heard = ears.listen_for_command(timeout=10)
    name = clean_name(heard)
    if not name:
        name = "friend"
        print("[wizard] Did not catch a name - using 'friend'. "
              "You can change it in config.ini later.")
    else:
        print("[wizard] Hello, " + name + "!")

    passed = mic_test()
    if passed:
        speaker.say("Nice, " + name + ", your microphone is good to go. "
                    "I saved everything. See you in a second!")
        print("[wizard] Mic test: PASSED.")
    else:
        speaker.say("Okay " + name + ", your microphone is a little quiet. "
                    "I still work, but any cheap headset mic would "
                    "transform how well I hear you. I saved everything. "
                    "See you in a second!")
        print("[wizard] Mic test: weak signal. Advised a headset mic.")

    _write_config(name)
    print("[wizard] config.ini created with name = " + name)
