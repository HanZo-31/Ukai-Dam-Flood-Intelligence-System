@echo off
setlocal
title Ukai Simulation
cd /d "%~dp0"
call "%~dp0team2_work\START_TEAM2.cmd" "%~dp0."
exit /b %ERRORLEVEL%
