# ============================================================
#  commands.py  -  LOCAL PC COMMANDS
# ============================================================
#  "open vscode", "check battery", "what is the time", "mute"...
#
#  THE MOST IMPORTANT DESIGN DECISION IN THIS WHOLE APP
#  ----------------------------------------------------
#  These commands are matched with SIMPLE WORD MATCHING in Python.
#  They are NEVER sent to the AI.
#
#  Why?
#    * Word matching is instant. The AI takes 2 to 15 seconds.
#    * Word matching is 100% reliable. The AI sometimes guesses wrong.
#    * Word matching works with NO internet. Perfect for blackouts.
#    * The AI can NEVER run a dangerous command by accident, because
#      it has no power here at all. It only ever gets to chat.
#
#  HOW OTHER FILES USE IT
#  ----------------------
#      import commands
#
#      handled, reply = commands.try_command("open vscode")
#
#      handled == True   -> we dealt with it, just speak `reply`
#      handled == False  -> not a command, send it to the AI brain
#
#  OPENING APPS  -  NO MORE HARDCODED LIST
#  ---------------------------------------
#  "open <name>" used to check a fixed APP_LIST. That meant every new
#  app needed a code edit, and anything unknown was blindly run with
#  `start <garbage>` - which pops up empty black command windows.
#
#  Now apps are AUTO-DISCOVERED:
#    1. Every .lnk shortcut in your USER and MACHINE Start Menu is
#       scanned, and its real target is resolved through the Windows
#       Shell (pywin32). The spoken name is simply the shortcut's
#       file name, lowercased ("Google Chrome.lnk" -> "google chrome").
#    2. Every .exe found on your PATH is merged in ("notepad", "calc").
#    3. A tiny floor of Windows system destinations that never appear
#       as shortcuts (Settings, Camera...) is built in.
#    4. The [APPS] section of config.ini can add or override entries -
#       that is the ONLY place you ever need to touch.
#
#  The spoken name is matched FUZZILY (difflib), so small mis-hearings
#  still work. If nothing matches, the assistant SAYS SO. It never
#  runs an unknown name, so no more empty command windows.
#
#  HOW TO ADD YOUR OWN COMMAND
#  ---------------------------
#  Apps   : add a line to the [APPS] section of config.ini.
#  Actions: copy any block in try_command() below and change the words.
# ============================================================

import datetime
import difflib
import os
import re
import shutil
import subprocess
import sys
import webbrowser

import psutil

import config
import weather


# ============================================================
#  APP AUTO-DISCOVERY
# ============================================================
#  The result is one flat dictionary:
#
#      spoken name  ->  { "kind": ..., "path": ..., "target": ..., "args": ... }
#
#  Built lazily the first time it is needed, then cached.
# ============================================================

# A tiny floor of Windows system destinations that NEVER show up as
# Start Menu shortcuts and are not on the PATH. This is NOT an app
# list - just the bare minimum so the most common system places work
# out of the box. Anything else is discovered automatically, and the
# [APPS] section of config.ini overrides everything.
SYSTEM_APPS = {
    "settings": "ms-settings:",
    "control panel": "control",
    "camera": "microsoft.windows.camera:",
    "photos": "ms-photos:",
}

# Shortcut names we refuse to treat as openable apps. Without this,
# "open chrome" could fuzzy-match "Uninstall Google Chrome" and that
# would be a very bad day.
_JUNK_MARKERS = (
    "uninstall", "remove", "readme", "read me", "website",
    "on the web", "safe mode", "repair", "troubleshoot",
)

_apps_cache = None


def _is_junk_name(name):
    """True if this shortcut name is an uninstaller / junk entry."""
    for marker in _JUNK_MARKERS:
        if marker in name:
            return True
    return False


