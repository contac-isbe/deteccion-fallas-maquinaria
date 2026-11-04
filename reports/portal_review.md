# Revisión de la alternativa local del punto 7.1

> Registro de las pruebas locales anteriores a subir la rama. El estado actual de revisión e integración se describe en README.md.


Base clonada: `4406aae`. Carpeta independiente: `version-local-alternativa`. Se prepararon los contenidos de las tres pestañas sin commits, ramas nuevas, pull requests, push ni despliegue. El Word y el repositorio original permanecieron sin cambios.

## Comprobaciones ejecutadas

- `scripts/verify_simulation.py`: 21 comprobaciones superadas, incluidas las 2 000 predicciones idénticas a la evaluación del notebook 03. El resultado de esta ejecución pertenece a esta copia: `reports/simulation_checks.json`.
- `scripts/verify_portal.py`: ocho comprobaciones superadas. Se comprobaron estructura de pestañas, recursos, metadatos coherentes con la evaluación histórica, 19 archivos consultables, descargas, rechazo de rutas no permitidas, integración con la sesión y conservación de archivos protegidos. Evidencia en `reports/portal_checks.json`.
- Revisión del navegador: navegación entre Documentación, Código y Ejecución y pruebas; selección de `src/preparation.py`; correspondencia entre el archivo elegido y el texto mostrado; avance manual hasta UDI 1392, en el registro 22, con alerta de falla.
- Revisión a 390 píxeles de ancho: Documentación y Código sin desbordamiento horizontal de la página; controles visibles en Ejecución; la sesión conservó los 22 registros y su alerta al cambiar de pestaña. Se probó la tecla Home desde la última pestaña y volvió a Documentación. La revisión estrecha es una emulación de tamaño de pantalla, no una prueba en un teléfono físico.
- Descarga del informe desde la pestaña Documentación: el archivo descargado coincide en bytes con `docs/Informe - Proyecto de IA.docx`.

## Capturas

- [Documentación](evidence_71/documentacion.png).
- [Visor de código](evidence_71/codigo.png).
- [Ejecución y alerta](evidence_71/ejecucion.png).
- [Documentación en pantalla estrecha](evidence_71/documentacion_movil.png).
- [Código en pantalla estrecha](evidence_71/codigo_movil.png).
- [Ejecución en pantalla estrecha](evidence_71/ejecucion_movil.png).
- [Vista final de escritorio](evidence_71/portal_final.png).

## Alcance

La alternativa utiliza las mismas versiones de dependencias, el mismo modelo y las mismas particiones. El entorno virtual se creó en esta carpeta y recibió una copia de los paquetes ya instalados, sin dependencias web nuevas ni reentrenamiento. Las huellas del modelo y del Word coinciden con las copias del repositorio original.

Las pestañas preparan los contenidos solicitados en 7.1.1, 7.1.2 y 7.1.3. El requisito de publicación en GitHub del apartado 7.1 aún no está completado, y el despliegue del 7.2 sigue pendiente. La sesión es compartida por el proceso local; consultar documentación o código no pausa automáticamente una reproducción en marcha. Las pruebas de estructura y navegación no equivalen a un estudio de usabilidad con participantes ni a compatibilidad con todos los dispositivos.

El servidor utilizado para la revisión se detuvo al finalizar. Para usar la alternativa, ejecutar `ABRIR_PORTAL.cmd` o el comando del README y abrir `http://127.0.0.1:8771`.
