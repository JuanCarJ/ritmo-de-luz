"""Primitivas de análisis de audio; NumPy se carga de forma opcional."""
from __future__ import annotations

from collections.abc import Sequence

from .models import AudioFeatures

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised in minimal installations
    np = None


def _require_numpy() -> None:
    if np is None:
        raise RuntimeError("audio analysis requires numpy; install ritmo-de-luz[audio]")


def _smooth(values, window: int):
    if window <= 1 or len(values) < 2:
        return values
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def analyzeAudio(samples: Sequence[float], sample_rate: int, *, frame_size: int = 2048,
                 hop_size: int = 512, mel_bands: int = 12, smoothing: int = 3) -> AudioFeatures:
    """Extrae RMS, centroide, onsets y energía por bandas mel normalizados."""
    _require_numpy()
    if sample_rate <= 0 or frame_size <= 0 or hop_size <= 0:
        raise ValueError("sample_rate, frame_size and hop_size must be positive")
    signal = np.asarray(samples, dtype=float).reshape(-1)
    if signal.size == 0:
        return AudioFeatures((), (), (), (), ())
    if signal.size < frame_size:
        signal = np.pad(signal, (0, frame_size - signal.size))
    count = 1 + max(0, (signal.size - frame_size) // hop_size)
    window = np.hanning(frame_size)
    frames = np.stack([signal[i * hop_size:i * hop_size + frame_size] * window for i in range(count)])
    magnitudes = np.abs(np.fft.rfft(frames, axis=1))
    power = magnitudes ** 2
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    rms = _normalize(rms)
    freqs = np.fft.rfftfreq(frame_size, 1.0 / sample_rate)
    denom = magnitudes.sum(axis=1)
    centroid = np.divide(magnitudes @ freqs, denom, out=np.zeros_like(denom), where=denom > 1e-12)
    centroid = _normalize(centroid)
    flux = np.maximum(0.0, np.diff(power, axis=0, prepend=power[:1])).sum(axis=1)
    onset = _normalize(flux)
    bands = _mel_filterbank(magnitudes, sample_rate, mel_bands)
    bands = np.asarray([_normalize(row) for row in bands.T]).T if bands.size else bands
    return AudioFeatures(tuple(np.arange(count) * hop_size / sample_rate),
                         tuple(_smooth(rms, smoothing)), tuple(_smooth(centroid, smoothing)),
                         tuple(_smooth(onset, smoothing)), tuple(tuple(float(x) for x in row) for row in bands))


def _normalize(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0: return values
    lo, hi = float(values.min()), float(values.max())
    return np.zeros_like(values) if hi - lo < 1e-12 else (values - lo) / (hi - lo)


def _mel_filterbank(magnitudes, sample_rate: int, count: int):
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
