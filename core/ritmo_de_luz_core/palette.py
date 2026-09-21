"""Colores dominantes de la imagen con K-Means sobre RGB."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .models import Palette


def extractPalette(image, *, colors: int = 5, seed: int = 7, maxPixels: int = 20000) -> Palette:
    """Agrupa los píxeles en `colors` centros; el peso es la fracción de píxeles de cada uno."""
    pixels = np.asarray(image, dtype=float).reshape(-1, np.asarray(image).shape[-1])[:, :3]
    if pixels.size == 0 or colors <= 0:
        return Palette((), ())
    step = max(1, len(pixels) // maxPixels)
    pixels = pixels[::step]
    k = min(colors, len(np.unique(pixels, axis=0)))
    model = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(pixels)
    counts = np.bincount(model.labels_, minlength=k)
    order = np.argsort(counts)[::-1]
    centers = [tuple(round(v) for v in model.cluster_centers_[i]) for i in order]
    weights = [float(counts[i] / counts.sum()) for i in order]
    return Palette(tuple(centers), tuple(weights))
