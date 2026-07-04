@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Energy Optimizer Platform - Stop

echo ============================================================
echo   Energy Optimizer Platform - Stop Services
echo ============================================================
echo.

:: ── 项目路径 ──
set "PROJECT_DIR=%~dp0"
set "PID_BACKEND=%PROJECT_DIR%backend\.backend.pid"
set "PID_FRONTEND=%PROJECT_DIR%frontend\.frontend.pid"

:: ── 方式 0: PID 文件优先 ──
echo [INFO] Checking PID files ...
for %%f in ("%PID_BACKEND%" "%PID_FRONTEND%") do (
    if exist %%f (
        set /p PID=<%%f
        taskkill /pid !PID! /f >nul 2>&1
        if !errorlevel! equ 0 (
            echo        [OK] Process from %%f ^(PID !PID!^) terminated.
        ) else (
            echo        [WARN] PID file %%f found but process !PID! could not be killed.
        )
        del %%f 2>nul
    )
)
echo.

:: ── 方式 1: PowerShell Get-NetTCPConnection (Win8+/2012+, locale-safe) ──
:: ── 方式 2: netstat + findstr ──
for %%p in (8000 5173) do (
    echo --- Checking port %%p ---
    set "KILLED=0"

    rem Method 1: PowerShell Get-NetTCPConnection (locale-safe)
    for /f "tokens=1" %%a in ('powershell -NoProfile -Command "& {try {$p=Get-NetTCPConnection -LocalPort %%p -ErrorAction Stop; $p.OwningProcess} catch{}}" 2^>nul') do (
        if not "%%a"=="0" if not "%%a"=="" (
            taskkill /pid %%a /f >nul 2>&1
            if !errorlevel! equ 0 (
                echo        [OK] Process on port %%p ^(PID %%a^) terminated.
                set "KILLED=1"
            ) else (
                echo        [WARN] Process on port %%p ^(PID %%a^) could not be killed.
            )
        )
    )

    rem Method 2: netstat + findstr /c: exact match on LISTENING lines
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":%%p " ^| findstr /c:"LISTENING"') do (
        if not "%%a"=="0" if not "%%a"=="" (
            taskkill /pid %%a /f >nul 2>&1
            if !errorlevel! equ 0 (
                echo        [OK] Process on port %%p ^(PID %%a^) terminated.
                set "KILLED=1"
            ) else (
                echo        [WARN] Process on port %%p ^(PID %%a^) could not be killed.
            )
        )
    )

    rem Verify: poll port to confirm released
    %WINDIR%\System32\ping -n 2 127.0.0.1 >nul
    set "STILL_RUNNING=0"
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":%%p " ^| findstr /c:"LISTENING"') do set "STILL_RUNNING=1"
    if !STILL_RUNNING! equ 0 (
        if !KILLED! equ 1 (
            echo        [OK] Port %%p is now free.
        ) else (
            echo        [INFO] Port %%p was not in use.
        )
    ) else (
        echo  [WARN] Port %%p may still be in use - try running as Administrator.
    )
    echo.
)

echo ============================================================
echo   Stop completed. Check above for any [WARN] messages.
echo ============================================================
echo.
pause
