@echo off
cd /d "%~dp0"
"runtime\python\python.exe" -B scripts\simulation_runtime.py --verify-copy
if errorlevel 1 (echo COPY VERIFICATION FAILED.) else (echo COPY VERIFIED.)
pause
