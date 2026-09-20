# Trazabilidad académica

| Requisito | Implementación | Evidencia |
|---|---|---|
| 6–12 bandas de frecuencia | 12 bandas normalizadas en `core/ritmo_de_luz_core/audio.py` | MP4 y prueba del core |
| Mapeo a imagen | mosaico 4 × 6 en `pipeline.py` | MP4 demo |
| Transformaciones suaves | interpolación lineal de energía por frame, brillo y escala | MP4 demo |
| MP4 a FPS fijo | `generateMosaicMp4()` a 30 FPS | `manifest.json` |
| Reacción a onsets | envolvente de onset incluida en el análisis y estados acústicos | prueba del core |
| Machine learning opcional | K-Means de estados acústicos y paleta de imagen, con fallback determinista | manifiesto y prueba del core |

La lógica académica es independiente de FastAPI, Docker y Caddy. La aplicación
solo orquesta el mismo pipeline reproducible.
