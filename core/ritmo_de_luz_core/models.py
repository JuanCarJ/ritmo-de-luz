"""Modelos del núcleo audiovisual."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AudioFeatures:
    """Features por ventana STFT (hop). Todas las series comparten `times`."""

    sampleRate: int
    hop: int
    times: np.ndarray  # (n,) segundos
    melDb: np.ndarray  # (bandas, n) dB relativos al máximo del clip
    melRaw: np.ndarray  # (bandas, n) dB normalizados a 0–1 por banda (p5–p95)
    melSmooth: np.ndarray  # (bandas, n) melRaw con ataque rápido y caída lenta
    bandEdgesHz: np.ndarray  # (bandas + 1,) límites de cada banda mel
    rms: np.ndarray  # (n,) 0–1
    centroid: np.ndarray  # (n,) 0–1
    onset: np.ndarray  # (n,) envolvente de ataques 0–1
    flash: np.ndarray  # (n,) impulso por ataque detectado con caída exponencial 0–1
    rawRms: np.ndarray
    rawCentroidHz: np.ndarray
    onsetTimes: np.ndarray
    beatTimes: np.ndarray
    tempo: float

    @property
    def bands(self) -> int:
        return int(self.melSmooth.shape[0])


@dataclass(frozen=True)
class Palette:
    """Colores dominantes (K-Means sobre RGB) ordenados por peso descendente."""

    colors: tuple[tuple[int, int, int], ...]
    weights: tuple[float, ...]

    def byVividness(self) -> tuple[tuple[int, int, int], ...]:
        """Colores de menos a más vivos (saturación × valor en HSV)."""
        return tuple(sorted(self.colors, key=vividness))


def vividness(rgb: tuple[int, int, int]) -> float:
    hi, lo = max(rgb) / 255, min(rgb) / 255
    return (hi - lo) * hi + 0.25 * hi


@dataclass(frozen=True)
class VisualState:
    """Estado acústico de K-Means; `id` 0 es el de menor energía."""

    id: int
    name: str
    color: tuple[int, int, int]
    energy: float
    brightness: float
    attacks: float
    share: float
