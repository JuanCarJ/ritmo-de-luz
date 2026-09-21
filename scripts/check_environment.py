from __future__ import annotations

import importlib.util
import sys

REQUIRED = ("fastapi", "uvicorn", "numpy", "PIL", "soundfile", "librosa", "sklearn", "imageio", "imageio_ffmpeg")

def main() -> int:
    missing = [name for name in REQUIRED if importlib.util.find_spec(name) is None]
    print(f"Python: {sys.version.split()[0]}")
    if missing:
        print("Faltan dependencias: " + ", ".join(missing))
        return 1
    import imageio_ffmpeg

    print(f"FFmpeg: {imageio_ffmpeg.get_ffmpeg_exe()}")
    print("Dependencias: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

