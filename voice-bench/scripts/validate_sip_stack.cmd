@echo off
setlocal
set PYTHONPATH=
set "VP2_ROOT=%~dp0.."
"%VP2_ROOT%\.venv\Scripts\python.exe" "%~dp0validate_sip_stack.py"
