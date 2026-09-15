# ============================================================
#  memory_store.py  -  BUDDY'S PERMANENT MEMORY
# ============================================================
#  "remember that john's birthday is october 5th"
#  "what is john's birthday?"   ->  "October 5th."
#
#  The conversation memory (brain.py) only lives while the app is
#  running. THIS memory lives forever in a tiny file called
#  memory.db (SQLite - built into Python, zero downloads, ~0 MB RAM).
#
#  PRIVACY, AS ALWAYS
#  ------------------
#  Everything you tell Buddy is stored ONLY in memory.db inside your
#  own app folder, on your own disk. It is never sent anywhere.
#  The file is git-ignored, so it can never leak into the code repo.
#
#  HOW A FACT IS STORED
#  --------------------
#      remember that my car plate is abc 123
#          key   = "my car plate"      (the part before "is")
#          value = "abc 123"           (the part after "is")
#  Facts without an "is" ("remember to buy milk") are stored whole.
#  Storing a key that already exists just UPDATES it - no duplicates.
#
#  HOW RECALL WORKS
#  ----------------
#  Fuzzy matching (difflib), exactly like app launching: a small
#  mis-hear ("john birthday" instead of "john's birthday") still
#  finds the fact. A fact is only spoken if it scores high enough,
#  otherwise the question falls through to the AI brain as normal.
# ============================================================

import difflib
import os
import re
import sqlite3

# memory.db sits NEXT TO the code, inside the app folder.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "memory.db")

# How close your words must be to a stored key before we are sure
# you mean that fact. Same philosophy as app launching: high enough
# that lookalikes never win.
RECALL_CUTOFF = 0.62
FORGET_CUTOFF = 0.72

_PUNCT = re.compile(r"[^\w\s]")


def _connection():
    """Open the memory file (creating it the first time)."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS facts ("
        " key TEXT PRIMARY KEY,"
        " value TEXT NOT NULL,"
        " created TEXT NOT NULL)")
    return connection


def _normalize(text):
    """Lowercase, strip punctuation, squash spaces - for matching."""
    text = _PUNCT.sub(" ", text.lower())
    return " ".join(text.split())


def remember(key, value):
    """Store one fact. An existing key gets updated, never duplicated."""
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return False
    connection = _connection()
    try:
        import datetime
        connection.execute(
            "INSERT OR REPLACE INTO facts (key, value, created) "
            "VALUES (?, ?, ?)",
            (key, value, datetime.datetime.now().isoformat(timespec="seconds")))
        connection.commit()
    finally:
        connection.close()
    return True


def best_match(query, cutoff):
    """
    Find the stored fact closest to `query`.
    Returns (key, value, score) or None. Exact matches always win,
    even in one-word cases where fuzzy math gets shy.
    """
    query = _normalize(query)
    if not query:
        return None
    connection = _connection()
    try:
        rows = connection.execute("SELECT key, value FROM facts").fetchall()
    finally:
        connection.close()
    best = None
    for key, value in rows:
        score = difflib.SequenceMatcher(
            None, query, _normalize(key)).ratio()
        if best is None or score > best[2]:
            best = (key, value, score)
    if best is not None and _normalize(best[0]) == query:
        best = (best[0], best[1], 1.0)
    if best is not None and best[2] >= cutoff:
        return best
    return None


def recall(query):
    """Return the value of the best-matching fact, or None."""
    hit = best_match(query, RECALL_CUTOFF)
    return hit[1] if hit else None


def forget(query):
    """Delete the best-matching fact. Returns its key, or None."""
    hit = best_match(query, FORGET_CUTOFF)
    if hit is None:
        return None
    connection = _connection()
    try:
        connection.execute("DELETE FROM facts WHERE key = ?", (hit[0],))
        connection.commit()
    finally:
        connection.close()
    return hit[0]


def forget_everything():
    """Wipe every stored fact. Returns how many were deleted."""
    connection = _connection()
    try:
        count = connection.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        connection.execute("DELETE FROM facts")
        connection.commit()
    finally:
        connection.close()
    return count


def all_facts(limit=8):
    """The newest facts, as [(key, value), ...] for the summary."""
    connection = _connection()
    try:
        rows = connection.execute(
            "SELECT key, value FROM facts ORDER BY created DESC LIMIT ?",
            (limit,)).fetchall()
    finally:
        connection.close()
    return rows


def count_facts():
    """How many facts Buddy currently holds."""
    connection = _connection()
    try:
        return connection.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    finally:
        connection.close()
