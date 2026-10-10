@echo off
cd /d "%~dp0"
echo This updates the checksum inventory of THIS folder after intentional edits.
echo It records file contents; it does not prove the edited software works.
"runtime\python\python.exe" -B scripts\seal_simulation_copy.py --root "%~dp0."
if errorlevel 1 (echo SEAL FAILED.) else (echo SEALED. Now run VERIFY_COPY.cmd.)
pause
