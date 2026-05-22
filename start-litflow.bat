@echo off
setlocal

cd /d "%~dp0"

echo Starting LitFlow development environment...
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Close backend/frontend terminal windows to stop LitFlow.
echo.

start "LitFlow Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"
start "LitFlow Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo LitFlow startup commands were opened in separate terminal windows.
echo.
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo Close backend/frontend terminal windows to stop LitFlow.
echo.
pause
