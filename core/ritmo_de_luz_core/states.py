"""Estados acústicos con K-Means y su color en la paleta de la imagen."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .models import AudioFeatures, Palette, VisualState

STATE_NAMES = ("Calma", "Movimiento", "Enérgico", "Fuerte")


def clusterStates(audio: AudioFeatures, palette: Palette, *, count: int = 4,
                  seed: int = 7) -> tuple[tuple[VisualState, ...], np.ndarray]:
    """Agrupa las ventanas por energía, brillo y ataques.

    Los grupos se ordenan por energía y reciben colores de la paleta ordenados por
    viveza: el estado más tranquilo toma el color más apagado y el más intenso el
    más vivo. Devuelve los estados y la etiqueta (0 = más tranquilo) de cada ventana.
    """
    points = np.column_stack([audio.rms, audio.centroid, audio.onset])
    if not len(points):
        return (), np.zeros(0, dtype=int)
    k = max(1, min(count, len(np.unique(points.round(4), axis=0))))
    model = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(points)
    centers = model.cluster_centers_
    order = np.argsort(centers[:, 0] + 0.5 * centers[:, 2])
    rank = np.empty(k, dtype=int)
    rank[order] = np.arange(k)
    labels = rank[model.labels_]

    colors = palette.byVividness() or ((255, 255, 255),)
    names = STATE_NAMES if k == len(STATE_NAMES) else tuple(f"Estado {i + 1}" for i in range(k))
    states = []
    for stateId in range(k):
        center = centers[order[stateId]]
        colorIndex = round(stateId * (len(colors) - 1) / max(1, k - 1))
        states.append(VisualState(
            id=stateId, name=names[stateId], color=tuple(int(c) for c in colors[colorIndex]),
            energy=float(center[0]), brightness=float(center[1]), attacks=float(center[2]),
            share=float(np.mean(labels == stateId)),
        ))
    return tuple(states), labels
