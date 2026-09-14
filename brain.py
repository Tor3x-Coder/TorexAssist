# ============================================================
#  brain.py  -  THE TWO BRAINS, AND THE SMART SWITCH
# ============================================================
#  This is the heart of the app.
#
#       BRAIN 1 (ONLINE)  = Google Gemini   -> smart, knows things
#       BRAIN 2 (OFFLINE) = Ollama llama3.2 -> lives inside your laptop
#
#  THE ONE RULE THAT MATTERS
#  -------------------------
#  We do NOT trust the internet check. We simply TRY Gemini first.
#  If it fails for ANY reason at all --
#
#       no internet / blackout / slow network / wifi needs a login page
#       free daily limit reached / wrong API key / Google is down
#
#  -- we instantly and silently fall back to Ollama.
#
#  The user never sees an error. The assistant just answers, maybe
#  a little less cleverly. That is the whole trick.
#
#  Other files use it like this:
#
#       import brain
#       reply = brain.ask("tell me a joke")
#       print(reply)
# ============================================================

import subprocess
import sys
import time

import requests

import config
import internet


# ------------------------------------------------------------
#  PERSONALITY
# ------------------------------------------------------------
#  This is the instruction we send before every conversation.
#  Keep answers SHORT because they will be read out loud by a
#  computer voice. A 200 word essay read by a robot is torture.
# ------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are TorexAssist, a friendly voice assistant on a Windows laptop. "
    "The user's name is " + config.USER_NAME + ". "
    "You are warm, casual and a little bit like a brother or close friend. "
    "CRITICAL: your answer will be SPOKEN OUT LOUD by a computer voice, "
    "so keep it to one or two short sentences. "
    "Never use markdown, never use bullet points, never use emoji, "
    "never write asterisks or hashtags. Plain spoken words only. "
    "Never spell out a long list. If you do not know something, say so honestly."
)


# The memory of the current conversation, newest at the end.
# Both brains share this, so switching between them mid-chat still
# feels like one continuous conversation.
#
# FORMAT: plain dicts,  {"role": "user" | "assistant", "content": ...}
# That is exactly what Ollama wants. Gemini is pickier - its pydantic
# models reject plain dicts - so ask_gemini() converts this list into
# google.genai types.Content objects on the fly. One memory, two
# dialects.
history = []


def remember(role, text):
    """Add one line to the conversation memory."""
    history.append({"role": role, "content": text})

    # Keep only the last 10 exchanges. Without this the memory grows
    # forever and every request gets slower and slower.
    while len(history) > 20:
        history.pop(0)


def forget_everything():
    """Wipe the memory. Used when the user says 'forget' or restarts."""
    history.clear()


# ============================================================
#  BRAIN 1  -  GOOGLE GEMINI  (ONLINE)
# ============================================================

client = None


def _get_gemini_client():
    """
    Connect to Gemini. We do this lazily (only when first needed)
    so the app still starts fine if the library is missing.
    """
    global client

    if client is not None:
        return client

    # No key pasted in config.ini? Do not even try.
    if not config.gemini_ready():
        raise Exception("No Gemini API key in config.ini")

    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    return client


def ask_gemini(user_text):
    """
    Send the question to Gemini and return its answer.
    If anything at all goes wrong, this raises an error and the
    caller falls back to Ollama.

    Note: the user's line is already in `history` - ask() put it there.
    We do NOT add it again here, otherwise a Gemini failure would
    leave the question saved twice and the offline brain would see
    you asking the same thing back to back.

    HISTORY FORMAT: the SDK's pydantic models reject plain
    {"role": ..., "content": ...} dicts. The conversation must be
    sent as google.genai types.Content objects - a role plus parts.
    We translate our simple memory into that shape right here.
    """
    gemini = _get_gemini_client()

    from google.genai import types

    contents = []
    for item in history:
        # Our memory says "assistant"; Gemini calls that role "model".
        role = "user" if item["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            # text= as a keyword: works on both old and new SDK versions.
            parts=[types.Part.from_text(text=item["content"])],
        ))

    # Gemini wants the first line to come from the user. If the memory
    # was trimmed so that a model line ended up first, drop those.
    while contents and contents[0].role != "user":
        contents.pop(0)

    response = gemini.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=contents,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "max_output_tokens": 220,       # short on purpose
            "temperature": 0.7,             # 0 = robotic, 1 = creative
        },
    )

    reply = (response.text or "").strip()
    if not reply:
        raise Exception("Gemini returned an empty answer")

    # "assistant" (not "model") so both brains use the same role word.
    remember("assistant", reply)
    return reply


