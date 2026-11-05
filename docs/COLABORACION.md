# Colaboración y mantenimiento

## Procedimiento para los cambios

1. Actualizar la copia local desde main.
2. Crear una rama para el cambio propuesto.
3. Realizar y comprobar el cambio localmente.
4. Subir la rama y abrir un pull request con una descripción del cambio y su verificación.
5. Revisar el pull request antes de integrarlo en main.

Los cambios de presentación deben conservar el modelo, las variables, las métricas y las funciones verificadas. Las modificaciones del modelo requieren un experimento documentado y una evaluación válida, sin reutilizar la reserva ya consultada para seleccionar parámetros.

## Publicación

La publicación automática en Render está desactivada. Integrar un pull request no actualiza por sí solo la aplicación pública. Después de aprobar una actualización destinada a la aplicación, desplegar la versión correspondiente y comprobar los recorridos afectados. La configuración está en [DESPLIEGUE.md](DESPLIEGUE.md).

Cuando cambie el informe, conservar iguales sus copias locales y la de docs/. Los registros de pruebas anteriores se mantienen como evidencia histórica.
