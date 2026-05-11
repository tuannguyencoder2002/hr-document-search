@echo off
title [Document Search] Next.js UI
echo ============================================
echo   Khoi dong Next.js UI (port 3000)
echo ============================================
echo.

REM --- Check Node exists ---
where node >nul 2>&1
if errorlevel 1 (
  echo [LOI] Chua cai Node.js. Tai tai: https://nodejs.org/
  pause
  exit /b 1
)

cd /d "%~dp0\web"

REM --- First-time install ---
if not exist node_modules (
  echo Chua co node_modules, dang cai dat dependencies...
  echo ^(lan dau co the mat 1-2 phut^)
  echo.
  call npm install
  if errorlevel 1 (
    echo.
    echo [LOI] npm install that bai. Kiem tra ket noi mang va thu lai.
    pause
    exit /b 1
  )
  echo.
)

REM --- Auto-open browser after 6s (dev server needs a moment to start) ---
start "" /b cmd /c "timeout /t 6 /nobreak >nul && start http://localhost:3000"

echo Dang khoi dong Next.js dev server...
echo UI: http://localhost:3000  (browser se tu mo)
echo API can chay o  http://localhost:8000  (chay 3_run_api.bat truoc)
echo.
echo Nhan Ctrl+C de dung.
echo.

call npm run dev
pause
