@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH="
set "XDG_CACHE_HOME=%CD%\.cache"
set "MOONSHINE_VOICE_CACHE=%CD%\models\moonshine"
set "NLTK_DATA=%CD%\models\nltk_data"
".venv\Scripts\python.exe" scripts\smoke_test.py
