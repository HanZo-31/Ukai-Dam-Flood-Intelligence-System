@echo off
echo Historical baseline-only diagnostic. This does not verify the merged candidate service.
echo For current combined evidence and commands, read START_INTEGRATION.md.
cd /d "%~dp0"
"runtime\python\python.exe" -B scripts\simulation_runtime.py --check-only --no-browser
pause
