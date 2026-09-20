from __future__ import annotations

import json
import os
import secrets
import threading
import wave
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
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "25000000"))
MIN_AUDIO_SECONDS = int(os.getenv("MIN_AUDIO_SECONDS", "20"))
MAX_AUDIO_SECONDS = int(os.getenv("MAX_AUDIO_SECONDS", "40"))
ENABLE_ML = os.getenv("ENABLE_ML", "false").lower() == "true"
EMBEDDED_WORKER = os.getenv("EMBEDDED_WORKER", "true").lower() == "true"

for directory in (JOBS_DIR, OUTPUTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Ritmo de Luz API", version="0.1.0")
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
    payload = {
        "name": "Ritmo de Luz",
        "videoUrl": "/artifacts/demo/ritmo-de-luz-menu-loop.mp4",
        "posterUrl": "/artifacts/demo/ritmo-de-luz-demo-poster.jpg",
        "bands": 12,
        "mlEnabled": ENABLE_ML,
        "demos": [],
    }
    if manifest.exists():
        try:
            payload.update(json.loads(manifest.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    return payload


async def _saveUpload(upload: UploadFile, destination: Path) -> None:
    total = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="El archivo supera el límite permitido.")
            target.write(chunk)


def _validateAudioDuration(audioPath: Path) -> None:
    try:
        with wave.open(str(audioPath), "rb") as audioFile:
            duration = audioFile.getnframes() / max(1, audioFile.getframerate())
    except (EOFError, wave.Error) as exc:
        raise HTTPException(status_code=415, detail="El audio debe ser un WAV válido.") from exc
    if duration < MIN_AUDIO_SECONDS or duration > MAX_AUDIO_SECONDS:
        raise HTTPException(status_code=413, detail=f"El audio debe durar entre {MIN_AUDIO_SECONDS} y {MAX_AUDIO_SECONDS} segundos.")


@app.post("/api/render", status_code=202)
async def createRender(
    image: Annotated[UploadFile, File()], audio: Annotated[UploadFile, File()]
) -> dict:
    image_type = (image.content_type or "").lower()
    audio_type = (audio.content_type or "").lower()
    if image_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=415, detail="La imagen debe ser PNG o JPG.")
    if audio_type not in {"audio/wav", "audio/x-wav", "audio/wave"} and not (audio.filename or "").lower().endswith(".wav"):
        raise HTTPException(status_code=415, detail="El audio debe ser un archivo WAV.")

    job_id = f"job_{secrets.token_hex(6)}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    await _saveUpload(image, job_dir / "input-image")
    audioPath = job_dir / "input-audio"
    await _saveUpload(audio, audioPath)
    _validateAudioDuration(audioPath)
    job = {"id": job_id, "status": "queued", "progress": 0, "mlEnabled": ENABLE_ML, "outputUrl": None, "error": None}
    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


@app.get("/api/jobs/{job_id}")
def jobStatus(job_id: str) -> dict:
    job_file = JOBS_DIR / job_id / "job.json"
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    try:
        return json.loads(job_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Estado de trabajo inválido.") from exc


@app.on_event("startup")
def startEmbeddedWorker() -> None:
    if not EMBEDDED_WORKER:
        return
    from apps.worker.worker import worker_loop

    thread = threading.Thread(target=worker_loop, args=(JOBS_DIR, OUTPUTS_DIR, False), daemon=True)
    thread.start()
