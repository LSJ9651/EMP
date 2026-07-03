@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Energy Optimizer Platform - Stop

echo ============================================================
echo   Energy Optimizer Platform - Stop Services
echo ============================================================
echo.

set "HAS_ERROR=0"

:: Port 8000 - Backend
echo --- Checking port 8000 ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8000 "') do (
    echo         Found PID: %%a
    set "PNAME=Unknown"
    for /f "tokens=1 delims=," %%b in ('tasklist /fi "PID eq %%a" /fo csv /nh 2^>nul') do (
        set "PNAME=%%~b"
    )
    taskkill /pid %%a /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo         [OK] PID %%a !PNAME! terminated
    ) else (
        echo         [WARN] PID %%a no longer exists
    )
)
netstat -ano | findstr "LISTENING" | findstr ":8000 " >nul 2>&1
if %errorlevel% neq 0 echo         [INFO] Port 8000 is not in use.
echo.

:: Port 5173 - Frontend
echo --- Checking port 5173 ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":5173 "') do (
    echo         Found PID: %%a
    set "PNAME=Unknown"
    for /f "tokens=1 delims=," %%b in ('tasklist /fi "PID eq %%a" /fo csv /nh 2^>nul') do (
        set "PNAME=%%~b"
    )
    taskkill /pid %%a /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo         [OK] PID %%a !PNAME! terminated
    ) else (
        echo         [WARN] PID %%a no longer exists
    )
)
netstat -ano | findstr "LISTENING" | findstr ":5173 " >nul 2>&1
if %errorlevel% neq 0 echo         [INFO] Port 5173 is not in use.
echo.

echo ============================================================
echo   All checks complete.
echo ============================================================
echo.
pause
