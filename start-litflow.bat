@echo off
setlocal

set "ROOT=%~dp0"

echo Starting LitFlow development environment...
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo.

where wt.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "LitFlow Backend" wt.exe new-tab --title "LitFlow Backend" cmd /k "pushd ""%ROOT%backend"" && if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"
  start "LitFlow Frontend" wt.exe new-tab --title "LitFlow Frontend" cmd /k "pushd ""%ROOT%frontend"" && npm run dev"
) else (
  start "LitFlow Backend" cmd /k "pushd ""%ROOT%backend"" && if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"
  start "LitFlow Frontend" cmd /k "pushd ""%ROOT%frontend"" && npm run dev"
)

echo LitFlow startup commands were opened in separate terminal windows.
echo.
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo.
pause
