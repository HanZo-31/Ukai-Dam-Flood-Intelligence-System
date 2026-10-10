@echo off
setlocal
set "npm_config_update_notifier=false"
set "npm_config_audit=false"
set "npm_config_fund=false"
set "PATH=%~dp0runtime\node;%PATH%"
cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 goto failed
call npm test
if errorlevel 1 goto failed
echo Build and frontend tests passed. Restart START_SIMULATION.cmd to use the new build.
pause
exit /b 0
:failed
echo Build or tests failed. Check the messages above before handing off this copy.
pause
exit /b 1
