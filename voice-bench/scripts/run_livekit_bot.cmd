@echo off
setlocal
cd /d "%~dp0.."
if not exist "livekit\.env" (
  echo Missing livekit\.env. Run scripts\configure_livekit.py first.
  exit /b 2
)
for /f "usebackq tokens=1,* delims==" %%A in ("livekit\.env") do set "%%A=%%B"
set "PYTHONPATH="
set "XDG_CACHE_HOME=%CD%\.cache"
set "MOONSHINE_VOICE_CACHE=%CD%\models\moonshine"
set "NLTK_DATA=%CD%\models\nltk_data"
".venv\Scripts\python.exe" src\bot_livekit.py
