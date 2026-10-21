@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run setup.cmd to create the Python environment.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8001 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8001
pause
