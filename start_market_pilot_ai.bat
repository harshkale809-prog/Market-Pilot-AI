@echo off
title MARKET PILOT AI - Master Launcher
echo ============================================================
echo           LAUNCHING MARKET PILOT AI SAAS PLATFORM
echo ============================================================
cd /d "%~dp0"

echo [1/3] Starting Backend API Server (FastAPI on http://localhost:8000)...
start "MarketPilot AI - Backend API" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Starting Frontend Dev Server (React/Vite on http://localhost:5173)...
start "MarketPilot AI - Frontend UI" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo [3/3] Opening browser at http://localhost:5173...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo ============================================================
echo MarketPilot AI is now running!
echo - Frontend: http://localhost:5173
echo - Backend:  http://localhost:8000
echo - Swagger:  http://localhost:8000/docs
echo ============================================================
