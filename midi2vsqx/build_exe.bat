@echo off
REM ====================================================================
REM  Build a standalone Windows .exe so you can share the app with a
REM  friend who does NOT have Python installed.
REM
REM  One-time:  py -m pip install pyinstaller
REM  Then just double-click this file.
REM  Result:    dist\MadeByMY-LyricTool.exe   (send that single file)
REM ====================================================================
cd /d "%~dp0"

py -m PyInstaller --noconfirm --onefile --windowed ^
  --name "MadeByMY-LyricTool" ^
  --hidden-import mido.backends.rtmidi ^
  --hidden-import rtmidi ^
  app.py

echo.
if exist "dist\MadeByMY-LyricTool.exe" (
  echo Built OK  ->  dist\MadeByMY-LyricTool.exe
) else (
  echo Build failed. Make sure PyInstaller is installed:
  echo     py -m pip install pyinstaller
)
echo.
pause
