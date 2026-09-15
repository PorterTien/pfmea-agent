@echo off
REM PFMEA Analysis Tool - Auto Setup & Start Script (Windows Batch)
REM This is a fallback script for older Windows systems without PowerShell

echo.
echo ========================================================================
echo   PFMEA Analysis Tool - Auto Setup & Start (Windows)
echo ========================================================================
echo.

REM Check for PowerShell
where powershell >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using PowerShell script for better compatibility...
    powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
    exit /b %ERRORLEVEL%
)

echo ERROR: PowerShell is required to run this script.
echo.
echo Please either:
echo   1. Install PowerShell (recommended)
echo   2. Or run the setup commands manually (see README.md)
echo.
pause
exit /b 1

