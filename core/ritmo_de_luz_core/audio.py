"""Primitivas de análisis de audio; NumPy se carga de forma opcional."""
from __future__ import annotations

from collections.abc import Sequence

from .models import AudioFeatures

try:
    import numpy as np
except ImportError:  # pragma: no cover - instalación mínima
    np = None


def _require_numpy() -> None:
    if np is None:
        raise RuntimeError("audio analysis requires numpy; install ritmo-de-luz[audio]")


def _smooth(values, window: int):
    if window <= 1 or len(values) < 2:
        return values
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def analyzeAudio(samples: Sequence[float], sampleRate: int, *, frameSize: int = 2048,
                 hopSize: int = 512, melBands: int = 12, smoothing: int = 3) -> AudioFeatures:
    """Extrae RMS, centroide, onsets y energía por bandas mel normalizados."""
    _require_numpy()
    if sampleRate <= 0 or frameSize <= 0 or hopSize <= 0:
        raise ValueError("sampleRate, frameSize and hopSize must be positive")
    signal = np.asarray(samples, dtype=float).reshape(-1)
    if signal.size == 0:
        return AudioFeatures((), (), (), (), ())
    if signal.size < frameSize:
        signal = np.pad(signal, (0, frameSize - signal.size))
    count = 1 + max(0, (signal.size - frameSize) // hopSize)
    window = np.hanning(frameSize)
    frames = np.stack([signal[i * hopSize:i * hopSize + frameSize] * window for i in range(count)])
    magnitudes = np.abs(np.fft.rfft(frames, axis=1))
    power = magnitudes ** 2
    rawRms = np.sqrt(np.mean(frames ** 2, axis=1))
    rms = _normalize(rawRms)
    freqs = np.fft.rfftfreq(frameSize, 1.0 / sampleRate)
    denom = magnitudes.sum(axis=1)
    rawCentroid = np.divide(magnitudes @ freqs, denom, out=np.zeros_like(denom), where=denom > 1e-12)
    centroid = _normalize(rawCentroid)
    flux = np.maximum(0.0, np.diff(power, axis=0, prepend=power[:1])).sum(axis=1)
    rawOnset = flux
    onset = _normalize(rawOnset)
    bands = _mel_filterbank(magnitudes, sampleRate, melBands)
    bands = np.asarray([_normalize(row) for row in bands.T]).T if bands.size else bands
    return AudioFeatures(tuple(np.arange(count) * hopSize / sampleRate),
                         tuple(_smooth(rms, smoothing)), tuple(_smooth(centroid, smoothing)),
                         tuple(_smooth(onset, smoothing)), tuple(tuple(float(x) for x in row) for row in bands),
                         tuple(float(x) for x in rawRms), tuple(float(x) for x in rawCentroid),
                         tuple(float(x) for x in rawOnset))


def _normalize(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0: return values
    lo, hi = float(values.min()), float(values.max())
    return np.zeros_like(values) if hi - lo < 1e-12 else (values - lo) / (hi - lo)


def _mel_filterbank(magnitudes, sampleRate: int, count: int):
    if count <= 0: return np.empty((magnitudes.shape[0], 0))
    bins = magnitudes.shape[1]; edges = np.linspace(0, bins - 1, count + 2, dtype=int)
    out = np.zeros((magnitudes.shape[0], count))
    for band in range(count):
        left, center, right = edges[band:band + 3]
        if right <= left: continue
        weights = np.zeros(bins)
        if center > left: weights[left:center] = np.linspace(0, 1, center - left, endpoint=False)
        if right > center: weights[center:right] = np.linspace(1, 0, right - center, endpoint=False)
        out[:, band] = (magnitudes * weights).sum(axis=1)
    return out
