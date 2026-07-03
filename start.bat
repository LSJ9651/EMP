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

:: ---------- Check Python ----------
echo [1/5] Checking Python environment...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo         Python %%v detected

:: ---------- Check Node.js ----------
echo [2/5] Checking Node.js environment...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo         Node.js %%v detected

:: ---------- Check backend dependencies ----------
echo [3/5] Checking backend dependencies...
if not exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    echo         [WARN] Virtual environment not found, creating...
    pushd "%BACKEND_DIR%"
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        popd
        pause
        exit /b 1
    )
    popd
)

:: Activate venv and check dependencies
call "%BACKEND_DIR%\.venv\Scripts\activate.bat"
"%BACKEND_DIR%\.venv\Scripts\python" -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo         [WARN] Backend dependencies not installed, installing...
    pushd "%BACKEND_DIR%"
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install backend dependencies.
        popd
        pause
        exit /b 1
    )
    popd
)
echo         Backend dependencies ready.
call deactivate

:: ---------- Check frontend dependencies ----------
echo [4/5] Checking frontend dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo         [WARN] Frontend dependencies not installed, installing...
    pushd "%FRONTEND_DIR%"
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies.
        popd
        pause
        exit /b 1
    )
    popd
)
echo         Frontend dependencies ready.

:: ---------- Start services ----------
echo [5/5] Starting services...
echo.

:: Start backend (new window)
echo         Starting backend service (http://localhost:8000) ...
start "Energy-Backend" cmd /c "cd /d "%BACKEND_DIR%" && call .venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start backend.
    pause
    exit /b 1
)
echo         API Docs: http://localhost:8000/docs

:: Wait for backend, then verify it is really up
echo         Waiting for backend service...
timeout /t 3 /nobreak >nul

:: Health check: retry up to 10 seconds
for /l %%i in (1,1,10) do (
    >nul 2>nul curl -sf http://localhost:8000/
    if !errorlevel! equ 0 goto :backend_ready
    >nul 2>nul powershell -Command "try { (Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing).StatusCode -eq 200 } catch { $false }"
    if !errorlevel! equ 0 goto :backend_ready
    timeout /t 1 /nobreak >nul
)
echo         [WARN] Backend did not respond, continuing anyway...
:backend_ready

:: Start frontend (new window)
echo         Starting frontend service (http://localhost:5173) ...
start "Energy-Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start frontend.
    pause
    exit /b 1
)
echo         Frontend URL: http://localhost:5173

:: Open default browser with frontend page
echo.
echo         Opening browser...
start http://localhost:5173
if %errorlevel% neq 0 (
    echo [WARN] Failed to open browser automatically.
    echo         Please manually open: http://localhost:5173
)

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
