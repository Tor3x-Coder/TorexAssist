    @echo off
REM ============================================================
REM  TorexAssist launcher - double-click this file
REM ============================================================
REM  This just opens the app in a normal window so you can see
REM  what it is doing. Handy while you are setting it up.
REM
REM  Once everything works and you want it hidden at startup,
REM  use the Task Scheduler instructions in README.md instead.
REM ============================================================

title TorexAssist

REM Move into the folder this file lives in, so paths always work
cd /d "%~dp0"

echo Starting TorexAssist...
echo.

REM Try the normal "python" command first.
REM If that fails, try the Windows "py" launcher.
python main.py
if errorlevel 1 (
    py -3.11 main.py
)

echo.
pause
