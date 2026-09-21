# Ejecución local

Ruta recomendada para el profesor: doble clic en `Iniciar_Mac.command` o en
`Iniciar_Windows.bat`. El script crea `.venv`, instala `requirements.txt`, genera las demos
si faltan y abre <http://127.0.0.1:8000>.

Manual:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/run_local.py        # PORT=8001 para otro puerto, NO_BROWSER=1 para no abrir el navegador
```

Para regenerar las demos: `.venv/bin/python scripts/generate_demo.py` (unos 45 s).

## Docker opcional

```bash
docker compose -f deploy/docker/compose.local.yml up --build
```

No es necesario para evaluar el proyecto.
