@echo off
title NeuroMesh Observatory Launcher
echo ============================================
echo   NEUROMESH OBSERVATORY - STARTING...
echo ============================================
echo.

:: Kill any existing Python processes on port 8765
echo [1/3] Cleaning up old server instances...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start the server
echo [2/3] Starting Python server on port 8765...
cd /d "C:\Users\ganes\Desktop\SoC_Verification_Project"
start "NeuroMesh Server" /MIN python -u serve_dashboard.py --port 8765

:: Wait for server to start
echo [3/3] Waiting for server to initialize...
timeout /t 4 /nobreak >nul

:: Open browser
echo.
echo ============================================
echo   LAUNCHING DASHBOARD...
echo   http://127.0.0.1:8765
echo ============================================
start http://127.0.0.1:8765

echo.
echo Dashboard is running! Close this window or the
echo server window (titled "NeuroMesh Server") to stop.
echo.
pause
