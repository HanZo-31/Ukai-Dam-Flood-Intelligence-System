@echo off
setlocal
cd /d "%~dp0"
"%~dp0runtime\python\python.exe" -B "%~dp0team2_work\combined_runtime.py" --source "%~dp0." --db-port 55438 --api-port 8786 --web-port 5178 --candidate-port 8778 --stop --no-browser
pause
