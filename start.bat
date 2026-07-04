@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Energy Optimizer Platform - Start

:: ============================================================
::  Energy Optimizer Platform - Windows Start Script
::  Start Backend  (FastAPI :8000) and Frontend (Vite :5173)
:: ============================================================

set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"

echo ============================================================
echo   Energy Optimizer Platform
echo ============================================================
echo.

:: ---------- Step 1: Check Python ----------
echo [1/5] Checking Python environment...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo         Python %%v detected

:: ---------- Step 2: Check Node.js ----------
echo [2/5] Checking Node.js environment...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo         Node.js %%v detected

:: ---------- Step 3: Backend venv + deps ----------
echo [3/5] Setting up backend environment...
if not exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    echo         [WARN] Virtual environment not found, creating...
    pushd "%BACKEND_DIR%"
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        popd
        pause
        exit /b 1
    )
    popd
)

echo         Installing/verifying backend dependencies...
pushd "%BACKEND_DIR%"
call .venv\Scripts\activate.bat
set RETRY=0

:retry_pip
pip install -r requirements.txt
if errorlevel 1 (
    set /a RETRY+=1
    if !RETRY! lss 3 (
        echo         [WARN] Install failed (attempt !RETRY!/3), retrying in 5 seconds...
        %WINDIR%\System32\ping -n 6 127.0.0.1 >nul
        goto retry_pip
    )
    echo [ERROR] Failed to install backend dependencies after 3 attempts.
    call deactivate
    popd
    pause
    exit /b 1
)
call deactivate
popd
echo         Backend dependencies ready.

:: ---------- Step 4: Frontend deps ----------
echo [4/5] Checking frontend dependencies...
if exist "%FRONTEND_DIR%\node_modules" goto :frontend_deps_done

echo         [WARN] Frontend dependencies not installed, installing...
pushd "%FRONTEND_DIR%"
set RETRY_NPM=0

:retry_npm
call npm install
if errorlevel 1 (
    set /a RETRY_NPM+=1
    if !RETRY_NPM! lss 3 (
        echo         [WARN] npm install failed (attempt !RETRY_NPM!/3), retrying in 5 seconds...
        %WINDIR%\System32\ping -n 6 127.0.0.1 >nul
        goto retry_npm
    )
    echo [ERROR] Failed to install frontend dependencies after 3 attempts.
    popd
    pause
    exit /b 1
)
popd

:frontend_deps_done
echo         Frontend dependencies ready.

:: ---------- Step 5: Start services ----------
echo [5/5] Starting services...
echo.

:: Start backend in new window
echo         Starting backend service (http://localhost:8000) ...
start "Energy-Backend" /D "%BACKEND_DIR%" cmd /c "call .venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo         API Docs: http://localhost:8000/docs

:: Wait a few seconds then health-check
echo         Waiting for backend service...
%WINDIR%\System32\ping -n 4 127.0.0.1 >nul

set BACKEND_UP=0
for /l %%i in (1,1,15) do (
    >nul 2>nul curl -sf http://localhost:8000/
    if not errorlevel 1 set BACKEND_UP=1 & goto :backend_ready
    %WINDIR%\System32\ping -n 2 127.0.0.1 >nul
)
:backend_ready

if %BACKEND_UP% equ 0 (
    echo [ERROR] Backend service did not respond at http://localhost:8000
    echo         Check backend window for errors.
)
if %BACKEND_UP% equ 1 echo         Backend service is up and responding.

:: Start frontend in new window
echo         Starting frontend service (http://localhost:5173) ...
start "Energy-Frontend" /D "%FRONTEND_DIR%" cmd /c "npm run dev"
echo         Frontend URL: http://localhost:5173

:: Open browser
echo.
echo         Opening browser...
start http://localhost:5173

echo.
echo ============================================================
echo   All services started!
echo   Backend: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo   Test account: admin / admin123
echo ============================================================
echo.
echo   Closing this window will not affect running services.
echo   To stop all services, run stop.bat
echo.

pause
