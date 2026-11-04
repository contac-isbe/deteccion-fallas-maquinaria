> Registro histórico de la interfaz base del apartado 6.2. Los tiempos descritos aquí pertenecen a aquella ejecución. Para las comprobaciones de esta alternativa local, consultar `portal_review.md`, `portal_checks.json` y la nueva ejecución de `simulation_checks.json`.

# Comprobación de la simulación local

La simulación reproduce la reserva de 2 000 observaciones de AI4I 2020 con el árbol de decisión ya seleccionado. Se utiliza una sesión compartida por servidor local, sin conexión a maquinaria física y sin entrenamiento. Este documento registra evidencia técnica para desarrollar el apartado 6.2 del informe; no lo sustituye.

## Evidencia automática

Comando: `python scripts/verify_simulation.py`, desde la raíz con el entorno del proyecto.

La ejecución registrada en [simulation_checks.json](simulation_checks.json) superó 21 comprobaciones. Se compararon las 2 000 predicciones con `test_predictions.csv`, conservando el orden de UDI y las etiquetas. Coincidieron todos los resultados: 1 919 verdaderos negativos, 50 verdaderos positivos, 13 falsos positivos y 18 falsos negativos. Las 63 alertas dependen de la predicción, incluidas las 13 falsas alarmas; las fallas omitidas no activan una alerta.

Se comprobaron entradas incompletas, mediciones ausentes o infinitas, tipo desconocido, valores fuera del dominio, identificadores duplicados, etiquetas no binarias, reserva incompleta o reordenada y mediciones alteradas. Una carga inválida se rechaza sin cambiar el avance. La reserva correcta se acepta y reinicia la sesión.

Se verificaron inicio, pausa y continuación con el trabajador de reproducción y el servidor HTTP reales. Durante la pausa no avanzó el contador. También se comprobó el reinicio, el avance manual, el final de la reserva y la descarga de CSV. Las huellas del modelo, selección, evaluación histórica, predicciones originales, dataset y reserva permanecieron idénticas antes y después.

## Revisión del navegador

Se revisó la interfaz local en el navegador integrado de Codex. Se comprobó:

- Avance manual inicial: UDI 2998, tipo L y resultado sin falla. Se mostraron las cinco mediciones con sus unidades y su comparación posterior.
- Ausencia de archivo: `Validar y cargar CSV` mostró «Selecciona un archivo CSV de prueba».
- CSV con encabezado incorrecto: se seleccionó un archivo de prueba y la interfaz mostró el mensaje de columnas incorrectas; conservó el registro procesado.
- Avance manual hasta el registro 22: UDI 1392, alerta «con falla» y etiqueta real con falla. La tabla mostró también la omisión de UDI 4852, sin esconderla.
- Descarga mediante el enlace de exportación: el CSV descargado contenía 22 filas y terminó en UDI 1392 con predicción 1, aunque la pantalla solo mostraba las últimas ocho filas.
- Reinicio: contador cero, mediciones vacías y ausencia de predicciones anteriores. Inicio automático a 0,2 segundos: contador en avance y controles adecuados; pausa observada en el registro 41. El contador permaneció en 41 durante la preparación de la documentación. Se pulsó Continuar y una nueva pausa mostró el registro 142.

Capturas originales del navegador:

- [Estado sin falla](evidence/simulacion_sin_falla.png).
- [Alerta de falla](evidence/simulacion_alerta.png).
- [Rechazo del CSV](evidence/simulacion_error_csv.png).

La carga correcta se comprobó por la API y la validación del backend; el flujo de selección de archivos del navegador se ejercitó con el CSV incorrecto. No se realizó un estudio de usabilidad con usuarios ni se verificaron todos los navegadores.

## Correspondencia con los requisitos del informe

| Requisito | Evidencia disponible |
| --- | --- |
| RF1: carga y validación | Reserva verificada al inicio; carga correcta e incorrecta en las pruebas; mensaje de rechazo en pantalla. |
| RF2: transformaciones y clasificación | Se utiliza el pipeline guardado. Se verificó que `predict` recibe solo las seis variables; todas las predicciones coinciden con el notebook 03. |
| RF3: reproducción y controles | Inicio, pausa, continuación, avance y reinicio comprobados. Orden de UDI conservado en los 2 000 registros. Mediciones y unidades visibles. |
| RF4: alertas | Una alerta por predicción positiva. Se comprobaron 63 en el recorrido completo y una alerta visible de UDI 1392. |
| RF5: registro exportable | CSV completo con identificadores, entradas, etiqueta posterior, predicción y tiempos; descarga comprobada por HTTP y desde el navegador. |
| RF6: métricas | Las métricas finales permanecen en el notebook 03. Los conteos de la simulación completa coinciden con su matriz de confusión; no se redefine la evaluación final. |
| RNF1: reproducibilidad | Mismas versiones y huellas comprobadas. Scripts de inicio y verificación documentados. |
| RNF2: consistencia de preparación | Transformaciones dentro del pipeline congelado y entradas en el mismo orden; sin ajustes durante la simulación. |
| RNF3: legibilidad | Revisión visual de mediciones, unidades y estados con texto e icono además de color. No equivale a una evaluación de usabilidad con usuarios. |
| RNF4: medición de tiempos | Promedio y percentil 95 de predicción y procesamiento sobre 2 000 registros; recorrido HTTP medido en 20 pasos. Definiciones y entorno en el JSON. |

## Tiempos y límites de interpretación

La ejecución registrada obtuvo media de 1,85 ms y percentil 95 de 2,60 ms para la llamada al pipeline. La selección, validación, predicción y construcción del registro tuvieron media de 3,51 ms y percentil 95 de 4,94 ms. El recorrido HTTP local se midió por separado con 20 solicitudes: media de 22,87 ms y percentil 95 de 31,77 ms. Los valores completos, el equipo y las versiones figuran en el JSON; una nueva ejecución puede producir otros tiempos.

Los cronometrajes no incluyen la actualización visual del navegador ni las pausas de reproducción. No se definió un tiempo máximo exigible y no se garantiza tiempo real industrial. Las diferencias frente a los tiempos históricos del notebook 03 no demuestran una mejora del modelo, que permaneció sin cambios.

La carga acepta únicamente la reserva completa original, no archivos externos. Una sesión se conserva solo mientras el proceso local está activo; reiniciar o detener el proceso borra los resultados no exportados. No se ha validado el sistema en maquinaria física. El dataset es sintético, se conservan las discrepancias de etiquetado conocidas y esta reproducción no aporta una nueva evaluación independiente.
