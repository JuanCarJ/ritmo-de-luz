from __future__ import annotations

import importlib.util
import shutil
import sys

REQUIRED = ("fastapi", "uvicorn", "numpy", "PIL", "soundfile", "imageio")
OPTIONAL = ("sklearn",)

def main() -> int:
    missing = [name for name in REQUIRED if importlib.util.find_spec(name) is None]
    print(f"Python: {sys.version.split()[0]}")
    print(f"FFmpeg: {shutil.which('ffmpeg') or 'se usará imageio-ffmpeg si está disponible'}")
    if missing:
        print("Faltan dependencias: " + ", ".join(missing))
        return 1
    print("Dependencias base: OK")
    print("Machine learning: " + ("OK" if importlib.util.find_spec(OPTIONAL[0]) else "fallback determinista"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

