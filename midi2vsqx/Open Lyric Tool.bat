@echo off
REM ====================================================================
REM  Double-click this file to open the MIDI -> VSQX Lyric Tool.
REM  (It just runs "python app.py" from this folder for you.)
REM ====================================================================
cd /d "%~dp0"
python app.py
if errorlevel 1 (
  echo.
  echo The app could not start.
  echo Make sure Python 3 is installed and that typing "python" in a
  echo terminal works. Then try double-clicking this file again.
  echo.
  pause
)
