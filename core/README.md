# `ritmo_de_luz_core`

Paquete Python sin dependencias web. Recibe una imagen y un audio y devuelve un MP4 más el
análisis que usa la interfaz.

```python
from ritmo_de_luz_core import renderVideo

analysis = renderVideo("samples/dalia.jpg", "artifacts/demo/audio/menu-loop.wav", "out.mp4")
print(analysis["syncScore"], analysis["tempo"])
```

- `audio.analyzeAudio`: 12 bandas mel en dB, normalizadas y suavizadas; RMS, centroide,
  ataques, destello y tempo.
- `palette.extractPalette`: 5 colores dominantes con K-Means.
- `states.clusterStates`: 4 estados acústicos con K-Means, ordenados por energía y
  asociados a los colores de la paleta.
- `pipeline.buildMosaicFrame`: compone un cuadro 3 × 4 a partir de las 12 energías.
- `pipeline.renderVideo`: tramo de 20 s → análisis → cuadros → MP4 con audio.
