@echo off
setlocal
cd /d "%~dp0.."
if not exist "livekit\.env" (
  echo Missing livekit\.env. Run scripts\configure_livekit.py first.
  exit /b 2
)
for /f "usebackq tokens=1,* delims==" %%A in ("livekit\.env") do set "%%A=%%B"
set "PYTHONPATH="
".venv\Scripts\python.exe" scripts\livekit_token.py %*
