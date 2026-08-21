@echo off
setlocal
cd /d "%~dp0.."
if not defined VP2_LIVEKIT_ENV_FILE set "VP2_LIVEKIT_ENV_FILE=%USERPROFILE%\.novacore\secrets\vp2-livekit.env"
if not exist "%VP2_LIVEKIT_ENV_FILE%" (
  echo Missing external LiveKit environment file. Run scripts\configure_livekit.py first.
  exit /b 2
)
for /f "usebackq tokens=1,* delims==" %%A in ("%VP2_LIVEKIT_ENV_FILE%") do set "%%A=%%B"
set "PYTHONPATH="
set "XDG_CACHE_HOME=%CD%\.cache"
set "MOONSHINE_VOICE_CACHE=%CD%\models\moonshine"
set "NLTK_DATA=%CD%\models\nltk_data"
".venv\Scripts\python.exe" src\bot_livekit.py
