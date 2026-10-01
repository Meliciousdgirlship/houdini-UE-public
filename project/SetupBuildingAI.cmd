@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_api.ps1"
if errorlevel 1 pause
