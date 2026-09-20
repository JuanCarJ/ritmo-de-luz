# Worker de render

El worker toma trabajos JSON de `runtime/jobs`, invoca `core` y escribe MP4 en
`runtime/outputs`. En modo local la API lo inicia como hilo embebido; en Docker
se ejecuta como servicio separado.