def _start_menu_folders():
    """The two Start Menu folders Windows keeps (user + whole machine)."""
    folders = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        folders.append(os.path.join(
            appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    if programdata:
        folders.append(os.path.join(
            programdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    return [folder for folder in folders if os.path.isdir(folder)]


def _resolve_shortcut(shortcut_path):
    """
    Ask the Windows Shell what a .lnk shortcut actually points at.
    Returns (target, arguments). Both are "" if it cannot be resolved.

    Primary method: pywin32's IShellLink COM object.
    Fallback: the WScript.Shell automation object (also pywin32).
    """
    # ---- Method 1: IShellLink (the proper Shell way) ----
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
        # SLGP_UNCPRIORITY (=2) asks for the UNC-friendly target path.
        # pywin32 has exposed it from `shell` in some versions and from
        # `shellcon` in others, so look in both before giving a default.
        unc_flag = getattr(shellcon, "SLGP_UNCPRIORITY", None)
        if unc_flag is None:
            unc_flag = getattr(shell, "SLGP_UNCPRIORITY", 2)
        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        persist = link.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Load(shortcut_path)
        # GetPath returns (path, WIN32_FIND_DATA); we want the path.
        target = link.GetPath(unc_flag)[0] or ""
        try:
            args = link.GetArguments() or ""
        except Exception:
            args = ""
        return target, args
    except Exception:
        pass

    # ---- Method 2: WScript.Shell fallback ----
    try:
        import win32com.client
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(
            shortcut_path)
        return (shortcut.TargetPath or ""), (shortcut.Arguments or "")
    except Exception:
        return "", ""


def _start_menu_apps():
    """Walk both Start Menus and turn every .lnk into a spoken name."""
    apps = {}
    for folder in _start_menu_folders():
        for root, _dirs, files in os.walk(folder):
            for file_name in files:
                if not file_name.lower().endswith(".lnk"):
                    continue
                name = file_name[:-4].strip().lower()
                if not name or _is_junk_name(name) or name in apps:
                    continue
                full_path = os.path.join(root, file_name)
                target, args = _resolve_shortcut(full_path)
                # Even if the target will not resolve (rare), keep the
                # entry - launch_app() can still "double-click" the .lnk.
                apps[name] = {
                    "kind": "shortcut",
                    "path": full_path,
                    "target": target,
                    "args": args,
                }
    return apps


def _path_apps():
    """Every .exe reachable on the PATH, spoken name = file name."""
    apps = {}
    seen_folders = set()
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder:
            continue
        key = folder.lower()
        if key in seen_folders or not os.path.isdir(folder):
            continue
        seen_folders.add(key)
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        for entry in entries:
            if not entry.lower().endswith(".exe"):
                continue
            name = entry[:-4].strip().lower()
            if not name or _is_junk_name(name) or name in apps:
                continue
            apps[name] = os.path.join(folder, entry)
    return apps


def _store_apps():
    """
    Everything Windows shows under Start -> All apps. This is the ONLY
    way to see Microsoft Store apps (WhatsApp, Snapchat, ...): they do
    NOT leave .lnk shortcuts behind, so the Start Menu scan above is
    blind to them.

    Instead of heavy COM acrobatics we just ask PowerShell politely
    (Get-StartApps). It also lists normal apps, but those are already
    known from the shortcut scan, so they only fill gaps here.
    """
    kwargs = {}
    if sys.platform == "win32":
        # 0x08000000 = CREATE_NO_WINDOW (no black box flash)
        kwargs["creationflags"] = 0x08000000
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
             "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True, timeout=30, **kwargs)
        return _parse_start_apps(result.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def _parse_start_apps(text):
    """Turn the Get-StartApps JSON into spoken-name entries."""
    import json as json_module
    apps = {}
    try:
        data = json_module.loads(text)
    except Exception:
        return apps
    if isinstance(data, dict):     # only ONE app -> JSON gives an object
        data = [data]
    if not isinstance(data, list):
        return apps
    for item in data:
        if not isinstance(item, dict):
            continue
        name = (item.get("Name") or "").strip().lower()
        app_id = (item.get("AppID") or "").strip()
        if not name or not app_id or _is_junk_name(name):
            continue
        if name not in apps:
            apps[name] = {
                "kind": "store",
                "path": app_id,
                "target": "shell:AppsFolder\\" + app_id,
                "args": "",
            }
    return apps


def discover_apps():
    """Build the full spoken-name -> app table. See the header above."""
    apps = {}

    # 1. Start Menu shortcuts (the most human-friendly names).
    apps.update(_start_menu_apps())

    # 2. PATH executables fill the gaps ("notepad", "calc", ...).
    for name, exe_path in _path_apps().items():
        if name not in apps:
            apps[name] = {
                "kind": "exe",
                "path": exe_path,
                "target": exe_path,
                "args": "",
            }

    # 3. The Start menu's full app list - the ONLY place Microsoft
    #    Store apps (WhatsApp, Snapchat, ...) show up.
    for name, entry in _store_apps().items():
        if name not in apps:
            apps[name] = entry

    # 4. The tiny system floor (Settings, Camera, ...).
    for name, target in SYSTEM_APPS.items():
        if name not in apps:
            apps[name] = {
                "kind": "system",
                "path": target,
                "target": target,
                "args": "",
            }

    # 5. config.ini [APPS] overrides - these ALWAYS win.
    for name, target in config.APP_OVERRIDES.items():
        target = target.strip()
        if name and target:
            apps[name.lower()] = {
                "kind": "override",
                "path": target,
                "target": target,
                "args": "",
            }

    return apps


def get_apps(force_refresh=False):
    """The cached app table. Built on first use."""
    global _apps_cache
    if _apps_cache is None or force_refresh:
        _apps_cache = discover_apps()
    return _apps_cache


def warm_up_apps():
    """
    Discover everything ahead of time, so the very first
    "open something" is instant instead of taking a second.
    Called once from main.py inside a background thread.
    """
    try:
        apps = get_apps()
        print("[apps] " + str(len(apps)) +
              " apps discovered - say 'open <name>' to launch one.")
    except Exception as error:
        print("[apps] discovery had a problem: " + str(error))


# ============================================================
#  MATCHING AND LAUNCHING
# ============================================================

_URI_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]{1,}:")

# Abbreviations people say out loud, mapped to what shortcuts are
# actually called. "vs code" would fuzzy-score terribly against
# "visual studio code", so we expand it BEFORE matching.
_ABBREVIATIONS = {
    "vs": "visual studio",
    "ms": "microsoft",
    "win": "windows",
}


def _looks_like_uri(target):
    """True for things like ms-settings: or https://... (not C:\\...)."""
    return bool(_URI_PATTERN.match(target))


def _expand_abbreviations(text):
    """Expand common spoken abbreviations, longest matches first."""
    for short, long_form in sorted(_ABBREVIATIONS.items(),
                                   key=lambda item: -len(item[0])):
        text = re.sub(r"\b" + re.escape(short) + r"\b", long_form, text)
    return text


def resolve_app_name(spoken, apps):
    """
    Match what the user said against the discovered app names.
    Returns the best app name, or None if nothing is close enough.
    """
    if not apps:
        return None

    # 1. Exact hit.
    if spoken in apps:
        return spoken

    # 1b. Abbreviations, expanded to their full form:
    #     "vs code" -> "visual studio code", "ms edge" -> "microsoft edge".
    expanded = _expand_abbreviations(spoken)
    if expanded != spoken and expanded in apps:
        return expanded

    names = list(apps)

    # From here on, match with the expanded form ("vs code" becomes
    # "visual studio code"), which scores far better against the
    # real shortcut names.
    needle = expanded

    # 2. Spaces do not matter to speech: "fire fox" == "firefox".
    needle_squashed = needle.replace(" ", "")
    if needle_squashed != needle:
        for n in names:
            if n.replace(" ", "") == needle_squashed:
                return n

    # 3. Word-boundary containment: "chrome" vs "google chrome",
    #    "code" vs "visual studio code".
    #    Word boundaries matter! Without them "photoshop deluxe"
    #    would contain "photos" and open the wrong app.
    if len(needle) >= 3:
        contained = [
            n for n in names
            if re.search(r"\b" + re.escape(needle) + r"\b", n)
            or re.search(r"\b" + re.escape(n) + r"\b", needle)
        ]
        if len(contained) == 1:
            return contained[0]
        if contained:
            best = difflib.get_close_matches(needle, contained, n=1, cutoff=0.5)
            if best:
                return best[0]

    # 4. Whole-phrase fuzzy: tolerates mis-hearings.
    best = difflib.get_close_matches(needle, names, n=1, cutoff=0.6)
    if best:
        return best[0]

    # 5. Word-by-word fuzzy: catches one mis-heard word inside a long
    #    name ("chome" for the "chrome" in "google chrome"), where the
    #    whole-phrase score is diluted below the cutoff.
    #    The 0.85 bar is deliberate: real mis-hearings ("chome",
    #    "exel", "spotfy") score ~0.89+, while lookalike-but-wrong
    #    pairs like "photoshop" vs "photos" score only ~0.80 and must
    #    NOT open the wrong app.
    best_name, best_score = None, 0.0
    needle_words = needle.split()
    for n in names:
        for name_word in n.split():
            for needle_word in needle_words:
                score = difflib.SequenceMatcher(
                    None, needle_word, name_word).ratio()
                if score > best_score:
                    best_score, best_name = score, n
    if best_name is not None and best_score >= 0.85:
        return best_name

    return None


def launch_app(entry):
    """
    Actually open a discovered app. Never uses `start` and never uses
    a shell, so an unknown name can NEVER spawn an empty command box.
    Raises an exception if it cannot open it (caller speaks the error).
    """
    target = (entry.get("target") or "").strip()
    args = (entry.get("args") or "").strip()

    # A Start-menu-registered app (Microsoft Store apps like WhatsApp
    # or Snapchat): launch it through explorer with its AppsFolder
    # address. This is the known-good trick for Store apps.
    if target.startswith("shell:AppsFolder"):
        os.startfile("explorer.exe", arguments=target)
        return

    # Windows URIs (ms-settings:, ms-photos:, https://...) -
    # hand them straight to the OS.
    if _looks_like_uri(target):
        os.startfile(target)
        return

    # A Start Menu shortcut whose target we could not resolve:
    # just "double-click" the shortcut itself. That always works,
    # including for Microsoft Store apps.
    if entry["kind"] == "shortcut" and (not target or not os.path.isfile(target)):
        os.startfile(entry["path"])
        return

    # A bare command like "code": find the real file on the PATH.
    if not os.path.isabs(target):
        found = shutil.which(target)
        if found:
            target = found
        elif entry["kind"] == "shortcut":
            os.startfile(entry["path"])
            return
        else:
            raise FileNotFoundError(target)
    elif not os.path.isfile(target):
        # The target vanished (app uninstalled). Try the shortcut.
        if entry["kind"] == "shortcut":
            os.startfile(entry["path"])
            return
        raise FileNotFoundError(target)

    if args:
        os.startfile(target, arguments=args)
    else:
        os.startfile(target)


def open_app(spoken_name):
    """Open a program by its spoken name. Never runs an unknown name."""
    spoken_name = spoken_name.strip().lower()

    # Remove filler words people naturally say
    for filler in ("please ", "the ", "my ", "app ", "program ", "application "):
        spoken_name = spoken_name.replace(filler, "")
    spoken_name = " ".join(spoken_name.split())

    if not spoken_name:
        return "Open what? Say the name of the app."

    apps = get_apps()
    name = resolve_app_name(spoken_name, apps)

    if name is None:
        # The old code ran `start <garbage>` here, which popped up
        # empty black command windows. Never again - just say so.
        return "I couldn't find an app called " + spoken_name + "."

    try:
        launch_app(apps[name])
    except Exception:
        return ("I found " + name + " but could not open it. "
                "You can point me at it in config.ini under [APPS].")

    if name == spoken_name:
        return "Opening " + name + "."
    return "Opening " + name + "."


# ============================================================
#  SMALL HELPERS
# ============================================================

def run_hidden(command):
    """
    Run a Windows command without a black box flashing on screen.
    We do not wait for it to finish, so the assistant stays fast.
    Only used for trusted, fixed commands below (shutdown etc) -
    NEVER for user-spoken app names.
    """
    flags = 0
    if sys.platform == "win32":
        # 0x08000000 = CREATE_NO_WINDOW
        flags = 0x08000000
    subprocess.Popen(command, shell=True, creationflags=flags)


def press_media_key(key_code):
    """
    Press a keyboard volume button for you, in code.
    Windows has special key codes for volume, like a real keyboard.
    """
    try:
        import win32api
        win32api.keybd_event(key_code, 0, 0, 0)          # key down
        win32api.keybd_event(key_code, 0, 2, 0)          # key up  (2 = release)
        return True
    except Exception:
        return False


# Windows volume key codes (just numbers Windows understands)
KEY_VOLUME_MUTE = 0xAD
KEY_VOLUME_DOWN = 0xAE
KEY_VOLUME_UP = 0xAF
KEY_MEDIA_NEXT = 0xB0
KEY_MEDIA_PLAY_PAUSE = 0xB3


# ============================================================
#  THE INDIVIDUAL COMMANDS
# ============================================================

def check_battery():
    """Read the laptop battery - works offline, no AI needed."""
    battery = psutil.sensors_battery()

    if battery is None:
        return "This computer does not have a battery. It is a desktop."

    percent = round(battery.percent)
    plugged = battery.power_plugged

    if plugged:
        state = "and it is plugged in and charging."
    else:
        # How long is left? Windows gives it in seconds.
        seconds_left = battery.secsleft
        if seconds_left is not None and seconds_left > 0 and seconds_left < 999999:
            hours = int(seconds_left // 3600)
            minutes = int((seconds_left % 3600) // 60)
            state = ("and you have about " + str(hours) + " hours " +
                     str(minutes) + " minutes left.")
        else:
            state = "and it is not charging."

    return "Battery is at " + str(percent) + " percent, " + state


def what_time():
    """Current time in plain words."""
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute

    if hour >= 12:
        period = "PM"
        hour = hour - 12
        if hour == 0:
            hour = 12
    else:
        period = "AM"
        if hour == 0:
            hour = 12

    if minute == 0:
        return "It is " + str(hour) + " " + period + " exactly."
    return "It is " + str(hour) + ":" + str(minute).zfill(2) + " " + period + "."


def what_date():
    """Today's date in plain words."""
    now = datetime.datetime.now()
    return "Today is " + now.strftime("%A, %d %B %Y") + "."


def do_weather():
    """Get REAL weather from the free weather service (see weather.py)."""
    return weather.get_weather_text()


def search_web(words):
    """Open a Google search in your normal browser."""
    words = words.strip()
    if not words:
        return "What should I search for?"
    webbrowser.open("https://www.google.com/search?q=" + words.replace(" ", "+"))
    return "Searching Google for " + words + "."


def open_youtube(words):
    """Open YouTube, or search YouTube if you said what to look for."""
    words = words.strip()
    if not words:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube."
    webbrowser.open("https://www.youtube.com/results?search_query=" + words.replace(" ", "+"))
    return "Searching YouTube for " + words + "."


def my_ip():
    """Show this computer's local IP address."""
    import socket
    try:
        address = socket.gethostbyname(socket.gethostname())
        return "Your local IP address is " + address + "."
    except Exception:
        return "I could not find your IP address."


def system_info():
    """Quick summary of the machine."""
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    return ("You are using " + str(round(memory.percent)) +
            " percent of your memory, and the processor is at " +
            str(round(cpu)) + " percent.")


def list_commands():
    """Tell the user what they can say."""
    text = ("You can say things like: open, plus almost any app name, "
            "check battery, what is the time, what is the date, "
            "what is the weather, mute, volume up, volume down, "
            "search google for cats, play something on youtube, "
            "system info, lock the computer, shut down, restart, sleep, "
            "or just ask me anything.")
    if config.FOLLOW_UP_WINDOW > 0:
        text += (" Also, after I answer you, just keep talking - for about " +
                 str(config.FOLLOW_UP_WINDOW) +
                 " seconds you do not need the wake word again.")
    return text


# ============================================================
#  POWER COMMANDS  -  LIFECYCLE, KNOW THE DIFFERENCE
# ============================================================
#   exit / quit / "done with you" / "go offline"   (main.py)
#        -> closes TOREX ASSIST ITSELF. Full close: the microphone
#           is released and the program ends.
#
#   sleep  ("go to sleep", "sleep mode")
#        -> the MACHINE sleeps. The assistant simply pauses with it
#           and carries on when the laptop wakes.
#
#   lock  ("lock the computer")
#        -> locks the Windows screen. The assistant KEEPS LISTENING
#           on the lock screen, so you can call it right back.
#
#   shut down / restart
#        -> machine-level power actions. The assistant dies (or the
#           machine reboots) - so we always confirm first, because a
#           microphone mis-hear should never kill your work.
#
#  The dangerous ones below need a yes/no first. Reason: the
#  microphone sometimes mis-hears. If it mis-hears and immediately
#  shuts down your laptop, you lose your work. So we ask first.
# ============================================================

# Holds the command we are waiting for permission to run.
pending_action = None


def dangerous_shutdown():
    run_hidden("shutdown /s /t 5")
    return "Shutting down in 5 seconds."


def dangerous_restart():
    run_hidden("shutdown /r /t 5")
    return "Restarting in 5 seconds."


def dangerous_sleep():
    run_hidden("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Going to sleep."


def dangerous_lock():
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Locking the computer."
    except Exception:
        run_hidden("rundll32.exe user32.dll,LockWorkStation")
        return "Locking the computer."


def cancel_pending():
    """Forget the dangerous command we were holding."""
    global pending_action
    pending_action = None
    return "Okay, cancelled."


# ============================================================
#  THE ROUTER  -  reads what you said and picks the right action
# ============================================================
#  It goes top to bottom and uses the FIRST match.
#  Order matters: "open youtube" must be checked before plain "open".
# ============================================================

def try_command(text):
    """
    Returns two things:
        True,  "the reply"   -> this WAS a command, speak the reply
        False, ""            -> not a command, send it to the AI
    """
    global pending_action

    # ---- FIRST: are we answering a yes/no from a dangerous command? ----
    if pending_action is not None:
        said_yes = ("yes" in text) or ("yeah" in text) or ("do it" in text) or ("sure" in text)
        said_no = ("no" in text) or ("cancel" in text) or ("never mind" in text) or ("stop" in text)

        if said_yes:
            action = pending_action
            pending_action = None
            return True, action()

        if said_no:
            return True, cancel_pending()

        # They said something else. Drop it and let the AI handle it.
        pending_action = None

    words = text.lower().strip()

    if not words:
        return False, ""

    # ---- Help ----
    if "what can you do" in words or "help me" in words or words == "help" \
            or "list commands" in words or "what are your commands" in words:
        return True, list_commands()

    # ---- Time and date ----
    if "what is the time" in words or "what time is it" in words \
            or "tell me the time" in words or words == "time":
        return True, what_time()

    if "what is the date" in words or "what day is it" in words \
            or "today's date" in words or words == "date":
        return True, what_date()

    # ---- Battery ----
    if "battery" in words:
        return True, check_battery()

    # ---- Weather ----
    # Note: we get REAL numbers. Free Gemini cannot browse the web,
    # so it would just make the weather up. See weather.py.
    if "weather" in words or "how hot is it" in words or "temperature" in words:
        return True, do_weather()

    # ---- Volume ----
    if "mute" in words or "unmute" in words or "quiet" in words or "shut up" in words:
        if press_media_key(KEY_VOLUME_MUTE):
            return True, "Toggling mute."
        return True, "I could not control the volume on this machine."

    if "volume up" in words or "louder" in words or "increase volume" in words:
        if press_media_key(KEY_VOLUME_UP):
            return True, "Volume up."
        return True, "I could not control the volume on this machine."

    if "volume down" in words or "lower the volume" in words or "quieter" in words:
        if press_media_key(KEY_VOLUME_DOWN):
            return True, "Volume down."
        return True, "I could not control the volume on this machine."

    # ---- System info ----
    if "system info" in words or "how is my computer" in words \
            or "memory usage" in words or "cpu usage" in words:
        return True, system_info()

    if "my ip" in words or "ip address" in words:
        return True, my_ip()

    # ---- Internet search ----
    if words.startswith("search google for") or words.startswith("search for") \
            or words.startswith("google "):
        search_words = words
        for prefix in ("search google for", "search for", "google"):
            search_words = search_words.replace(prefix, "", 1)
        return True, search_web(search_words)

    if "youtube" in words:
        video_words = words
        for prefix in ("play", "search", "open", "on", "youtube", "for"):
            video_words = video_words.replace(prefix, "", 1)
        return True, open_youtube(video_words)

    # ---- Clear the conversation memory ----
    # Checked BEFORE the "open" block, because "start over" must not
    # be treated as "open an app called over".
    if "forget everything" in words or "clear the conversation" in words \
            or "start over" in words:
        import brain
        brain.forget_everything()
        return True, "Okay, I have forgotten our conversation."

    # ---- DANGEROUS ones (ask first) ----
    if "shut down" in words or "shutdown" in words or "power off" in words \
            or "turn off the computer" in words or "turn off the laptop" in words:
        if config.CONFIRM_DANGEROUS:
            pending_action = dangerous_shutdown
            return True, "Are you sure you want to shut down? Say yes or no."
        return True, dangerous_shutdown()

    if "restart" in words or "reboot" in words:
        if config.CONFIRM_DANGEROUS:
            pending_action = dangerous_restart
            return True, "Are you sure you want to restart? Say yes or no."
        return True, dangerous_restart()

    if "go to sleep" in words or "sleep the computer" in words or "sleep mode" in words:
        if config.CONFIRM_DANGEROUS:
            pending_action = dangerous_sleep
            return True, "Are you sure you want the computer to sleep? Say yes or no."
        return True, dangerous_sleep()

    if "lock the computer" in words or "lock the laptop" in words or words == "lock":
        return True, dangerous_lock()

    # ---- OPEN AN APP ----
    # Checked near the bottom on purpose, because "open" appears in
    # lots of normal sentences. Apps are auto-discovered from your
    # Start Menu and PATH - see the top of this file. No hardcoding.
    if words.startswith("open ") or words.startswith("launch ") \
            or words.startswith("start ") or words.startswith("run "):
        app_name = words
        for prefix in ("open", "launch", "start", "run"):
            app_name = app_name.replace(prefix, "", 1)
        return True, open_app(app_name)

    # ---- Not a command ----
    return False, ""
