@echo off
setlocal enabledelayedexpansion

set PROFILE=%LOCALAPPDATA%\GoogleFlowAgentProfile

if not exist "%PROFILE%" mkdir "%PROFILE%"
if exist "%PROFILE%\lockfile" del /f /q "%PROFILE%\lockfile" >nul 2>&1

set CHROME_BIN=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_BIN=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_BIN%"=="" (
    echo [ERROR] Google Chrome not found in standard paths.
    pause
    exit /b 1
)

echo Starting Chrome with remote debugging on port 9222...
echo Profile path: %PROFILE%
start /min "" "%CHROME_BIN%" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%PROFILE%" "https://flow.google.com"

echo [SUCCESS] Chrome started in background/minimized.
