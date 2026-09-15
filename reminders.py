# ============================================================
#  reminders.py  -  TIMERS & REMINDERS, FULLY OFFLINE
# ============================================================
#  "remind me to check the oven in 15 minutes"
#  "set a timer for 30 seconds"
#  "cancel my timer"
#
#  Pure Python (threading + time math) - zero downloads. The timer
#  keeps running while you keep talking to Buddy, and when it fires
#  you get a spoken announcement plus two friendly beeps.
#
#  ONE HONEST LIMIT: timers live inside the running app. If you tell
#  Buddy "exit" (full close), any running timers die with it - so
#  main.py warns you before closing while a timer is alive.
# ============================================================

import itertools
import re
import threading

import speaker

_UNITS = {
    "second": 1, "seconds": 1, "sec": 1, "secs": 1,
    "minute": 60, "minutes": 60, "min": 60, "mins": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
}

_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# Speech gives us WORDS ("fifteen minutes", "twenty five seconds"),
# typing gives us DIGITS ("15 minutes"). Both must work.
_NUMBER_WORDS = (
    r"\d+|"
    r"(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
    r"(?:\s+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"nineteen|eighteen|seventeen|sixteen|fifteen|fourteen|thirteen|"
    r"twelve|eleven|ten|nine|eight|seven|six|five|four|three|two|one|"
    r"an?"
)

# "in 15 minutes", "for about 2 hours", "in an hour",
# "in fifteen minutes", "in twenty five seconds" ...
_TIME_RE = re.compile(
    r"\b(?:in|for)\s+(?:about\s+)?(" + _NUMBER_WORDS + r")\s*"
    r"(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b")

# Words peeled off when we figure out WHAT you want to be reminded about.
_STRIP_PHRASES = (
    "hey buddy", "please remind me to", "remind me to", "remind me",
    "set a timer for", "set a timer", "set timer for", "set timer",
    "start a timer for", "start a timer", "timer for", "reminder to",
    "reminder", "timer", "please", "reminder for", "alarm for", "alarm",
)

# Safety caps: nothing under 3 seconds (you would miss it) and
# nothing over 12 hours (that is a calendar, not a timer).
MIN_SECONDS = 3
MAX_SECONDS = 12 * 3600

_ids = itertools.count(1)
_lock = threading.Lock()
_active = {}          # id -> {"label": ..., "timer": threading.Timer}


def _to_number(token):
    """'15' -> 15, 'fifteen' -> 15, 'twenty five' -> 25, 'an' -> 1."""
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    if token in ("a", "an"):
        return 1
    parts = token.split()
    if len(parts) == 1:
        number = _ONES.get(parts[0], _TENS.get(parts[0]))
        return number
    tens = _TENS.get(parts[0], 0)
    ones = _ONES.get(parts[1], 0)
    return (tens + ones) or None


def parse_time(text):
    """
    Find "in/for <number> <unit>" in what you said.
    Returns (seconds, the_rest_of_the_sentence) or (None, None).
    """
    match = _TIME_RE.search(text)
    if not match:
        return None, None
    number = _to_number(match.group(1))
    if not number:
        return None, None
    seconds = number * _UNITS[match.group(2).lower()]
    remainder = (text[:match.start()] + " " + text[match.end():]).strip()
    return seconds, remainder


def _label_from(remainder):
    """Turn the leftover words into a human reminder label."""
    label = remainder.lower()
    for phrase in _STRIP_PHRASES:
        label = label.replace(phrase, " ")
    label = " ".join(label.split()).strip(" .,!?")
    return label or "your timer"


def describe_duration(seconds):
    """900 -> '15 minutes', 3600 -> '1 hour', 95 -> '1 minute'."""
    seconds = int(seconds)
    if seconds % 3600 == 0:
        n = seconds // 3600
        return str(n) + (" hour" if n == 1 else " hours")
    if seconds % 60 == 0:
        n = seconds // 60
        return str(n) + (" minute" if n == 1 else " minutes")
    return str(seconds) + (" second" if seconds == 1 else " seconds")


def _beep():
    try:
        import winsound
        winsound.Beep(880, 220)
        winsound.Beep(880, 220)
    except Exception:
        pass


def _fire(timer_id):
    """Runs on the timer's own thread when the countdown hits zero."""
    with _lock:
        entry = _active.pop(timer_id, None)
    label = entry["label"] if entry else "your timer"
    _beep()
    speaker.say("Time is up, boss. " + label + ".")


def set_reminder(text):
    """
    Handle "remind me to ..." / "set a timer for ...".
    Returns the spoken reply.
    """
    seconds, remainder = parse_time(text.lower())
    if seconds is None:
        return ("Tell me the time, like: remind me to check the oven "
                "in fifteen minutes.")
    if seconds < MIN_SECONDS:
        return "That is a bit too quick for me to be useful. Give me at least a few seconds."
    if seconds > MAX_SECONDS:
        return "Twelve hours is my limit. I am a timer, not a calendar, boss."

    label = _label_from(remainder)
    timer_id = next(_ids)
    timer = threading.Timer(seconds, _fire, args=[timer_id])
    timer.daemon = True
    with _lock:
        _active[timer_id] = {"label": label, "timer": timer}
    timer.start()
    return ("Done. I will remind you about " + label + " in " +
            describe_duration(seconds) + ".")


def cancel_timer():
    """Cancel the most recently set timer. Returns the spoken reply."""
    with _lock:
        if not _active:
            return "You have no timers running right now."
        timer_id = max(_active)
        entry = _active.pop(timer_id)
    entry["timer"].cancel()
    return "Cancelled your reminder about " + entry["label"] + "."


def active_count():
    """How many timers are still counting down."""
    with _lock:
        return len(_active)


def status():
    """One friendly sentence about the running timers."""
    with _lock:
        entries = [entry["label"] for entry in _active.values()]
    if not entries:
        return "No timers are running right now."
    return ("You have " + str(len(entries)) + " running: " +
            ", ".join(entries) + ".")
