"""Render del ecualizador visual: imagen dividida en 3 × 4 mosaicos, uno por banda mel."""
from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .audio import analyzeAudio
from .models import AudioFeatures, Palette, VisualState
from .palette import extractPalette
from .states import clusterStates

FPS = 30
SIZE = (1280, 720)  # múltiplos de 16: el códec H.264 no reescala el cuadro
ROWS, COLS = 3, 4  # 12 mosaicos = 12 bandas
GUTTER = 6
CLIP_SECONDS = 20.0
MIN_SECONDS = 10.0
ZOOM = 0.18  # acercamiento máximo del mosaico con energía 1
CONTRAST = 0.9  # cuánto se separa cada banda del promedio del instante
GAMMA = 1.4  # curva >1: los tramos suaves quedan oscuros y los golpes destacan
FLASH_LIFT = 0.38  # cuánto aclara un ataque todo el cuadro

ProgressFn = Callable[[int, str], None]


def bandCell(band: int, rows: int = ROWS, cols: int = COLS) -> tuple[int, int]:
    """Banda 0 (graves) abajo a la izquierda; banda 11 (agudos) arriba a la derecha."""
    return rows - 1 - band // cols, band % cols


def openImage(image) -> Image.Image:
    picture = Image.open(image) if isinstance(image, (str, Path)) else Image.fromarray(np.asarray(image, dtype=np.uint8))
    return ImageOps.exif_transpose(picture).convert("RGB")


def fitImage(image, size=SIZE) -> np.ndarray:
    """Recorta al centro y escala a `size` sin deformar la imagen."""
    return np.asarray(ImageOps.fit(openImage(image), size, Image.Resampling.LANCZOS))


def cropBox(width: int, height: int, size=SIZE) -> list[float]:
    """Zona que conserva `fitImage`, en fracciones de la imagen original (x0, y0, x1, y1)."""
    target = size[0] / size[1]
    if width / height > target:
        keep = height * target / width
        return [(1 - keep) / 2, 0.0, (1 + keep) / 2, 1.0]
    keep = width / target / height
    return [0.0, (1 - keep) / 2, 1.0, (1 + keep) / 2]


