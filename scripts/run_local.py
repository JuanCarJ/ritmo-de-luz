from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("DATA_DIR", str(ROOT / "runtime"))
os.environ.setdefault("EMBEDDED_WORKER", "true")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))

if __name__ == "__main__":
    uvicorn.run("apps.api.app.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=False)

