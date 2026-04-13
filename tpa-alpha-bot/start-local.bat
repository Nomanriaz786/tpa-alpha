@echo off
REM TPA Alpha Bot - Local Development Startup Script (Windows)
REM Run this from the tpa-alpha-bot directory

echo.
echo ========================================
echo   TPA Alpha Bot - Local Development
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo ^⚠️  Please edit .env with your credentials before running!
    echo.
    pause
)

echo.
echo [1/3] Starting Backend API Server...
echo        Starting FastAPI on port 8000...
cd backend
start "TPA Backend" cmd /k python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd ..
timeout /t 2 /nobreak

echo.
echo [2/3] Starting Frontend React App...
echo        Starting Vite on port 5173...
cd frontend
start "TPA Frontend" cmd /k npm install ^&^& npm run dev
cd ..
timeout /t 3 /nobreak

echo.
echo [3/3] Starting Discord Bot...
cd bot
start "TPA Bot" cmd /k python bot.py
cd ..

echo.
echo ========================================
echo   ^✅ Services Starting!
echo ========================================
echo.
echo ^📍 URLs:
echo    Frontend:  http://localhost:5173
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo.
echo ^🔧 Check individual console windows for logs
echo.
echo ^⏹️  Close console windows to stop services
echo.
pause
