@echo off
title J.A.R.V.I.S — Demo Launcher
echo.
echo ╔══════════════════════════════════════════╗
echo ║     J.A.R.V.I.S — DEMO LAUNCHER         ║
echo ║     Hermes Neural Interface              ║
echo ╚══════════════════════════════════════════╝
echo.
echo Opening JARVIS HUD in your default browser...
echo.
echo TIP: Click the arc reactor ring or press Space for a demo.
echo TIP: Press 'B' for cinematic boot sequence.
echo TIP: Press 'Esc' to dismiss panels.
echo.

start "" "%~dp0jarvis_demo.html"

echo Launched! If the browser didn't open, double-click jarvis_demo.html directly.
echo.
pause
