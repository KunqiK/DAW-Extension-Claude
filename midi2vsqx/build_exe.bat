@echo off
REM ====================================================================
REM  Build a standalone Windows .exe so you can share the app with a
REM  friend who does NOT have Python installed.
REM
REM  Uses Python 3.9 (py -3.9) — that's where this project's libraries
REM  (customtkinter / mido / python-rtmidi) are installed. If you keep
REM  them under a different Python, change "py -3.9" below to match.
REM
REM  One-time:  py -3.9 -m pip install pyinstaller -r requirements.txt
REM  Then just double-click this file.
REM  Result:    dist\MadeByMY-LyricTool.exe   (send that single file)
REM ====================================================================
cd /d "%~dp0"

py -3.9 -m PyInstaller --noconfirm --onefile --windowed ^
  --name "MadeByMY-LyricTool" ^
  --collect-all customtkinter ^
  --hidden-import mido.backends.rtmidi ^
  --hidden-import rtmidi ^
  app.py

echo.
if exist "dist\MadeByMY-LyricTool.exe" (
  echo Built OK  ->  dist\MadeByMY-LyricTool.exe
) else (
  echo Build failed. Make sure PyInstaller is installed:
  echo     py -3.9 -m pip install pyinstaller -r requirements.txt
)
echo.
pause
