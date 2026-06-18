@echo off
REM ====================================================================
REM  Double-click this file to open the MIDI -> VSQX Lyric Tool.
REM  It finds a Python 3 that has the app's libraries (installing them
REM  the first time if needed), then runs app.py with it.
REM ====================================================================
cd /d "%~dp0"

REM --- Pick a Python launcher. Prefer 3.9 (where this project's libs live). ---
set "PYEXE="
py -3.9 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.9"
if not defined PYEXE ( py -3 -c "import sys" >nul 2>&1 && set "PYEXE=py -3" )
if not defined PYEXE ( python -c "import sys" >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
  echo.
  echo Python 3 was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add Python to PATH" during setup, then run this again.
  echo.
  pause
  exit /b 1
)

REM --- Make sure the libraries are present in that Python; install if not. ---
%PYEXE% -c "import customtkinter, mido, rtmidi" >nul 2>&1
if errorlevel 1 (
  echo First-time setup: installing the libraries the app needs ^(one moment^)...
  %PYEXE% -m pip install -r requirements.txt
)

%PYEXE% app.py
if errorlevel 1 (
  echo.
  echo The app could not start - see the message above.
  pause
)
