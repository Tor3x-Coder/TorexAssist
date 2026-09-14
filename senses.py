# ============================================================
#  senses.py  -  BUDDY'S EYES ON THE PC (read-only awareness)
# ============================================================
#  Small, safe, READ-ONLY tricks that make Buddy feel aware:
#
#     * "what am I looking at?"  -> the active window's title
#     * "read my clipboard"      -> what you last copied
#
#  PRIVACY RULE (non-negotiable):
#  Everything in this file happens ONLY when the user asks, in that
#  exact moment, and the result is only spoken back to THEM on this
#  machine. Nothing is watched in the background, nothing is stored,
#  nothing is sent anywhere. A privacy-first assistant that secretly
#  watches the clipboard is just spyware with a friendly voice.
# ============================================================

import sys
import ctypes


def _user32():
    u32 = ctypes.windll.user32
    # 64-bit safety: pointers must not be truncated to 32-bit ints.
    u32.GetForegroundWindow.restype = ctypes.c_void_p
    u32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    u32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    u32.OpenClipboard.argtypes = [ctypes.c_void_p]
    u32.GetClipboardData.restype = ctypes.c_void_p
    return u32


def active_window_title():
    """The title of whatever window is in front right now. '' if unknown."""
    if sys.platform != "win32":
        return ""
    try:
        u32 = _user32()
        hwnd = u32.GetForegroundWindow()
        length = u32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        u32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""


def clipboard_text():
    """What the user last copied. '' if empty or unavailable."""
    if sys.platform != "win32":
        return ""
    try:
        u32 = _user32()
        k32 = ctypes.windll.kernel32
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]

        CF_UNICODETEXT = 13
        if not u32.OpenClipboard(None):
            return ""
        try:
            handle = u32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            pointer = k32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.wstring_at(pointer).strip()
            finally:
                k32.GlobalUnlock(handle)
        finally:
            u32.CloseClipboard()
    except Exception:
        return ""