def envelope(samples: np.ndarray, points: int = 400) -> np.ndarray:
    """RMS del audio completo en `points` tramos, 0–1, para dibujar la forma de onda."""
    chunk = max(1, samples.size // points)
    usable = samples[: chunk * (samples.size // chunk)].astype(float).reshape(-1, chunk)
    rms = np.sqrt((usable ** 2).mean(axis=1))
    return rms / max(1e-9, rms.max())


def buildMosaicFrame(base: np.ndarray, bands, *, flash: float = 0.0,
                     stateColor=(255, 255, 255), rows: int = ROWS, cols: int = COLS,
                     gutter: int = GUTTER) -> np.ndarray:
    """Compone un cuadro: cada mosaico muestra SU región de la imagen.

    Energía de la banda (0–1) → contraste espectral y curva gamma → brillo
    (0.22×–1.25×) y acercamiento (hasta +18 %).
    Ataque (flash 0–1) → aclara todo el cuadro hacia el color del estado.
    Estado K-Means → color de las juntas entre mosaicos.
    """
    bands = np.clip(np.asarray(bands, dtype=float), 0.0, 1.0)
    if bands.size != rows * cols:
        raise ValueError(f"expected {rows * cols} band values, got {bands.size}")
    bands = visualEnergy(bands)
    height, width = base.shape[:2]
    tileH, tileW = height // rows, width // cols
    color = np.asarray(stateColor, dtype=float)
    joint = color * (0.35 + 0.65 * flash)
    canvas = np.empty((tileH * rows, tileW * cols, 3), dtype=float)
    canvas[:] = joint
    lift = (color + 255.0) / 2
    half = gutter // 2
    innerW, innerH = tileW - gutter, tileH - gutter
    for band, energy in enumerate(bands):
        row, col = bandCell(band, rows, cols)
        y, x = row * tileH, col * tileW
        region = base[y:y + tileH, x:x + tileW]
        zoom = 1.0 + ZOOM * energy
        cropW, cropH = int(tileW / zoom), int(tileH / zoom)
        cx, cy = (tileW - cropW) // 2, (tileH - cropH) // 2
        crop = Image.fromarray(region[cy:cy + cropH, cx:cx + cropW])
        tile = np.asarray(crop.resize((innerW, innerH), Image.Resampling.BILINEAR), dtype=float)
        tile *= 0.22 + 1.03 * energy
        tile += FLASH_LIFT * flash * (lift - tile)
        canvas[y + half:y + half + innerH, x + half:x + half + innerW] = tile
    return np.clip(canvas, 0, 255).astype(np.uint8)


def visualEnergy(bands: np.ndarray) -> np.ndarray:
    """Resalta las bandas que sobresalen en el instante y oscurece los tramos suaves."""
    spread = bands + CONTRAST * (bands - bands.mean())
    return np.clip(spread, 0.0, 1.0) ** GAMMA


def loadAudio(path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    samples, sampleRate = sf.read(str(path), dtype="float32", always_2d=True)
    return samples.mean(axis=1), int(sampleRate)


def pickSegment(samples: np.ndarray, sampleRate: int, seconds: float = CLIP_SECONDS) -> tuple[float, np.ndarray]:
    """Devuelve el tramo de `seconds` con más energía (paso de 0.5 s)."""
    length = int(seconds * sampleRate)
    if samples.size <= length:
        return 0.0, samples
    step = sampleRate // 2
    energy = np.convolve(samples.astype(float) ** 2, np.ones(step), mode="valid")[::step]
    windows = length // step
    totals = np.convolve(energy, np.ones(windows), mode="valid")
    start = int(np.argmax(totals)) * step
    return start / sampleRate, samples[start:start + length]


def perFrame(features: AudioFeatures, frameCount: int, fps: int, labels: np.ndarray) -> dict[str, np.ndarray]:
    """Interpola las series por hop (~86/s) a los instantes exactos de cada cuadro de video."""
    t = np.arange(frameCount) / fps
    interp = lambda series: np.interp(t, features.times, series)
    hopIndex = np.clip(np.round(t * features.sampleRate / features.hop).astype(int), 0, len(features.times) - 1)
    return {
        "t": t,
        "bands": np.stack([interp(row) for row in features.melSmooth], axis=1),
        "bandsRaw": np.stack([interp(row) for row in features.melRaw], axis=1),
        "bandsDb": np.stack([interp(row) for row in features.melDb], axis=1),
        "flash": interp(features.flash),
        "onset": interp(features.onset),
        "rms": interp(features.rms),
        "state": labels[hopIndex] if labels.size else np.zeros(frameCount, dtype=int),
    }


def renderVideo(image, audio, output, *, sampleRate: int | None = None, seconds: float = CLIP_SECONDS,
                minSeconds: float = MIN_SECONDS, fps: int = FPS, size=SIZE,
                onProgress: ProgressFn | None = None, posterPath=None) -> dict:
    """Genera el MP4 con audio y devuelve el análisis que alimenta la interfaz."""
    import imageio.v2 as imageio
    import imageio_ffmpeg
    import soundfile as sf

    report = onProgress or (lambda progress, phase: None)
    if isinstance(audio, (str, Path)):
        samples, sampleRate = loadAudio(audio)
    else:
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        if not sampleRate:
            raise ValueError("sampleRate is required when audio is an array")
    if samples.size == 0:
        raise ValueError("audio must contain at least one sample")
    if samples.size / sampleRate < minSeconds:
        raise ValueError(f"El audio debe durar al menos {minSeconds:g} s.")

    report(10, "Eligiendo el tramo de audio")
    start, segment = pickSegment(samples, sampleRate, seconds)
    report(20, "Calculando bandas mel y ataques")
    features = analyzeAudio(segment, sampleRate)
    source = openImage(image)
    base = np.asarray(ImageOps.fit(source, size, Image.Resampling.LANCZOS))
    report(30, "Agrupando colores y estados con K-Means")
    palette = extractPalette(base)
    states, labels = clusterStates(features, palette)
    frameCount = max(1, round(segment.size / sampleRate * fps))
    series = perFrame(features, frameCount, fps, labels)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    luminance = np.empty(frameCount)
    posterFrame, posterScore = None, -1.0
    with tempfile.TemporaryDirectory() as tmp:
        silent, wav = Path(tmp) / "video.mp4", Path(tmp) / "audio.wav"
        writer = imageio.get_writer(silent, fps=fps, codec="libx264", quality=None, macro_block_size=16,
                                    pixelformat="yuv420p", ffmpeg_log_level="error",
                                    output_params=["-crf", "22", "-preset", "medium"])
        try:
            for i in range(frameCount):
                state = states[series["state"][i]] if states else None
                frame = buildMosaicFrame(base, series["bands"][i], flash=float(series["flash"][i]),
                                         stateColor=state.color if state else (255, 255, 255))
                writer.append_data(frame)
                luminance[i] = frame.mean()
                score = float(series["bands"][i].mean())
                if score > posterScore:
                    posterFrame, posterScore = frame, score
                if i % max(1, frameCount // 20) == 0:
                    report(35 + round(55 * i / frameCount), "Componiendo cuadros")
        finally:
            writer.close()
        report(92, "Uniendo audio y video")
        sf.write(wav, segment, sampleRate)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(silent),
                        "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                        "-movflags", "+faststart", str(output)], check=True)
    if posterPath and posterFrame is not None:
        Image.fromarray(posterFrame).save(posterPath, quality=88)
    report(98, "Guardando análisis")
    payload = analysisPayload(features, palette, states, series, luminance, fps=fps,
                              start=start, duration=segment.size / sampleRate, size=size)
    payload["input"] = {
        "durationSeconds": round(samples.size / sampleRate, 2),
        "envelope": np.round(envelope(samples), 3).tolist(),
        "imageSize": list(source.size),
        "crop": [round(v, 4) for v in cropBox(*source.size, size)],
    }
    return payload


def syncScore(onset: np.ndarray, luminance: np.ndarray) -> float:
    """Correlación entre la fuerza de ataque y la subida de brillo del video (−1 a 1)."""
    rise = np.maximum(0.0, np.diff(luminance, prepend=luminance[:1]))
    if onset.std() < 1e-9 or rise.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(onset, rise)[0, 1])


def analysisPayload(features: AudioFeatures, palette: Palette, states: tuple[VisualState, ...],
                    series: dict[str, np.ndarray], luminance: np.ndarray, *, fps: int,
                    start: float, duration: float, size) -> dict:
    r = lambda values, digits=3: np.round(np.asarray(values, dtype=float), digits).tolist()
    vivid = palette.byVividness()
    dbRange = np.percentile(features.melDb, [5, 95], axis=1).T
    return {
        "fps": fps,
        "size": list(size),
        "grid": {"rows": ROWS, "cols": COLS},
        "segmentStart": round(start, 2),
        "durationSeconds": round(duration, 2),
        "sampleRate": features.sampleRate,
        "hop": features.hop,
        "tempo": round(features.tempo, 1),
        "bandEdgesHz": r(features.bandEdgesHz, 0),
        "onsetTimes": r(features.onsetTimes, 3),
        "beatTimes": r(features.beatTimes, 3),
        "syncScore": round(syncScore(series["onset"], luminance), 3),
        "bandDbRange": r(dbRange, 1),
        "frames": {
            "bands": r(series["bands"]),
            "bandsRaw": r(series["bandsRaw"]),
            "bandsDb": r(series["bandsDb"], 1),
            "flash": r(series["flash"]),
            "onset": r(series["onset"]),
            "rms": r(series["rms"]),
            "state": series["state"].astype(int).tolist(),
            "luminance": r(luminance / 255.0),
        },
        "palette": [{"rgb": list(c), "weight": round(w, 3), "vividRank": vivid.index(c)}
                    for c, w in zip(palette.colors, palette.weights)],
        "states": [{"id": s.id, "name": s.name, "rgb": list(s.color), "energy": round(s.energy, 3),
                    "brightness": round(s.brightness, 3), "attacks": round(s.attacks, 3),
                    "share": round(s.share, 3)} for s in states],
    }
