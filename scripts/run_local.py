"""Arranca la aplicación local: genera la demo si falta y abre el navegador."""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("DATA_DIR", str(ROOT / "runtime"))
os.environ.setdefault("EMBEDDED_WORKER", "true")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "scripts"))

if __name__ == "__main__":
    if not (ROOT / "artifacts" / "demo" / "manifest.json").exists():
        print("Primera ejecución: generando las demos (menos de un minuto)...")
        import generate_demo

        generate_demo.main()
    port = int(os.getenv("PORT", "8000"))
    url = f"http://127.0.0.1:{port}"
    print(f"\nRitmo de Luz listo en {url}  (Ctrl+C para cerrar)\n")
    if os.getenv("NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("apps.api.app.main:app", host="127.0.0.1", port=port, reload=False, log_level="warning")
