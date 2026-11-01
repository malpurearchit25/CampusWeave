@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-CampusWeave.ps1"
if errorlevel 1 pause
if not errorlevel 1 start "" "http://127.0.0.1:5050"
