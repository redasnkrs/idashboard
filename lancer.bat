@echo off
cd /d "%~dp0"
if exist "idash.exe" (
  start "" "idash.exe"
  exit /b 0
)
python main.py
if errorlevel 1 pause
