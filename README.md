# Ritmo de Luz

Midterm, Proyecto 2 (Image–Audio Synchronizer). Una foto se divide en 12 mosaicos
(3 × 4). Cada mosaico sigue a una de las 12 bandas mel del audio: se ilumina y se acerca
cuando su banda suena, y los golpes del audio aclaran todo el cuadro.

## Ejecutar (un paso)

Requisito: Python 3.11 o superior. No hace falta instalar FFmpeg.

- **macOS:** doble clic en `Iniciar_Mac.command`. Si macOS lo bloquea: clic derecho → Abrir.
- **Windows:** doble clic en `Iniciar_Windows.bat`.

La primera vez se crea `.venv` y se instalan las dependencias (1–3 min). Luego se abre el
navegador en <http://127.0.0.1:8000> con el video de la demo ya reproduciéndose.
Los tres ejemplos vienen pregenerados; con **Usar mis archivos** se genera uno nuevo
(15–40 s).

Desde una terminal, lo equivalente es:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_local.py
```

## Qué hace el pipeline

1. **Tramo:** elige los 20 s con más energía del audio (el video debe durar 10–20 s).
2. **Bandas:** STFT (n_fft 2048, hop 512) → 12 bandas mel (30 Hz–16 kHz) con `librosa`,
   convertidas a dB.
3. **Normalización:** cada banda se lleva a 0–1 entre sus percentiles 5 y 95, así que un
   pico aislado no aplana el resto.
4. **Suavizado:** envolvente de ataque rápido y caída lenta (sube en un hop y cae en unos
   0,15 s); después se interpola a los instantes exactos de cada cuadro (30 FPS).
5. **Ataques:** `onset_strength` + `onset_detect`; cada ataque produce un destello con caída
   exponencial.
6. **Mapeo:** banda 1 (graves) abajo a la izquierda y banda 12 (agudos) arriba a la derecha.
   La energía controla el brillo (0,22×–1,25×) y el zoom (hasta +18 %) del mosaico.
7. **K-Means:** agrupa los píxeles en 5 colores dominantes y los instantes del audio
   (RMS, centroide, ataque) en 4 perfiles, de Calma a Fuerte. El perfil más enérgico toma
   el color más vivo de la foto y lo pinta en las juntas.
8. **Salida:** MP4 1280×720, 30 FPS, H.264 + AAC; audio unido con el FFmpeg de `imageio-ffmpeg`.

La interfaz muestra, sincronizado con el video, lo que calculó el pipeline: bandas, mapa
de mosaicos, ataques y estado K-Means. La sección plegable *Cómo se calcula cada cuadro*
muestra el espectrograma, el efecto del suavizado y la correlación entre ataques del audio
y brillo del video (0,90 en Menu Loop y Space Ranger; 0,49 en Peaceful Forest, que casi no
tiene golpes).

## Estructura

- `core/ritmo_de_luz_core/`: análisis (`audio.py`), paleta (`palette.py`), estados
  (`states.py`) y render (`pipeline.py`). No depende de la web.
- `apps/api/`, `apps/worker/`: servidor local y cola de renders.
- `apps/web/static/`: interfaz (HTML, CSS y JS sin compilación).
- `scripts/generate_demo.py`: regenera las tres demos de `artifacts/demo/`.
- `samples/`: fotos y audios originales; créditos en `docs/academic/media-attributions.md`.
- `tests/`: `python -m pytest -q`.
