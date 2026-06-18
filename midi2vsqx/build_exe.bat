@echo off
REM ====================================================================
REM  Build a standalone Windows app so you can share it with a friend
REM  who does NOT have Python installed.
REM
REM  Uses Python 3.9 (py -3.9) — that's where this project's libraries
REM  (customtkinter / mido / python-rtmidi) are installed. If you keep
REM  them under a different Python, change "py -3.9" below to match.
REM
REM  We build a ONE-FOLDER app (--onedir), not a single .exe: a one-file
REM  exe unpacks itself to %TEMP% on every launch, which can fail with
REM  "Failed to extract ... decompression resulted in return code -1"
REM  (antivirus / locked temp). A one-folder build has no unpack step.
REM
REM  One-time:  py -3.9 -m pip install pyinstaller -r requirements.txt
REM  Then just double-click this file.
REM  Result:    dist\MadeByMY-LyricTool\  (a folder)
REM             -> run MadeByMY-LyricTool.exe inside it.
REM             -> to share: zip that whole folder and send the zip.
REM ====================================================================
cd /d "%~dp0"

py -3.9 -m PyInstaller --noconfirm --onedir --windowed ^
  --name "MadeByMY-LyricTool" ^
  --collect-all customtkinter ^
  --hidden-import mido.backends.rtmidi ^
  --hidden-import rtmidi ^
  app.py

echo.
if exist "dist\MadeByMY-LyricTool\MadeByMY-LyricTool.exe" (
  echo Built OK  ->  dist\MadeByMY-LyricTool\MadeByMY-LyricTool.exe
  echo To share: zip the whole "dist\MadeByMY-LyricTool" folder.
) else (
  echo Build failed. Make sure PyInstaller is installed:
  echo     py -3.9 -m pip install pyinstaller -r requirements.txt
)
echo.
pause
