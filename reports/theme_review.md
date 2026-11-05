# Revisión de los modos claro y oscuro

Se añadió un interruptor «Modo oscuro» en la esquina superior derecha, disponible en Monitor, El proyecto y Código. La paleta oscura conserva la identidad índigo/lavanda y adapta las superficies, textos, controles, gráficos, ilustración y estados de clasificación. No se usa un filtro de inversión de colores.

## Comprobaciones realizadas

- El interruptor cambia entre claro y oscuro y expone su estado mediante `role="switch"` y `aria-checked`.
- En el navegador se cambió a claro y se recargó: se conservó claro. Después se cambió a oscuro y se recargó: se conservó oscuro.
- El control respondió a la tecla Espacio y cambió a claro. Posteriormente se volvió a oscuro mediante clic.
- Al alternar con 22 observaciones procesadas, la sesión siguió en el registro 22 y conservó la alerta de UDI 1392. El tema no interviene en la clasificación ni cambia los datos.
- Se revisaron visualmente Monitor, El proyecto y Código en oscuro. Se corrigió el color de las instrucciones de ejecución para mejorar su contraste.
- A 390 píxeles de ancho, el interruptor permaneció visible y la página no presentó desbordamiento horizontal. Se revisaron ambos temas en ese tamaño, sin probar un teléfono físico.
- No se detectaron errores de JavaScript durante esta revisión. Las ocho comprobaciones del portal pasaron, incluyendo las nuevas rutas de estilos y script del tema.

La implementación usa la preferencia de color del sistema cuando no existe una elección guardada. La elección manual se almacena localmente cuando el navegador lo permite; un fallo de almacenamiento no impide alternar durante la sesión. También contempla cambios de la preferencia del sistema y sincronización entre pestañas. Estos últimos casos se contemplan en el código, pero no fueron emulados en la revisión del navegador.

## Capturas

- [Monitor en oscuro](evidence_monitor/modo_oscuro.png).
- [Proyecto en oscuro](evidence_monitor/modo_oscuro_proyecto.png).
- [Código en oscuro](evidence_monitor/modo_oscuro_codigo.png).
- [Oscuro en pantalla estrecha](evidence_monitor/modo_oscuro_movil.png).
- [Claro en pantalla estrecha](evidence_monitor/modo_claro_movil.png).
