# Guía para explicar Ritmo de Luz

Guion de apoyo para el video (≈ 6 min). En la página solo están los títulos de cada fase; aquí va
lo que conviene decir en cada una y qué señalar en pantalla.

## Apertura (≈ 30 s)

- Qué es: una imagen dividida en 12 mosaicos (3 × 4) que reacciona a 12 bandas de frecuencia
  del audio. Es el Proyecto 2 del Midterm (Image–Audio Synchronizer).
- Muestra el video arriba con **Escuchar con sonido**. Señala la consola de la derecha: barras
  de las 12 bandas, mapa de mosaicos, indicador de golpe y estado K-Means, todo sincronizado.
- Frase puente: "Ahora veamos cómo se llega a este resultado, fase por fase".
- Puedes usar **Recorrer los pasos**: avanza sola cada 7 s con el video sonando.

## Diagrama de flujo (≈ 20 s)

Dos carriles que se juntan en el cuadro final:

- **Imagen:** recorte → 5 colores.
- **Audio:** tramo de 20 s → 12 bandas en dB → 0 a 1 → suavizado; del mismo tramo salen los
  golpes y los 4 estados.
- Todo converge en el paso 8, que compone 30 cuadros por segundo.

---

## 1 · Lectura — Foto y audio de entrada

- **Entra:** una foto (JPG/PNG) y un audio (WAV, FLAC, OGG o MP3).
- **Hace:**
  - Recorta la foto al centro en 16:9 y la escala a 1280 × 720 **sin deformarla**
    (`ImageOps.fit`). Señala el recuadro sobre la foto original.
  - Elige los **20 s con más energía** del audio: suma la energía en ventanas de 0,5 s y toma el
    tramo de 20 s con mayor total. Señala el tramo resaltado en la forma de onda.
- **Sale:** imagen de 1280 × 720 (pasa a 2 y 8) y tramo de 20 s (pasa a 3, 6 y 7).
- **Por qué:** el enunciado pide un audio de entrada de 20–40 s y un MP4 de 10–20 s. Los clips
  de entrada duran 30 s y el video, 20 s.

## 2 · Extracción de color — Paleta de la imagen con K-Means

- **Entra:** los píxeles de la imagen recortada (se muestrean ~20 000).
- **Hace:** K-Means agrupa los píxeles por su color RGB en 5 grupos. El centro de cada grupo es
  un color dominante y su peso es la fracción de píxeles que tiene.
- **Sale:** 5 colores ordenados de **apagado a vivo** (saturación × valor en HSV). Ese orden se
  usa en el paso 7.
- **Qué señalar:** la barra superior (ancho = % de píxeles) y la fila inferior (orden de viveza).
- **Idea clave:** es aprendizaje no supervisado: nadie etiqueta los colores; el algoritmo agrupa
  lo que se parece.

## 3 · Transformación — Del sonido a 12 bandas de frecuencia

- **Entra:** el tramo de 20 s.
- **Hace:**
  - STFT con ventanas de 2048 muestras (46 ms) cada 512 muestras (11,6 ms), es decir, unas
    86 lecturas por segundo.
  - Banco de **12 filtros mel** entre 30 Hz y 16 kHz (`librosa.feature.melspectrogram`). La
    escala mel es más fina en graves y más gruesa en agudos, como el oído.
  - La potencia se pasa a **dB** (`power_to_db`), que comprime el rango dinámico como lo
    percibimos.
- **Sale:** energía de 12 bandas, 86 veces por segundo (pasa a 4).
- **Qué señalar:** espectrograma; abajo graves, arriba agudos; más claro = más energía.
- **Rúbrica:** "Correct band computation" (30 pts). Aquí se ve que las bandas son mel reales.

## 4 · Estandarización — Cada banda en escala 0–1

- **Entra:** los dB de cada banda.
- **Hace:** reescala cada banda por separado entre sus **percentiles 5 y 95**. Lo que queda por
  debajo es 0 y lo que queda por encima es 1.
- **Por qué percentiles y no mínimo–máximo:** un pico aislado no aplana el resto. Y por banda,
  porque los agudos tienen mucha menos energía que los graves; sin esto, los mosaicos de agudos
  casi no se moverían.
- **Sale:** 12 valores 0–1 comparables entre sí (pasa a 5).
- **Qué señalar:** en la gráfica de dB, las dos líneas punteadas (p5 y p95); abajo, la misma
  banda ya en 0–1. Cambia de banda con el selector.

## 5 · Suavizado — Movimiento sin parpadeo

