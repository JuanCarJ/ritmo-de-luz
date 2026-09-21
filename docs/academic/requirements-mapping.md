# Trazabilidad con el enunciado

## Requisitos del Proyecto 2

| Requisito | Implementación | Evidencia |
|---|---|---|
| Imagen base JPG/PNG | `fitImage()` recorta al centro a 1280×720 sin deformar | `pipeline.py` |
| Audio de 20–40 s | Clips de entrada de 30 s en `artifacts/demo/audio/` | `generate_demo.py` |
| 6–12 bandas; energía por hop | 12 bandas mel (`librosa.feature.melspectrogram`), hop de 512 muestras | `audio.py`, `test_features_are_12_mel_bands…` |
| Normalizar y suavizar | dB → percentiles 5–95 por banda → envolvente de ataque y caída | `percentileNormalize`, `attackRelease` y sus pruebas |
| Mapear bandas a mosaicos | Rejilla 3 × 4: banda *i* → mosaico *i*, de graves (abajo a la izquierda) a agudos (arriba a la derecha) | `bandCell`, `test_band_layout…` |
| Transformaciones suaves | Brillo y zoom por mosaico en función de la energía suavizada; interpolación a 30 FPS | `buildMosaicFrame`, `perFrame` |
| MP4 ≥ 10 FPS y 10–20 s | 30 FPS, 20 s (tramo de mayor energía), H.264 + AAC | `renderVideo`, `manifest.json` |
| Reacción visible a ataques | `onset_detect` → destello con caída de 0,18 s | Correlación ataque–brillo del video: 0,92 / 0,90 / 0,49 |
| ML opcional | K-Means en la paleta (5 colores) y en los estados acústicos (4) | `palette.py`, `states.py`, `test_palette_and_states_are_ordered` |

## Justificación del mapeo

- **Posición:** las bandas se leen como un ecualizador. Los graves ocupan la fila de abajo
  (el "peso" del sonido) y los agudos la de arriba.
- **Brillo:** es la variable que el ojo detecta más rápido. Antes de aplicarla, cada banda se
  separa del promedio del instante (contraste espectral) y pasa por una curva gamma de 1,4,
  para que los tramos suaves queden oscuros y los golpes destaquen.
- **Zoom:** es un segundo canal redundante que da sensación de pulso sin deformar la imagen.
- **Destello global:** refleja los ataques, que el enunciado pide hacer visibles.
- **Juntas con el color del estado K-Means:** muestran el carácter del fragmento (reposo o
  clímax) con colores de la propia foto.

## Rúbrica

| Criterio | Dónde se ve |
|---|---|
| Cálculo y normalización de bandas (30) | `audio.py`; figuras *Espectrograma mel* y *Suavizado* en la interfaz |
| Diseño del mapeo (20) | Mapa 3 × 4 en vivo en la interfaz; esta sección |
| Calidad visual y sincronización (20) | Video de la demo; figura *Sincronía comprobada* |
| Estructura y rendimiento (10) | `core/` sin dependencias web; render cuadro a cuadro (sin acumular en RAM), unos 15 s por video |
| Video explicativo (20) | Pendiente de grabación |
