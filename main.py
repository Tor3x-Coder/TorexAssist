# ============================================================
#  main.py  -  TOREX ASSIST  -  START HERE
# ============================================================
#  Run it with:      python main.py
#
#  WHAT HAPPENS
#    1. It checks your internet (quietly, in the background).
#    2. It opens the microphone and starts listening.
#    3. It says hello.
#    4. It waits to hear the wake word.
#    5. When it hears it:
#         - if it is a PC command  -> run it instantly (no AI)
#         - if it is a question    -> ask the AI
#                                    Gemini first, Ollama if that fails
#    6. Back to step 4. Forever.
#
#  TO STOP IT:  say "exit", or press Ctrl + C in the window.
# ============================================================

import datetime
import sys
import time

import config
import brain
import commands
import ears
import internet
import speaker


# Words that mean "goodbye, shut yourself down"
EXIT_WORDS = ["exit", "quit", "shut yourself down", "go to sleep now", "goodbye assistant"]


# ------------------------------------------------------------
#  The greeting. Changes with the time of day, like you asked.
#  Edit these lines to say whatever you like.
# ------------------------------------------------------------
def make_greeting():
    hour = datetime.datetime.now().hour
    name = config.USER_NAME

    if 5 <= hour < 12:
        greeting = "Good morning " + name + ". Welcome back, brother."
    elif 12 <= hour < 17:
        greeting = "Good afternoon " + name + ". Good to see you again."
    elif 17 <= hour < 22:
        greeting = "Good evening " + name + ". Welcome back, brother."
    else:
        greeting = "Hello " + name + ". It is late, but I am here."

    # Tell the user which brain is ready, so there are no surprises.
    if internet.is_online() and config.gemini_ready():
        status = "I am online, so I will use the cloud brain."
    elif internet.is_online():
        status = "I am online, but you have not added a Gemini key yet, so I will use the local brain."
    else:
        status = "There is no internet right now, so I am using the offline brain inside this laptop."

    return greeting + " " + status


# ------------------------------------------------------------
#  A tiny beep so you know it is thinking.
#  This matters because the offline brain can take several seconds
#  on the first question, and silence feels like a crash.
# ------------------------------------------------------------
def thinking_beep():
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(880, 90)      # frequency, milliseconds
    except Exception:
        pass


# ------------------------------------------------------------
#  Handle one thing the user said
# ------------------------------------------------------------
def handle(heard_text):
    """Returns True to keep running, False to exit."""
    print("You said: " + heard_text)

    # 1. Does the user want to quit?
    lowered = heard_text.lower()
    for exit_word in EXIT_WORDS:
        if exit_word in lowered:
            speaker.say("Alright " + config.USER_NAME + ", I am going offline. See you soon.")
            return False

    # 2. Is it a PC command? Check this FIRST, always.
    #    Commands never go to the AI. They are instant and they work
    #    with no internet at all. See commands.py for why.
    was_command, reply = commands.try_command(heard_text)

    if was_command:
        speaker.say(reply)
        return True

    # 3. Not a command. This is a real question - send it to the brain.
    #    brain.ask() tries Gemini, and silently falls back to Ollama
    #    if Gemini fails for any reason. You never see an error.
    thinking_beep()
    answer = brain.ask(heard_text)
    speaker.say(answer)
    return True


# ------------------------------------------------------------
#  THE MAIN PROGRAM
# ------------------------------------------------------------
def main():
    # A nicer window title
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("TorexAssist")
    except Exception:
        pass

    print("=" * 64)
    print("   T O R E X   A S S I S T")
    print("=" * 64)
    print("  Wake word  : " + config.WAKE_WORD)
    print("  Your name  : " + config.USER_NAME)
    print("  Cloud brain: " + (config.GEMINI_MODEL if config.gemini_ready() else "(no API key yet)"))
    print("  Local brain: Ollama " + config.OLLAMA_MODEL)
    print("=" * 64)

    # ---- Step 1: start the background internet checker ----
    internet.start()

    # ---- Step 2: make sure the offline brain is awake ----
    # We do this at startup rather than during a blackout, so that the
    # first offline question is not slow.
    brain.make_sure_ollama_is_running()

    # ---- Step 3: open the ears ----
    if not ears.setup():
        print("\nCould not start listening. Read the message above and try again.")
        input("\nPress Enter to close...")
        return

    # ---- Step 4: say hello ----
    # Small pause so the Windows sound system is fully awake first.
    # Without this, the very first greeting is sometimes silent.
    time.sleep(1.0)
    speaker.say(make_greeting())

    print("\nReady. Say '" + config.WAKE_WORD + "' to talk to me.")
    print("Say 'what can you do' for the command list.")
    print("Say 'exit' or press Ctrl+C to quit.\n")

    # ---- Step 5: the forever loop ----
    while True:
        try:
            # Wait here until the wake word is heard.
            phrase = ears.wait_for_wake_word()
            print("\n>>> Heard: " + phrase)

            # Case A: it was an instant command ("check battery"),
            # not the wake word. Just do it, no extra listening needed.
            if phrase not in [w.lower() for w in ears.WAKE_WORDS]:
                keep_going = handle(phrase)
                if not keep_going:
                    break
                continue

            # Case B: it was the wake word. Now listen properly.
            speaker.say("Yes?")
            heard = ears.listen_for_command()

            if not heard:
                speaker.say("I did not hear anything. Call me again when you are ready.")
                continue

            keep_going = handle(heard)
            if not keep_going:
                break

            # Tiny pause before listening again, so we do not pick up
            # the tail end of our own voice or the room echo.
            time.sleep(0.3)

        except KeyboardInterrupt:
            # Ctrl + C in the window
            print("\n\nStopped by the user.")
            break

        except Exception as error:
            # Never die. One bad moment should not kill the assistant.
            print("\n[error] Something went wrong: " + str(error))
            print("[error] I will keep listening.\n")
            time.sleep(1)
            continue

    # ---- Clean up ----
    ears.shutdown()
    print("TorexAssist has stopped.")


# This is the standard Python way to say "run main() when this file
# is started directly".
if __name__ == "__main__":
    main()
