@echo off
REM Doble clic en Windows: instala lo necesario (solo la primera vez) y abre Ritmo de Luz.
setlocal
cd /d "%~dp0"

set "PY=py -3"
%PY% --version >nul 2>&1 || set "PY=python"
%PY% --version >nul 2>&1 || (
  echo Se necesita Python 3.11 o superior: https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual ^(solo la primera vez^)...
  %PY% -m venv .venv || (pause & exit /b 1)
)

".venv\Scripts\python.exe" -c "import librosa, sklearn, fastapi, uvicorn, imageio_ffmpeg, multipart" >nul 2>&1
if errorlevel 1 (
  echo Instalando dependencias ^(1-3 minutos, solo la primera vez^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q || (pause & exit /b 1)
)

".venv\Scripts\python.exe" scripts\run_local.py
pause
