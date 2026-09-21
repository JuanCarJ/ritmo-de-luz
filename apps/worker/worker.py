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
        import numpy as np
        import soundfile as sf
        from PIL import Image
        from ritmo_de_luz_core.pipeline import generateMosaicMp4

        samples, _sampleRate = sf.read(job_dir / "input-audio", dtype="float32", always_2d=False)
        samples = np.mean(samples, axis=1) if np.ndim(samples) > 1 else samples

        lastProgress = 5

        def reportProgress(progress: int, phase: str) -> None:
            nonlocal lastProgress
            if progress >= lastProgress + 5 or progress >= 95:
                lastProgress = progress
                _write_status(job_file, status="running", progress=progress, phase=phase)

        def saveAnalysis(features, palette, states, stateLabels) -> None:
            analysis = {
                "times": [float(value) for value in features.times],
                "waveform": [float(value) for value in samples[::max(1, len(samples) // 120)]],
                "rms": [float(value) for value in features.rms],
                "rawRms": [float(value) for value in features.rawRms],
                "spectralCentroid": [float(value) for value in features.spectral_centroid],
                "rawSpectralCentroid": [float(value) for value in features.rawSpectralCentroid],
                "onset": [float(value) for value in features.onset],
                "rawOnset": [float(value) for value in features.rawOnset],
                "melBands": [[float(value) for value in frame] for frame in features.mel_bands],
                "palette": {"colors": palette.colors, "weights": [float(value) for value in palette.weights]},
                "stateLabels": list(stateLabels),
                "states": [{"name": state.name, "intensity": state.intensity,
                            "color": state.color, "features": state.features} for state in states],
            }
            analysis_path = output_dir / f"{job['id']}.json"
            analysis_path.write_text(json.dumps(analysis), encoding="utf-8")

            source = np.asarray(Image.open(job_dir / "input-image").convert("RGB"))
            firstMel = features.mel_bands[0] if features.mel_bands else (features.rms[0],)
            firstState = states[0] if states else None
            preview = buildMosaicFrame(source, mel=firstMel,
                                       intensity=firstState.intensity if firstState else features.rms[0],
                                       color=firstState.color if firstState else (255, 255, 255),
                                       rows=4, columns=6, size=(960, 540))
            Image.fromarray(preview).save(output_dir / f"{job['id']}-mapping.png")
            _write_status(job_file, analysisUrl=f"/runtime/outputs/{job['id']}.json",
                          mappingUrl=f"/runtime/outputs/{job['id']}-mapping.png")

        from ritmo_de_luz_core.pipeline import buildMosaicFrame

        generateMosaicMp4(
            image=job_dir / "input-image",
            audio=job_dir / "input-audio",
            output=str(output),
            useMl=bool(job.get("mlEnabled", False)),
            onProgress=reportProgress,
            onAnalysis=saveAnalysis,
        )
        _write_status(job_file, status="completed", progress=100, phase="MP4 listo",
                      outputUrl=f"/runtime/outputs/{output.name}")
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