# ============================================================
#  BRAIN 2  -  OLLAMA  (OFFLINE, INSIDE YOUR LAPTOP)
# ============================================================

ollama_checked = False


def _ollama_program_path():
    """Where Ollama normally lives on Windows."""
    import os
    normal_place = os.path.join(
        os.path.expanduser("~"), "AppData", "Local", "Programs",
        "Ollama", "ollama.exe"
    )
    if os.path.exists(normal_place):
        return normal_place
    # Maybe it is on the PATH, so just try the plain name.
    return "ollama"


def make_sure_ollama_is_running():
    """
    Ollama is a small background server. If it is not running, our
    offline brain cannot answer. So we check, and start it quietly
    if needed.

    We only do this check once per app run.
    """
    global ollama_checked

    if ollama_checked:
        return

    # Is it already awake?
    try:
        requests.get(config.OLLAMA_ADDRESS, timeout=2)
        ollama_checked = True
        return
    except Exception:
        pass

    # Not awake. Start it in the background with no window popping up.
    print("[ollama] Not running. Starting it quietly...")
    try:
        creation_flags = 0
        if sys.platform == "win32":
            # This flag means: do not show a black command window.
            creation_flags = 0x08000000
        subprocess.Popen(
            [_ollama_program_path(), "serve"],
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as error:
        print("[ollama] Could not start it: " + str(error))
        print("[ollama] Please install Ollama, or start it manually.")
        ollama_checked = True
        return

    # Wait up to 20 seconds for it to wake up.
    for _ in range(20):
        time.sleep(1)
        try:
            requests.get(config.OLLAMA_ADDRESS, timeout=2)
            print("[ollama] Running now.")
            break
        except Exception:
            continue

    ollama_checked = True


def ask_ollama(user_text):
    """
    Send the question to the local model and return its answer.
    This works with NO internet at all.
    """
    make_sure_ollama_is_running()

    # Again: the user's line is already in `history`, we do not re-add it.
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "stream": False,     # False = wait and give us the whole answer
    }

    answer = requests.post(
        config.OLLAMA_ADDRESS + "/api/chat",
        json=payload,
        # The FIRST question after the laptop has been idle is slow,
        # because Ollama has to load the model off the disk.
        # That can take 5 to 20 seconds. This timeout allows for it.
        timeout=120,
    )
    answer.raise_for_status()

    data = answer.json()
    reply = data["message"]["content"].strip()
    if not reply:
        raise Exception("Ollama returned an empty answer")

    remember("assistant", reply)
    return reply


# ============================================================
#  THE SMART SWITCH  -  the function the rest of the app calls
# ============================================================

def ask(user_text):
    """
    Give me a question, get an answer back. You do not need to know
    or care which brain produced it.

    GUARANTEE: this always returns a non-empty sentence, and it
    never raises. Whatever goes wrong, the assistant says something
    sensible instead of freezing or crashing.
    """
    user_text = user_text.strip()
    if not user_text:
        return "I did not catch that."

    # Save your question to memory EXACTLY ONCE, here, before we try
    # any brain. That way both brains see the same conversation, and
    # a failed Gemini attempt cannot duplicate your question.
    remember("user", user_text)

    # ---- Try the online brain first ----
    # Only bother if (a) we think we have internet and (b) a key exists.
    if internet.is_online() and config.gemini_ready():
        try:
            reply = (ask_gemini(user_text) or "").strip()

            # Double-check it actually gave us words. An AI service can
            # reply with an empty string when it is filtered, overloaded
            # or having a bad day. Without this check the assistant
            # would wake up, listen, and then say NOTHING AT ALL -
            # which looks exactly like a frozen app.
            if reply:
                print("[brain] answered by Gemini (online)")
                return reply

            print("[brain] Gemini replied with nothing usable.")
        except Exception as error:
            # No drama. No error shown to the user. Just note it
            # in the console for you, and quietly switch brains.
            print("[brain] Gemini failed: " + str(error))

        print("[brain] Switching to Ollama (offline).")

    # ---- Fall back to the offline brain ----
    try:
        reply = (ask_ollama(user_text) or "").strip()
        if reply:
            print("[brain] answered by Ollama (offline)")
            return reply
        print("[brain] Ollama replied with nothing usable.")
    except Exception as error:
        print("[brain] Ollama failed too: " + str(error))

    # ---- Last resort: never crash, always say something ----
    return ("Sorry " + config.USER_NAME +
            ", both of my brains are down right now. "
            "Please check that Ollama is installed and running.")
