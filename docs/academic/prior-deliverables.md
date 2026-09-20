# Relación con los entregables previos

Esta entrega parte de los dos trabajos previos conservados en el proyecto de la
asignatura (`UCO/S9/Electiva`). No copia sus aplicaciones sin relación: reutiliza
los conceptos que sí sirven para el objetivo del sincronizador imagen-audio.

## Entregable 1: visión por computador

El trabajo anterior resolvió dos casos independientes: conteo de personas con
YOLOX y detección/OCR de placas con `platerec`. Esos modelos reciben una imagen
para detectar objetos o texto. Ritmo de Luz recibe una imagen como superficie
visual, no como objeto que deba reconocerse; por eso YOLO y OCR quedan fuera del
pipeline. La decisión conserva el alcance del Proyecto 2 del enunciado y evita
añadir una técnica que no mejora la sincronización.

## Entregable 2: procesamiento de audio

El trabajo anterior documentó forma de onda, RMS, recorte de silencio, muestreo,
cuantificación, FFT, filtrado, espectrograma y características espectrales. Ritmo
de Luz reutiliza la parte necesaria para animación temporal: el audio se divide en
ventanas con STFT, se calculan energía RMS, centroide, ataques y 12 bandas mel, y
después se normaliza, suaviza e interpola para controlar los mosaicos a 30 FPS.

La interfaz muestra esos resultados calculados para la demo: la forma de onda, el
espectrograma de bandas mel, RMS antes/después de normalizar, el mosaico 4 × 6,
la salida MP4 y los estados agrupados por K-Means. No se dibujan gráficas de
relleno: cada visual se alimenta del archivo de análisis generado por `core/`.

## Correspondencia con la entrega actual

| Antecedente | Se conserva aquí | Evidencia visible |
|---|---|---|
| Forma de onda y RMS | Ventanas temporales y energía normalizada | Entrada y Normalización |
| FFT/espectrograma | STFT y banco de 12 bandas mel | Frecuencias |
| Filtrado/ataques | Centroide y onset para describir cambios | Análisis del core y estados |
| Procesamiento de imagen | Imagen como fuente de píxeles y mosaico | Entrada y Mapeo 4 × 6 |
| Modelos YOLO/OCR | No se incluyen | Fuera del alcance del sincronizador |

