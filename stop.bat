@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Energy Optimizer Platform - Stop

echo ============================================================
echo   Energy Optimizer Platform - Stop Services
echo ============================================================
echo.

:: Kill process on port 8000 (Backend) and 5173 (Frontend)
:: 兼容中英文 Windows：直接按端口号查找，不依赖 LISTENING 关键字
for %%p in (8000 5173) do (
    echo --- Checking port %%p ---
    for /f "skip=4 tokens=5" %%a in ('netstat -ano ^| findstr ":%%p "') do (
        if not "%%a"=="0" (
            taskkill /pid %%a /f >nul 2>&1
            if !errorlevel! equ 0 (
                echo         [OK] PID %%a terminated
            ) else (
                echo         [WARN] PID %%a already terminated
            )
        )
    )
    echo         [INFO] Port %%p check complete.
    echo.
)

echo ============================================================
echo   All checks complete.
echo ============================================================
echo.
pause
