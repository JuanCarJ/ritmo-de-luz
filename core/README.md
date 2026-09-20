# `ritmo_de_luz_core`

Paquete Python puro para convertir una señal de audio y una colección de píxeles en
features, paleta, estados visuales y frames tipados. No depende de FastAPI, Docker,
Caddy ni de rutas de servidor.

`numpy` es necesario para el análisis STFT; `scikit-learn` acelera KMeans pero tiene
fallback determinista; `imageio` + ffmpeg son opcionales para `renderMp4`.

```python
from ritmo_de_luz_core import analyze
result = analyze(samples, 44_100, pixels=[(255, 0, 0), (0, 0, 255)])
```

`generateMosaicMp4(image, audio, output, sample_rate=44_100)` acepta arrays o
rutas de imagen/audio y genera un mosaico 4×6 reactivo a mel bands. La mezcla de
audio depende del backend FFmpeg disponible; el render de frames no depende de
`scikit-learn`.
