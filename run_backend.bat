@echo off
echo ============================================================
echo Starting MARKET PILOT AI - FastAPI Backend Server
echo ============================================================
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at backend\.venv
    echo Run: py -3.12 -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Using Python 3.12 Virtual Environment...
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
