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

:: ---------- Check port conflicts ----------
echo [0/6] Checking port availability...
set "PORT_CONFLICT=0"
for %%p in (8000 5173) do (
    netstat -ano | findstr /c:":%%p " | findstr /c:"LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [ERROR] Port %%p is already in use. Please stop the process first or run stop.bat.
        set "PORT_CONFLICT=1"
    )
)
if !PORT_CONFLICT! equ 1 (
    pause
    exit /b 1
)
echo         All ports available.

:: ---------- Check Python ----------
echo [1/6] Checking Python environment...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9-3.12 and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo         Python !PYVER! detected
:: Validate Python version range (3.9 - 3.12)
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set "PYMAJOR=%%a"
    set "PYMINOR=%%b"
)
if !PYMAJOR! gtr 3 (
    echo [ERROR] Python 3.13+ is not supported due to SQLAlchemy compatibility.
    echo        Please use Python 3.9 - 3.12. Download from https://www.python.org/downloads/
    pause
    exit /b 1
)
if !PYMAJOR! lss 3 (
    echo [ERROR] Python 3.9+ is required. Found Python 2.x.
    pause
    exit /b 1
)
if !PYMINOR! lss 9 (
    echo [ERROR] Python 3.9+ is required. Found Python 3.!PYMINOR!.
    pause
    exit /b 1
)

:: ---------- Check Node.js ----------
echo [2/6] Checking Node.js environment...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo         Node.js %%v detected

:: ---------- Check backend dependencies ----------
echo [3/6] Checking backend dependencies...
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
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo         [WARN] Backend dependencies not installed, installing...
    pushd "%BACKEND_DIR%"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    popd
)
echo         Backend dependencies ready.
call deactivate

:: ---------- Check frontend dependencies ----------
echo [4/6] Checking frontend dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo         [WARN] Frontend dependencies not installed, installing...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
)
echo         Frontend dependencies ready.

:: ---------- Check .env file ----------
echo [5/6] Checking configuration...
if not exist "%BACKEND_DIR%\.env" (
    echo         [WARN] backend/.env not found. The platform will start with default settings.
    echo             For production use, copy .env.example to .env and configure your API keys.
)

:: ---------- Initialize database ----------
echo         Initializing database and seed data...
pushd "%BACKEND_DIR%"
call .venv\Scripts\activate.bat
python scripts/init_db.py
if %errorlevel% neq 0 (
    echo [ERROR] Database initialization failed.
    popd
    pause
    exit /b 1
)
python scripts/init_mock_data.py
if %errorlevel% neq 0 (
    echo [ERROR] Mock data initialization failed.
    popd
    pause
    exit /b 1
)
call deactivate
popd

:: ---------- Start services ----------
echo [6/6] Starting services...
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

:: Wait for backend (HTTP health check)
echo         Waiting for backend service to be ready...
set "RETRIES=10"
set "READY=0"
for /l %%i in (1,1,!RETRIES!) do (
    timeout /t 1 /nobreak >nul
    powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri http://localhost:8000/ -TimeoutSec 1 -UseBasicParsing; exit 0 } catch { exit 1 }" 2>nul
    if !errorlevel! equ 0 (
        set "READY=1"
        goto :backend_ready
    )
)
:backend_ready
if !READY! equ 0 (
    echo [WARN] Backend did not respond within 10 seconds. It may still be starting up.
) else (
    echo         Backend is ready.
)

:: Start frontend (new window)
echo         Starting frontend service (http://localhost:5173) ...
start "Energy-Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"
echo         Frontend URL: http://localhost:5173

:: Save PID files for stop.bat
echo         Saving process IDs for stop.bat...
timeout /t 1 /nobreak >nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8000 " ^| findstr /c:"LISTENING"') do (
    echo %%a > "%PROJECT_DIR%backend\.backend.pid"
    echo         Backend PID: %%a
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":5173 " ^| findstr /c:"LISTENING"') do (
    echo %%a > "%PROJECT_DIR%frontend\.frontend.pid"
    echo         Frontend PID: %%a
)

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
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo   Test account: admin / admin123
echo ============================================================
echo.
echo   Closing this window will not affect running services.
echo   To stop all services, run stop.bat
echo.

pause
