"""Análisis de audio: 12 bandas mel, energía, brillo espectral y ataques."""
from __future__ import annotations

from collections.abc import Sequence

import librosa
import numpy as np

from .models import AudioFeatures

N_FFT = 2048  # 46 ms a 44.1 kHz: resolución suficiente para graves
HOP = 512  # 11.6 ms entre ventanas: ~86 lecturas por segundo
FMIN = 30.0
FMAX = 16000.0
ATTACK = 0.6  # fracción del salto que se sigue en cada hop cuando la energía sube
RELEASE = 0.08  # fracción que se sigue cuando baja: caída de ~0.15 s
FLASH_DECAY_S = 0.18


def analyzeAudio(samples: Sequence[float], sampleRate: int, *, bands: int = 12,
                 nFft: int = N_FFT, hop: int = HOP) -> AudioFeatures:
    """Calcula bandas mel en dB normalizadas y suavizadas, RMS, centroide y ataques."""
    if sampleRate <= 0 or nFft <= 0 or hop <= 0 or bands <= 0:
        raise ValueError("sampleRate, nFft, hop and bands must be positive")
    y = np.asarray(samples, dtype=np.float32).reshape(-1)
    if y.size == 0:
        raise ValueError("audio must contain at least one sample")
    if y.size < nFft:
        y = np.pad(y, (0, nFft - y.size))

    fmax = min(FMAX, sampleRate / 2)
    mel = librosa.feature.melspectrogram(y=y, sr=sampleRate, n_fft=nFft, hop_length=hop,
                                         n_mels=bands, fmin=FMIN, fmax=fmax, power=2.0)
    # dB comprime el rango dinámico como lo percibe el oído; ref=max deja 0 dB en el pico.
    melDb = librosa.power_to_db(mel, ref=np.max, top_db=80.0)
    melRaw = np.stack([percentileNormalize(row) for row in melDb])
    melSmooth = attackRelease(melRaw, ATTACK, RELEASE)

    rawRms = librosa.feature.rms(y=y, frame_length=nFft, hop_length=hop)[0]
    rawCentroid = librosa.feature.spectral_centroid(y=y, sr=sampleRate, n_fft=nFft, hop_length=hop)[0]
    onsetEnv = librosa.onset.onset_strength(y=y, sr=sampleRate, hop_length=hop)
    onsetFrames = librosa.onset.onset_detect(onset_envelope=onsetEnv, sr=sampleRate, hop_length=hop)
    tempo, beatFrames = librosa.beat.beat_track(onset_envelope=onsetEnv, sr=sampleRate, hop_length=hop)

    n = min(melRaw.shape[1], rawRms.size, rawCentroid.size, onsetEnv.size)
    onset = percentileNormalize(onsetEnv[:n], low=0, high=99)
    flash = onsetFlash(onset, onsetFrames[onsetFrames < n], hop / sampleRate)
    edges = librosa.mel_frequencies(n_mels=bands + 2, fmin=FMIN, fmax=fmax)
    bandEdges = np.concatenate([[edges[0]], (edges[1:-2] + edges[2:-1]) / 2, [edges[-1]]])

    return AudioFeatures(
        sampleRate=int(sampleRate), hop=hop,
        times=librosa.frames_to_time(np.arange(n), sr=sampleRate, hop_length=hop),
        melDb=melDb[:, :n], melRaw=melRaw[:, :n], melSmooth=melSmooth[:, :n],
        bandEdgesHz=bandEdges,
        rms=percentileNormalize(rawRms[:n], low=0, high=99),
        centroid=percentileNormalize(rawCentroid[:n], low=1, high=99),
        onset=onset, flash=flash,
        rawRms=rawRms[:n], rawCentroidHz=rawCentroid[:n],
        onsetTimes=librosa.frames_to_time(onsetFrames, sr=sampleRate, hop_length=hop),
        beatTimes=librosa.frames_to_time(beatFrames, sr=sampleRate, hop_length=hop),
        tempo=float(np.atleast_1d(tempo)[0]),
    )


def percentileNormalize(values, *, low: float = 5, high: float = 95) -> np.ndarray:
    """Reescala a 0–1 entre dos percentiles; un pico aislado no aplana el resto."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values
    lo, hi = np.percentile(values, [low, high])
    if hi - lo < 1e-9:
        return np.zeros_like(values)
    return np.clip((values - lo) / (hi - lo), 0.0, 1.0)


def attackRelease(values, attack: float, release: float) -> np.ndarray:
    """Filtro de envolvente: sube rápido con los golpes y cae despacio, sin parpadeo."""
    values = np.asarray(values, dtype=float)
    out = np.empty_like(values)
    state = values[..., 0].copy()
    for i in range(values.shape[-1]):
        current = values[..., i]
        coef = np.where(current > state, attack, release)
        state = state + coef * (current - state)
        out[..., i] = state
    return out


def onsetFlash(onset: np.ndarray, onsetFrames: np.ndarray, hopSeconds: float) -> np.ndarray:
    """Impulso en cada ataque detectado (proporcional a su fuerza) con caída exponencial."""
    impulses = np.zeros_like(onset)
    impulses[onsetFrames] = np.maximum(0.35, onset[onsetFrames])
    decay = float(np.exp(-hopSeconds / FLASH_DECAY_S))
    out = np.empty_like(onset)
    state = 0.0
    for i, impulse in enumerate(impulses):
        state = max(float(impulse), state * decay)
        out[i] = state
    return out
