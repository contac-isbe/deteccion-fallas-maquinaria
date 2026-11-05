@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\run_simulation.py --port 8771
pause
