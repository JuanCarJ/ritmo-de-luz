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
    output = output_dir / f"{job['id']}.mp4"
    try:
        from ritmo_de_luz_core.pipeline import generateMosaicMp4

        lastProgress = 5

        def reportProgress(progress: int, phase: str) -> None:
            nonlocal lastProgress
            if progress >= lastProgress + 5 or progress >= 95:
                lastProgress = progress
                _write_status(job_file, status="running", progress=progress, phase=phase)

        generateMosaicMp4(
            image=job_dir / "input-image",
            audio=job_dir / "input-audio",
            output=str(output),
            useMl=bool(job.get("mlEnabled", False)),
            onProgress=reportProgress,
        )
        _write_status(job_file, status="completed", progress=100, phase="MP4 listo", outputUrl=f"/runtime/outputs/{output.name}")
    except (OSError, RuntimeError, ValueError) as exc:
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
