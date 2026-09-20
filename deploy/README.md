# Despliegue

Esta carpeta prepara el despliegue, pero no lo ejecuta automáticamente. La
publicación en `servidor_do_1` queda bloqueada hasta la aprobación explícita del
resultado local.

- `docker/compose.local.yml`: prueba Docker local opcional.
- `docker/compose.prod.yml`: servicios API y worker para el servidor.
- `caddy/Caddyfile.example`: ruta HTTPS propuesta, pendiente de DNS y aprobación.
- `env/.env.example`: nombres de configuración sin secretos.

