# Ritmo de Luz

**El sonido se convierte en luz.**

Ritmo de Luz es la entrega del Midterm: una aplicación de investigación multimedia que analiza un audio,
extrae energía y bandas de frecuencia, y transforma una imagen en una animación
de mosaicos sincronizada con el sonido. La ruta base es determinista y cumple el
sincronizador visual; como segunda capa opcional, K-Means agrupa estados acústicos
y colores para enriquecer el ambiente visual. Se activa con `ENABLE_ML=true`.

## Ver el resultado

La demo pública se publicará en una URL dedicada cuando la versión local haya sido
probada y aprobada. El servidor tendrá un MP4 demo precargado para que la aplicación
sea evaluable desde el primer clic, sin esperar un render nuevo.

## Ejecutar localmente sin Docker

Requisitos: Python 3.11+, FFmpeg (o `imageio-ffmpeg`) y un navegador.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,ml]'
python scripts/check_environment.py
python scripts/run_local.py
```

Abrir <http://127.0.0.1:8000>. La página incluye la demo preparada y un recorrido
para procesar archivos propios.

La interfaz usa Tailwind CSS compilado dentro de `apps/web/static/tailwind.css`.
Si se cambian clases de la interfaz, regenerarlo con:

```bash
npm install
npm run build:css
```

## Ejecutar el pipeline académico

```bash
python scripts/generate_demo.py
```

El pipeline produce tres MP4, un póster y un manifiesto reproducible en
`artifacts/demo/`. Las features, la paleta y los estados se calculan dentro de
`core/` y se pueden inspeccionar ejecutando sus pruebas.

## Estructura

- `core/`: análisis de audio, imagen, ML y renderizado; no conoce Docker ni HTTP.
- `apps/api/`: API local y pública.
- `apps/worker/`: trabajos de render largos.
- `apps/web/`: interfaz web.
- `deploy/`: Docker Compose, Caddy y scripts operativos.
- `docs/academic/`: trazabilidad entre requisitos, conceptos y resultados.
- `docs/operations/`: ejecución y publicación; no contiene secretos.

## Estado de despliegue

El despliegue en `servidor_do_1` está deliberadamente deshabilitado hasta que la
demo local sea probada y aprobada. `deploy_enabled: false` en `delivery.yaml` es
una barrera explícita de esta etapa.
