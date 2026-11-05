# Revisión del monitor interactivo

> Registro de las pruebas locales anteriores a subir la rama. El estado actual de revisión e integración se describe en README.md.


Esta revisión corresponde al rediseño local con índigo y lavanda. El modelo, las seis entradas, las etiquetas y la reserva de prueba se conservaron. No se modificó el Word ni el repositorio original y no se publicaron cambios.

## Interfaz

El inicio abre Monitor; las otras secciones son El proyecto y Código. El monitor contiene una representación SVG ilustrativa de maquinaria, cinco mediciones con pequeñas gráficas, un gráfico de variable seleccionable, alertas recientes y la tabla de comparación posterior. La representación no simula una máquina física ni una conexión a sensores.

El servidor entrega las últimas 60 observaciones realmente procesadas. Las gráficas conservan ese orden de reproducción, que no debe interpretarse como una serie temporal de una misma máquina. Los puntos de alerta indican una predicción de falla; el historial conserva las falsas alarmas y las omisiones. Las alertas recientes muestran hasta cinco de las predicciones positivas de la ventana de 60 registros, mientras el contador de sesión mantiene todas las alertas.

Los títulos usan Space Grotesk, los textos Inter y las cifras una tipografía monoespaciada del sistema. Los archivos de fuente se sirven localmente e incluyen sus licencias y procedencia en web/fonts/. La animación de reproducción se detiene al pausar y se respeta la preferencia de movimiento reducido.

## Comprobaciones

- Las 21 pruebas de scripts/verify_simulation.py pasaron. Se incluyó la comprobación de la ventana de 60 UDI al terminar los 2 000 registros y de su limpieza al reiniciar. Las predicciones y los archivos protegidos permanecieron iguales.
- Las ocho pruebas de scripts/verify_portal.py pasaron, incluyendo los nuevos recursos de JavaScript, CSS y las dos fuentes locales. Los resultados están en monitor_simulation_checks.json y portal_checks.json.
- El navegador confirmó la carga efectiva de Space Grotesk e Inter y la ausencia de errores de JavaScript en la revisión.
- Al procesar manualmente 22 registros se mostró la alerta de UDI 1392, con 2 737 rpm y 8,8 Nm. El gráfico mostraba 22 registros, del UDI 2998 al UDI 1392. Elegir Torque cambió su último valor a 8,8 Nm.
- Reiniciar dejó cero registros, cero alertas, mediciones vacías, cero trazos de datos y ausencia de puntos en las gráficas pequeñas.
- La reproducción automática a 0,2 segundos activó la animación. Al pausar en el registro 81 se detuvo la animación y la gráfica mostró exactamente los últimos 60 registros, del UDI 1392 al UDI 586, con último valor de 2 001 rpm.
- A 390 píxeles de ancho, la página no presentó desbordamiento horizontal. Se revisaron Monitor, El proyecto y Código; la sesión siguió en 81 registros al regresar al monitor y el gráfico se reajustó al ancho visible. Esta fue una revisión de tamaño de pantalla, no una prueba en un teléfono físico.

## Capturas

- [Monitor con alerta](evidence_monitor/monitor_alerta.png).
- [Vista estrecha](evidence_monitor/monitor_movil.png).
- [Monitor completo final](evidence_monitor/monitor_completo.png).
- [Vista final de escritorio](evidence_monitor/monitor_final.png).

Las capturas de evidence_71/ corresponden a las versiones visuales anteriores. Los tiempos son mediciones locales y no garantías industriales. La reproducción de la reserva ya evaluada no crea otra evaluación independiente del modelo. El despliegue y la publicación siguen pendientes.
