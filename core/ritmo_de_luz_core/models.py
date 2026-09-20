"""Modelos tipados y ligeros para el núcleo audiovisual."""
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AudioFeatures:
    times: tuple[float, ...]
    rms: tuple[float, ...]
    spectral_centroid: tuple[float, ...]
    onset: tuple[float, ...]
    mel_bands: tuple[tuple[float, ...], ...] = ()


@dataclass(frozen=True)
class Palette:
    colors: tuple[tuple[int, int, int], ...]
    weights: tuple[float, ...]


@dataclass(frozen=True)
class VisualState:
    name: str
    intensity: float
    color: tuple[int, int, int]
    features: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualFrame:
    index: int
    time: float
    state: str
    intensity: float
    color: tuple[int, int, int]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisResult:
    audio: AudioFeatures
    palette: Palette
    states: tuple[VisualState, ...]
    frames: tuple[VisualFrame, ...]
