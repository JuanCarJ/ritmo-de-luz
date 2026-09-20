# Ejecución local

La ruta recomendada para el profesor no requiere Docker:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,ml]'
python scripts/check_environment.py
python scripts/generate_demo.py
python scripts/run_local.py
```

Después se abre `http://127.0.0.1:8000`. La interfaz sirve el artefacto demo
precargado y permite iniciar un render adicional.

## Docker opcional

Para comprobar el empaquetado local:

```bash
docker compose -f deploy/docker/compose.local.yml up --build
```

Esto es opcional y no forma parte del requisito para evaluar el proyecto.

