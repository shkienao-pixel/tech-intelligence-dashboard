@echo off
chcp 65001 >nul
title Tech Intelligence Dashboard

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Tech Intelligence Dashboard            ║
echo  ║   X Data + Claude AI Analysis            ║
echo  ╚══════════════════════════════════════════╝
echo.

set PYTHON=D:\pppppppp\python.exe
set PIP=D:\pppppppp\Scripts\pip.exe

:: ── Check .env ────────────────────────────────────────────────────────────────
if not exist "server\.env" (
    copy "server\.env.example" "server\.env" >nul
)

:: Check if credentials are filled
findstr /C:"your_x_username" "server\.env" >nul
if not errorlevel 1 (
    echo  *** IMPORTANT: Fill in your credentials in server\.env ***
    echo.
    echo  Required fields:
    echo    X_USERNAME        = your X ^(Twitter^) username
    echo    X_EMAIL           = your X email address
    echo    X_PASSWORD        = your X password
    echo    ANTHROPIC_API_KEY = sk-ant-... ^(from console.anthropic.com^)
    echo.
    start notepad "server\.env"
    echo Press any key after filling in credentials...
    pause >nul
)

:: ── Install / Update Dependencies ────────────────────────────────────────────
echo [1/2] Checking Python dependencies...
%PIP% install fastapi "uvicorn[standard]" twikit anthropic python-dotenv httpx -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo       Dependencies OK

:: ── Start Server ──────────────────────────────────────────────────────────────
echo [2/2] Starting server on http://localhost:8000
echo.
echo  ┌─────────────────────────────────────────────────┐
echo  │  Dashboard: http://localhost:8000/app/index.html │
echo  │  API Docs:  http://localhost:8000/docs           │
echo  │  Press Ctrl+C to stop                            │
echo  └─────────────────────────────────────────────────┘
echo.

:: Open browser after 2 seconds
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000/app/index.html"

:: Start server
cd server
%PYTHON% main.py

pause
