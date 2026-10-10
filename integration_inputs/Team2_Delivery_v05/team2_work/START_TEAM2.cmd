@echo off
setlocal
set "UKAI_TEAM2_SOURCE=%~1"
if not defined UKAI_TEAM2_SOURCE set "UKAI_TEAM2_SOURCE=%UKAI_REFERENCE_ROOT%"
if not defined UKAI_TEAM2_SOURCE if exist "%~dp0..\runtime\python\python.exe" set "UKAI_TEAM2_SOURCE=%~dp0.."
if not defined UKAI_TEAM2_SOURCE (
  echo Usage: START_TEAM2.cmd "full path to Ukai_SSD_Ready"
  exit /b 1
)
"%UKAI_TEAM2_SOURCE%\runtime\python\python.exe" -B "%~dp0combined_runtime.py" --source "%UKAI_TEAM2_SOURCE%"
set "UKAI_TEAM2_EXIT=%ERRORLEVEL%"
pause
exit /b %UKAI_TEAM2_EXIT%
