from __future__ import annotations

import json
import os
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = ROOT / "apps" / "web" / "static"
ARTIFACTS_DIR = ROOT / "artifacts"
RUNTIME_DIR = Path(os.getenv("DATA_DIR", ROOT / "runtime"))
JOBS_DIR = RUNTIME_DIR / "jobs"
OUTPUTS_DIR = RUNTIME_DIR / "outputs"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "40000000"))
# Se acepta cualquier duración razonable: el render usa el tramo de 20 s con más energía.
MIN_AUDIO_SECONDS = 10
MAX_AUDIO_SECONDS = 600
EMBEDDED_WORKER = os.getenv("EMBEDDED_WORKER", "true").lower() == "true"

for directory in (JOBS_DIR, OUTPUTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if EMBEDDED_WORKER:
        from apps.worker.worker import worker_loop

        threading.Thread(target=worker_loop, args=(JOBS_DIR, OUTPUTS_DIR, False), daemon=True).start()
    yield


app = FastAPI(title="Ritmo de Luz API", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")
app.mount("/runtime/outputs", StaticFiles(directory=OUTPUTS_DIR), name="runtime-outputs")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ritmo-de-luz-api"}


@app.get("/api/demo")
def demo() -> dict:
    manifest = ARTIFACTS_DIR / "demo" / "manifest.json"
    if not manifest.exists():
        raise HTTPException(status_code=503, detail="Falta la demo. Ejecuta scripts/generate_demo.py.")
    return json.loads(manifest.read_text(encoding="utf-8"))


async def _saveUpload(upload: UploadFile, destination: Path) -> None:
    total = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="El archivo supera 40 MB.")
            target.write(chunk)


def _validateImage(path: Path) -> None:
    from PIL import Image

    try:
        with Image.open(path) as picture:
            picture.verify()
    except Exception as exc:
        raise HTTPException(status_code=415, detail="La imagen debe ser un PNG o JPG válido.") from exc


def _validateAudio(path: Path) -> None:
    import soundfile as sf

    try:
        info = sf.info(str(path))
    except Exception as exc:
        raise HTTPException(status_code=415, detail="No se pudo leer el audio. Usa WAV, FLAC, OGG o MP3.") from exc
    if not MIN_AUDIO_SECONDS <= info.duration <= MAX_AUDIO_SECONDS:
        raise HTTPException(status_code=422, detail=f"El audio debe durar entre {MIN_AUDIO_SECONDS} s y "
                                                    f"10 min (dura {info.duration:.1f} s).")


@app.post("/api/render", status_code=202)
async def createRender(image: Annotated[UploadFile, File()], audio: Annotated[UploadFile, File()]) -> dict:
    job_id = f"job_{secrets.token_hex(6)}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    await _saveUpload(image, job_dir / "input-image")
    await _saveUpload(audio, job_dir / "input-audio")
    _validateImage(job_dir / "input-image")
    _validateAudio(job_dir / "input-audio")
    job = {"id": job_id, "status": "queued", "progress": 0, "phase": "En cola", "outputUrl": None, "error": None}
    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


@app.get("/api/jobs/{job_id}")
def jobStatus(job_id: str) -> dict:
    if not job_id.startswith("job_") or not job_id[4:].isalnum():
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    job_file = JOBS_DIR / job_id / "job.json"
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    try:
        return json.loads(job_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Estado de trabajo inválido.") from exc
