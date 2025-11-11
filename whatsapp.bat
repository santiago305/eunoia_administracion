@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo.
echo [0/3] Preparando entorno (venv + dependencias)...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\bootstrap.ps1"
if errorlevel 1 (
  echo [ERROR] Fallo preparando dependencias. Revisa mensajes anteriores.
  pause
  exit /b 1
)

echo.
echo [1/3] Preparando Chrome (CDP)...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_chrome_debug.ps1"
if errorlevel 1 (
  echo [ERROR] No se pudo abrir Chrome.
  pause
  exit /b 1
)

timeout /t 4 /nobreak >nul

REM Detectar Python del venv o del sistema
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo [2/3] Ejecutando programa (con cierre garantizado de Chrome al final)...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\run_with_cleanup.ps1" -Python "%PY%" -Entry "main.py"
set "ERR=%ERRORLEVEL%"

echo.
echo [3/3] Fin del proceso. Codigo de salida: %ERR%
pause