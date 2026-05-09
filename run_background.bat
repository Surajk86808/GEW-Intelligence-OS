@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "LOG_DIR=%ROOT_DIR%phase_2_transcription\logs"
set "LOG_FILE=%LOG_DIR%\transcription.log"
set "PYTHON_EXE=%ROOT_DIR%venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Launching GEW background transcription. Logs: "%LOG_FILE%"
start "GEW Background Transcription" /min cmd /c ""%PYTHON_EXE%" "%ROOT_DIR%main.py" --background --resume --minimal-ui %* >> "%LOG_FILE%" 2>&1"
