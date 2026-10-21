@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail
echo Setup finished. Start Ollama and run: ollama pull qwen2.5:1.5b
echo Then run start.cmd.
pause
exit /b 0
:fail
echo Setup failed. Check the error above.
pause
exit /b 1
