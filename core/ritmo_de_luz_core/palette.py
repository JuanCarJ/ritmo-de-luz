"""Extracción de paleta con aceleración opcional de scikit-learn."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import Palette


def extractPalette(pixels: Iterable[Sequence[int]], *, colors: int = 5, seed: int = 7,
                   useMl: bool = True) -> Palette:
    points = [tuple(max(0, min(255, int(c))) for c in p[:3]) for p in pixels]
    if not points or colors <= 0: return Palette((), ())
    colors = min(colors, len(points))
    try:
        if not useMl:
            raise ImportError
        from sklearn.cluster import KMeans
        model = KMeans(n_clusters=colors, random_state=seed, n_init=10).fit(points)
        centers = [tuple(round(float(v)) for v in row) for row in model.cluster_centers_]
        counts = [int((model.labels_ == i).sum()) for i in range(colors)]
    except (ImportError, ValueError):
        # Los cuantiles mantienen el resultado reproducible sin sklearn.
        ordered = sorted(points)
        centers, counts = [], []
        for i in range(colors):
            bucket = ordered[i * len(ordered) // colors:(i + 1) * len(ordered) // colors]
            bucket = bucket or [ordered[min(i, len(ordered) - 1)]]
            centers.append(tuple(round(sum(p[j] for p in bucket) / len(bucket)) for j in range(3)))
            counts.append(len(bucket))
    total = float(sum(counts))
    return Palette(tuple(centers), tuple(c / total for c in counts))
