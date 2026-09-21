from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _write_status(job_file: Path, **changes: object) -> dict:
    job = json.loads(job_file.read_text(encoding="utf-8"))
    job.update(changes)
    job_file.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


def process_job(job_dir: Path, output_dir: Path) -> None:
    job_file = job_dir / "job.json"
    job = _write_status(job_file, status="running", progress=5, phase="Cargando archivos")
    output_dir.mkdir(parents=True, exist_ok=True)
    jobId = job["id"]
    video = output_dir / f"{jobId}.mp4"
    poster = output_dir / f"{jobId}.jpg"
    lastProgress = 5

    def reportProgress(progress: int, phase: str) -> None:
        nonlocal lastProgress
        if progress >= lastProgress + 3:
            lastProgress = progress
            _write_status(job_file, status="running", progress=progress, phase=phase)

    try:
        from ritmo_de_luz_core.pipeline import renderVideo

        analysis = renderVideo(job_dir / "input-image", job_dir / "input-audio", video,
                               onProgress=reportProgress, posterPath=poster)
        (output_dir / f"{jobId}.json").write_text(json.dumps(analysis), encoding="utf-8")
        _write_status(job_file, status="completed", progress=100, phase="Video listo",
                      outputUrl=f"/runtime/outputs/{video.name}",
                      posterUrl=f"/runtime/outputs/{poster.name}",
                      analysisUrl=f"/runtime/outputs/{jobId}.json")
    except Exception as exc:  # noqa: BLE001 - el error se muestra en la interfaz en lugar de dejar el trabajo colgado
        _write_status(job_file, status="failed", progress=100, phase="Error", error=str(exc)[:240])


def worker_loop(jobs_dir: Path, output_dir: Path, once: bool = False) -> None:
    jobs_dir.mkdir(parents=True, exist_ok=True)
    while True:
        for job_dir in sorted(jobs_dir.glob("job_*")):
            job_file = job_dir / "job.json"
            if not job_file.exists():
                continue
            try:
                job = json.loads(job_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if job.get("status") == "queued":
                process_job(job_dir, output_dir)
        if once:
            return
        time.sleep(1)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    jobs = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "runtime/jobs"
    outputs = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "runtime/outputs"
    worker_loop(jobs, outputs)
