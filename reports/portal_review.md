# Revisión del portal y del manual de uso

Revisión del cierre del apartado 7.1, realizada el 4 de noviembre de 2026. El rediseño conserva el modelo, las seis entradas y la reserva de AI4I 2020. La publicación de las fuentes en GitHub se distingue del despliegue externo del 7.2, que sigue pendiente.

## Comprobaciones

- La simulación superó 21 comprobaciones: las 2 000 predicciones coincidieron con el notebook 03; se conservaron 1 919 TN, 13 FP, 18 FN y 50 TP. Evidencia actual en `monitor_simulation_checks.json`.
- El portal superó ocho comprobaciones HTTP y de estructura: tres paneles asociados, recursos, metadatos, 26 archivos consultables, descargas idénticas a los originales, rechazo de rutas no permitidas, sesión conservada y archivos protegidos sin cambios. Evidencia en `portal_checks.json`.
- La descarga verificada incluye el Word, un notebook, la procedencia de los datos, la evidencia original del 6.2, la nueva evidencia del monitor y `docs/MANUAL_USUARIO.md`.
- En el navegador se abrió la guía desde Monitor, se cerró con su botón y con Escape y se regresó a una sesión que conservó su avance. La guía se revisó en claro y oscuro.
- La revisión a 390 píxeles de ancho confirmó texto ajustado y desplazamiento vertical dentro del diálogo. Es una revisión de tamaño de pantalla, no una prueba en un teléfono físico.
- Se navegó entre El proyecto, Código y Monitor; el avance manual hasta el registro 22 mostró la alerta del UDI 1392, con 2 737 rpm y 8,8 Nm.

## Evidencia visual actual

- [Documentación](portal_evidence/71-documentacion.png).
- [Código e instrucciones](portal_evidence/71-codigo.png).
- [Monitor con alerta](portal_evidence/71-monitor.png).
- [Guía en modo claro](portal_evidence/manual-light.png).
- [Guía en pantalla estrecha](portal_evidence/manual-mobile.png).

Las revisiones del rediseño y del tema están en `monitor_review.md` y `theme_review.md`. Sus capturas anteriores se conservan como evidencia histórica. La evidencia original del 6.2 permanece en `simulation_checks.json` y `simulation_review.md`; las ejecuciones posteriores no sustituyen sus tiempos.

## Límites

El servidor escucha únicamente en el propio equipo. Las pestañas conectadas comparten sesión y cambiar de sección no pausa la reproducción. La reserva es sintética y ya fue evaluada; reproducirla no constituye una nueva prueba independiente. No se modificó ni reentrenó el modelo durante esta revisión.
