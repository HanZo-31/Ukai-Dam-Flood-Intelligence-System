@echo off
setlocal
set "npm_config_update_notifier=false"
set "npm_config_audit=false"
set "npm_config_fund=false"
set "PATH=%~dp0runtime\node;%PATH%"
cd /d "%~dp0frontend"
echo Start START_SIMULATION.cmd first. Development opens at http://127.0.0.1:5175.
call npm run dev
pause