- **Entra:** las bandas en 0–1.
- **Hace:** filtro de envolvente de **ataque rápido y caída lenta**: cuando la energía sube, la
  sigue un 60 % por lectura (casi de inmediato); cuando baja, solo un 8 % (se apaga en
  ~0,15 s). Después interpola esas ~86 lecturas por segundo a los 30 cuadros por segundo del
  video.
- **Sale:** un valor por banda y por cuadro, sin parpadeo (pasa a 8).
- **Qué señalar:** la curva gris (antes) salta; la ámbar (después) sube igual de rápido pero
  cae suave.
- **Rúbrica:** "Mapping design (clear, justified, smooth)" y "Interpolate energies for
  smoothness".

## 6 · Detección — Golpes del audio

- **Entra:** el tramo de 20 s.
- **Hace:** `onset_strength` mide los aumentos bruscos de energía espectral y `onset_detect`
  marca cada golpe. Cada golpe dispara un **destello** proporcional a su fuerza que se apaga en
  0,18 s.
- **Sale:** la lista de golpes y la curva de destello (pasa a 8).
- **Qué señalar:** las marcas arriba (golpes detectados), la curva ámbar (fuerza) y el área
  verde (destello).
- **Rúbrica:** "Ensure visible reaction to beats or onsets".

## 7 · Agrupación — Estados del audio con K-Means

- **Entra:** para cada instante del tramo, energía (RMS), brillo espectral (centroide) y fuerza
  de golpe.
- **Hace:** K-Means agrupa las ventanas del tramo en 4 perfiles y los ordena de menor a mayor
  intensidad (energía + golpes): Calma, Movimiento, Enérgico y Fuerte.
- **Sale:** un perfil por instante. El más tranquilo toma el color más apagado de la paleta
  (paso 2) y el más intenso, el más vivo (pasa a 8).
- **Qué aporta:** las bandas dicen **qué suena ahora**; K-Means dice **en qué parte de la
  canción estamos**, sin umbrales puestos a mano. Así el video cambia de carácter cuando cambia
  la música. Aquí se unen imagen y audio.
- **Qué señalar:** la línea de tiempo de colores y las 4 tarjetas (con el % del tramo que ocupa
  cada estado). La tarjeta del estado actual se resalta mientras suena.

## 8 · Composición — Del análisis al video

- **Entra:** imagen (1), bandas suavizadas (5), destellos (6) y estados (7).
- **Hace:** compone 600 cuadros (30 FPS × 20 s) con cuatro reglas:
  1. **Banda → su mosaico:** la energía controla el brillo (0,22× a 1,25×) y el zoom (hasta
     +18 %) de su región de la imagen. Antes se aplica contraste espectral (cada banda se
     separa del promedio del instante) y una curva gamma de 1,4, para que lo suave quede oscuro
     y los golpes destaquen.
  2. **Posición:** banda 1 (graves) abajo a la izquierda, banda 12 (agudos) arriba a la
     derecha, como un ecualizador.
  3. **Golpe → destello** que aclara todo el cuadro.
  4. **Estado → color de las juntas** entre mosaicos.
- **Sale:** MP4 de 1280 × 720, 30 FPS, 20 s, H.264 + AAC con el audio original (FFmpeg incluido
  en `imageio-ffmpeg`). Los cuadros se escriben uno a uno, sin acumularlos en memoria
  (~15 s por video).
- **Comprobación:** correlación entre la fuerza de los golpes del audio y la subida de brillo del
  video. Señala las dos curvas y el número.

## Cifras de las demos

| Demo | Imagen | Tempo | Golpes | Sincronía |
|---|---|---|---|---|
| Menu Loop | dalia.jpg | 129 BPM | 87 | 0,92 |
| Cyberpunk Moonlight Sonata | aurora.jpg | 108 BPM | 120 | 0,92 |
| Battle Theme A | carina.jpg | 144 BPM | 114 | 0,87 |
| Space Ranger | pagoda.jpg | 162 BPM | 94 | 0,90 |
| Peaceful Forest | coral.png | 126 BPM | 46 | 0,54 |

Peaceful Forest tiene la sincronía más baja porque casi no tiene golpes: el video responde sobre
todo a cambios lentos de energía. Es un buen contraste para mostrar.

## Cierre (≈ 30 s)

- Usa **Usar mis archivos** para mostrar que funciona con cualquier imagen y audio (tarda
  15–40 s).
- Resumen: 12 bandas mel → estandarización → suavizado → 12 mosaicos; golpes → destello;
  K-Means en imagen y audio → color de las juntas.
- Ejecución para el profesor: doble clic en `Iniciar_Mac.command` o `Iniciar_Windows.bat`.
