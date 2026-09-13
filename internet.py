# ============================================================
#  internet.py  -  CHECKS IF YOU HAVE INTERNET (IN THE BACKGROUND)
# ============================================================
#  Other files just ask:
#
#       import internet
#       if internet.is_online():
#           ... use the cloud AI ...
#
#  WHY WE DO IT THIS WAY
#  ---------------------
#  Checking the internet properly is trickier than it looks:
#
#   * A "ping" test fails on many networks that block pings.
#     It would say "offline" while your internet is fine.
#
#   * A "is wifi connected" test fails at hotels, airports and
#     hotspots where you must sign in on a page first.
#     It would say "online" but every real request fails.
#
#  The only honest test: actually try to reach a real web address.
#
#  We do that quietly in a background thread every few seconds so
#  the main app never freezes waiting for it.
# ============================================================

import threading
import time

import requests


# This address belongs to Google. It is tiny (no content at all)
# and it exists purely for connectivity tests like this one.
TEST_ADDRESS = "https://www.gstatic.com/generate_204"

# How often to re-check, in seconds. 10 is a good balance:
# fast enough to notice a blackout, light enough to not waste battery.
CHECK_EVERY_SECONDS = 10

# How long to wait before giving up on one test.
# Short on purpose. If it takes more than 4 seconds, treat it as
# "not usable" because an AI call would be painfully slow anyway.
TIMEOUT_SECONDS = 4


# The remembered answer. Other files read this instantly.
_online = False

# So we only start the background thread once.
_started = False


def _do_one_check():
    """One single internet test. Returns True or False."""
    try:
        answer = requests.get(TEST_ADDRESS, timeout=TIMEOUT_SECONDS)
        # That address always replies with code 204 and no content.
        # If we get ANY reply from the internet, we are online.
        return answer.status_code in (200, 204)
    except Exception:
        # No internet, timeout, DNS problem, blocked... all the same:
        # we cannot reach the outside world right now.
        return False


def _background_worker():
    """This loop runs forever in its own thread."""
    global _online

    while True:
        result = _do_one_check()

        # Only print when the situation CHANGES, so your console
        # does not fill up with noise.
        if result != _online:
            if result:
                print("[internet] Back online.  -> using Gemini (cloud brain)")
            else:
                print("[internet] No internet.  -> using Ollama (offline brain)")

        _online = result
        time.sleep(CHECK_EVERY_SECONDS)


def start():
    """Start the background checker. Call this once when the app starts."""
    global _started

    if _started:
        return

    # Do one immediate check so we have an answer right away,
    # instead of waiting 10 seconds for the first result.
    global _online
    _online = _do_one_check()

    thread = threading.Thread(target=_background_worker)
    thread.daemon = True   # means: dies automatically when the app closes
    thread.start()

    _started = True

    if _online:
        print("[internet] Online. Gemini is available.")
    else:
        print("[internet] Offline. Ollama will be used.")


def is_online():
    """The question everyone asks. Instant answer, never blocks."""
    return _online
