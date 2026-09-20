"""Agrupación de estados visuales con fallback determinista."""
from __future__ import annotations

from .models import AudioFeatures, Palette, VisualState


def clusterStates(audio: AudioFeatures, palette: Palette, *, count: int = 4, seed: int = 7,
                  useMl: bool = True) -> tuple[VisualState, ...]:
    count = max(1, count)
    n = len(audio.rms)
    if not n: return ()
    points = [[audio.rms[i], audio.spectral_centroid[i], audio.onset[i]] for i in range(n)]
    labels = None
    try:
        if not useMl:
            raise ImportError
        from sklearn.cluster import KMeans
        labels = KMeans(n_clusters=min(count, n), random_state=seed, n_init=10).fit_predict(points)
    except (ImportError, ValueError):
        labels = [min(count - 1, int(p[0] * count)) for p in points]
    result = []
    for state_id in range(max(labels) + 1):
        members = [i for i, label in enumerate(labels) if label == state_id]
        avg = [sum(points[i][j] for i in members) / len(members) for j in range(3)]
        color = palette.colors[state_id % len(palette.colors)] if palette.colors else (255, 255, 255)
        result.append(VisualState(f"state_{state_id}", max(0.0, min(1.0, avg[0])), color,
                                  {"centroid": avg[1], "onset": avg[2]}))
    return tuple(result)
