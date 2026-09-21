#!/bin/bash
# Doble clic en macOS: instala lo necesario (solo la primera vez) y abre Ritmo de Luz.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Se necesita Python 3.11 o superior: https://www.python.org/downloads/"
  read -r -p "Pulsa Enter para cerrar"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Creando entorno virtual (solo la primera vez)..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import librosa, sklearn, fastapi, uvicorn, imageio_ffmpeg, multipart" >/dev/null 2>&1; then
  echo "Instalando dependencias (1–3 minutos, solo la primera vez)..."
  .venv/bin/python -m pip install --upgrade pip -q
  .venv/bin/python -m pip install -r requirements.txt -q
fi

.venv/bin/python scripts/run_local.py
