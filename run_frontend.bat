@echo off
echo ============================================================
echo Starting MARKET PILOT AI - React / Vite Frontend
echo ============================================================
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [ERROR] node_modules not found. Running npm install...
    call npm install
)

echo Starting Vite development server at http://localhost:5173...
npm run dev
pause
