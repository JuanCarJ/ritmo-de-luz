# Publicación en servidor

La publicación queda bloqueada hasta la aprobación local del usuario.

Cuando exista autorización explícita, el operador deberá:

1. Confirmar la rama y SHA revisados.
2. Confirmar que el árbol está limpio.
3. Verificar la ruta y el volumen de datos en `servidor_do_1`.
4. Configurar el DNS y añadir el host al Caddy administrado.
5. Levantar únicamente `api` y `worker` del Compose del proyecto.
6. Comprobar `/health`, `/api/demo` y la reproducción del MP4 precargado.
7. Probar un render nuevo con archivos pequeños.
8. Conservar la imagen anterior para rollback.

No se incluyen aquí secretos, credenciales SSH ni valores de producción.

