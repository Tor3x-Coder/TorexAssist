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
#  HOW TO ADD YOUR OWN COMMAND
#  ---------------------------
#  Scroll to the bottom to the APP_LIST and add a line, or copy any
#  block below and change the words. It is meant to be edited.
# ============================================================

import datetime
import os
import subprocess
import sys
import webbrowser

import psutil

import config
import weather


# ============================================================
#  YOUR APPS
# ============================================================
#  Left side  = the word you will say
#  Right side = what actually gets run
#
#  Most Windows 11 apps work with just their name, because Windows
#  has "app execution aliases" set up for them (try it: open a Run
#  box with Win+R and type "notepad").
#
#  If one does not open, replace it with the FULL PATH, for example:
#      "vscode": r"C:\Users\YourName\AppData\Local\Programs\Microsoft VS Code\Code.exe",
#
#  The r before the quote is important on Windows paths.
# ============================================================
APP_LIST = {
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "file explorer": "explorer",
    "explorer": "explorer",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "spotify": "spotify",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "terminal": "wt",
    "command prompt": "cmd",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
    "camera": "start microsoft.windows.camera:",
    "photos": "start ms-photos:",
}


# ============================================================
#  SMALL HELPERS
# ============================================================

def run_hidden(command):
    """
    Run a Windows command without a black box flashing on screen.
    We do not wait for it to finish, so the assistant stays fast.
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

def open_app(spoken_name):
    """Open a program by its spoken name."""
    spoken_name = spoken_name.strip().lower()

    # Remove filler words people naturally say
    for filler in ("the ", "my ", "app ", "program ", "application "):
        spoken_name = spoken_name.replace(filler, "")
    spoken_name = spoken_name.strip()

    if not spoken_name:
        return "Open what? Say the name of the app."

    # Look it up in our list
    target = APP_LIST.get(spoken_name)

    if target is None:
        # Not in the list. Try anyway - Windows often knows the name.
        target = spoken_name.replace(" ", "")

    try:
        if target.startswith("start "):
            run_hidden(target)
        else:
            run_hidden("start " + target)
        return "Opening " + spoken_name + "."
    except Exception as error:
        return ("I could not open " + spoken_name + ". "
                "You may need to add its full path in commands.py.")


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
    return ("You can say things like: open vscode, check battery, "
            "what is the time, what is the date, what is the weather, "
            "mute, volume up, volume down, search google for cats, "
            "play something on youtube, system info, lock the computer, "
            "shut down, restart, sleep, or just ask me anything.")


# ============================================================
#  DANGEROUS COMMANDS  (need a yes/no first)
# ============================================================
#  Reason: the microphone sometimes mis-hears. If it mis-hears and
#  immediately shuts down your laptop, you lose your work.
#  So we ask first. You say "yes" or "no".
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
    # lots of normal sentences.
    if words.startswith("open ") or words.startswith("launch ") \
            or words.startswith("start ") or words.startswith("run "):
        app_name = words
        for prefix in ("open", "launch", "start", "run"):
            app_name = app_name.replace(prefix, "", 1)
        return True, open_app(app_name)

    # ---- Clear the conversation memory ----
    if "forget everything" in words or "clear the conversation" in words \
            or "start over" in words:
        import brain
        brain.forget_everything()
        return True, "Okay, I have forgotten our conversation."

    # ---- Not a command ----
    return False, ""
