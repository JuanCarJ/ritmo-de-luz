"""API de análisis y generación de frames."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from .audio import analyzeAudio
from .models import AnalysisResult, VisualFrame
from .palette import extractPalette
from .states import clusterStates


def analyze(samples: Sequence[float], sampleRate: int, pixels: Iterable[Sequence[int]] = (), *, useMl: bool = False) -> AnalysisResult:
    audio = analyzeAudio(samples, sampleRate)
    palette = extractPalette(pixels, useMl=useMl)
    states = clusterStates(audio, palette, useMl=useMl)
    frames = tuple(VisualFrame(i, audio.times[i], states[i % len(states)].name,
                               states[i % len(states)].intensity, states[i % len(states)].color)
                   for i in range(len(audio.times))) if states else ()
    return AnalysisResult(audio, palette, states, frames)

def renderMp4(frames: Sequence[VisualFrame], output: str, *, fps: int = 30, size=(640, 360)) -> str:
    """Renderiza frames de color sólido si están disponibles imageio y FFmpeg."""
    try:
        import imageio.v3 as iio
        import numpy as np
    except Exception as exc:
        raise RuntimeError("MP4 rendering requires imageio and ffmpeg") from exc
    images = [np.full((size[1], size[0], 3), frame.color, dtype=np.uint8) for frame in frames]
    iio.imwrite(output, images, fps=fps)
    return output


def buildMosaicFrame(image, *, mel: Sequence[float] = (), intensity: float = 1.0,
                     color=(255, 255, 255), rows: int = 4, columns: int = 6,
                     size=(960, 540)):
    """Construye un mosaico RGB reproducible; cada baldosa sigue una banda mel."""
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("mosaic rendering requires numpy and pillow") from exc
    source = np.asarray(image, dtype=np.uint8)
    if source.ndim != 3 or source.shape[2] < 3:
        raise ValueError("image must be an HxWx3 RGB array")
    source = source[:, :, :3]
    tile_w, tile_h = size[0] // columns, size[1] // rows
    values = list(mel) or [0.0]
    canvas = np.zeros((tile_h * rows, tile_w * columns, 3), dtype=np.uint8)
    tint = np.asarray(color, dtype=float) / 255.0
    for idx in range(rows * columns):
        value = max(0.0, min(1.0, float(values[idx % len(values)])))
        scale = 0.82 + 0.24 * value
        crop_w = max(1, int(source.shape[1] / scale)); crop_h = max(1, int(source.shape[0] / scale))
        cx, cy = source.shape[1] // 2, source.shape[0] // 2
        crop = source[max(0, cy - crop_h // 2):cy + crop_h // 2,
                      max(0, cx - crop_w // 2):cx + crop_w // 2]
        tile = np.asarray(Image.fromarray(crop).resize((tile_w, tile_h), Image.Resampling.BILINEAR), dtype=float)
        alpha = 0.55 + 0.45 * value
        tile = tile * (0.75 + 0.25 * float(intensity)) * alpha + (255.0 * tint) * (1 - alpha)
        y, x = (idx // columns) * tile_h, (idx % columns) * tile_w
        canvas[y:y + tile_h, x:x + tile_w] = np.clip(tile, 0, 255).astype(np.uint8)
    return canvas


def generateMosaicMp4(image, audio, output: str, *, sampleRate: int | None = None,
                      fps: int = 30, size=(960, 540), rows: int = 4, columns: int = 6,
                      useMl: bool = False) -> str:
    """Genera un MP4 de mosaicos reactivos desde rutas o arrays de audio e imagen."""
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("mosaic rendering requires imageio, numpy and pillow") from exc
    image_path = str(image) if isinstance(image, (str, Path)) else None
    source = np.asarray(Image.open(image).convert("RGB")) if image_path else np.asarray(image)
    audio_path = str(audio) if isinstance(audio, (str, Path)) else None
    if audio_path:
        try:
            import soundfile as sf
            samples, detected_rate = sf.read(audio_path, dtype="float32")
            samples = np.mean(samples, axis=1) if np.ndim(samples) > 1 else samples
            sampleRate = sampleRate or int(detected_rate)
        except Exception as exc:
            raise RuntimeError("loading audio paths requires soundfile") from exc
    else:
        samples = np.asarray(audio, dtype=float)
    if not sampleRate:
        raise ValueError("sampleRate is required when audio is an array")
    if samples.size == 0:
        raise ValueError("audio must contain at least one sample")
    try:
        import imageio.v3 as iio
    except Exception as exc:
        raise RuntimeError("mosaic rendering requires imageio, numpy and pillow") from exc
    features = analyzeAudio(samples, sampleRate, melBands=12)
    palette = extractPalette(source.reshape(-1, 3)[::max(1, source.shape[0] * source.shape[1] // 2000)], useMl=useMl)
    states = clusterStates(features, palette, useMl=useMl)
    duration = max(1, round(len(samples) / sampleRate * fps))
    frames = []
    for idx in range(duration):
        exactPos = min(len(features.times) - 1, idx / fps * sampleRate / 512)
        leftPos = int(exactPos)
        rightPos = min(len(features.times) - 1, leftPos + 1)
        blend = exactPos - leftPos
        leftMel = features.mel_bands[leftPos] if features.mel_bands else (features.rms[leftPos],)
        rightMel = features.mel_bands[rightPos] if features.mel_bands else (features.rms[rightPos],)
        mel = tuple((1 - blend) * left + blend * right for left, right in zip(leftMel, rightMel))
        state = states[min(len(states) - 1, round(exactPos))] if states else None
        intensity = state.intensity if state else features.rms[leftPos]
        color = state.color if state else (255, 255, 255)
        frames.append(buildMosaicFrame(source, mel=mel, intensity=intensity, color=color,
                                       rows=rows, columns=columns, size=size))
    iio.imwrite(output, np.asarray(frames), fps=fps)
    if audio_path and shutil.which("ffmpeg"):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            muxed = tmp.name
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(output),
                            "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", muxed],
                           check=True)
            Path(muxed).replace(output)
        finally:
            Path(muxed).unlink(missing_ok=True)
    return output
