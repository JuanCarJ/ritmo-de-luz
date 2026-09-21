# Trazabilidad académica

## Evidencia técnica del Midterm

| Requisito | Implementación | Evidencia |
|---|---|---|
| 6–12 bandas de frecuencia | 12 bandas normalizadas en `core/ritmo_de_luz_core/audio.py` | MP4 y prueba del core |
| Mapeo a imagen | mosaico 4 × 6 en `pipeline.py`; cada banda mel se aplica a dos regiones | MP4 demo |
| Transformaciones suaves | interpolación lineal de energía por frame, brillo y escala | MP4 demo |
| MP4 a FPS fijo | `generateMosaicMp4()` a 30 FPS | `manifest.json` |
| Reacción a onsets | envolvente de onset incluida en el análisis y estados acústicos | prueba del core |
| Machine learning opcional | K-Means de estados acústicos y paleta de imagen, después de la ruta base; fallback determinista | manifiesto y prueba del core |

La lógica académica es independiente de FastAPI, Docker y Caddy. La aplicación
solo orquesta el mismo pipeline reproducible.

## Lectura de la rúbrica del Midterm

La solución implementa la alternativa de sincronización imagen–audio del
Midterm. El Entregable 2 anterior se usa como antecedente técnico, pero no se
presenta como el proyecto actual.

| Criterio | Cómo se demuestra aquí | Estado |
|---|---|---|
| Cálculo y normalización de bandas (30) | 12 bandas mel, RMS, centroide y onsets en `core/`; valores normalizados y suavizados. | Implementado y probado |
| Diseño del mapeo (20) | 24 mosaicos; cada banda controla brillo, escala y mezcla de color. | Implementado |
| Calidad y sincronización percibida (20) | 30 FPS, interpolación lineal entre ventanas y audio muxado cuando FFmpeg está disponible. | Demo local verificable |
| Estructura y rendimiento (10) | `core/` separado de API, worker y despliegue; proceso por cola y fallback sin ML. | Implementado |
| Explicación en video (20) | El video de entrega debe mostrar la demo y recorrer los seis pasos de la interfaz. | Pendiente de grabación |

La entrega final también requiere el informe PDF y el comprimido con código, medios
y salidas. Esos artefactos de Moodle no se sustituyen por el servidor web.
