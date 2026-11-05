# Manual de uso de la interfaz

Sistema de detección de fallas en maquinaria mediante aprendizaje automático.

## 1. Abrir la aplicación

Si el proyecto ya está preparado en esta computadora, abrir `ABRIR_PORTAL.cmd` o ejecutar desde la raíz:

```powershell
.\.venv\Scripts\python.exe scripts/run_simulation.py --port 8771
```

Entrar a **http://127.0.0.1:8771** en el navegador y mantener la terminal abierta. Para detener el servidor, presionar **Ctrl+C** en esa terminal. El botón **Guía de uso** abre las instrucciones rápidas dentro de la página.

`127.0.0.1` corresponde al propio equipo. Este enlace local no permite que otra persona entre desde su computadora o celular. El alojamiento con un enlace externo corresponde al despliegue del apartado 7.2 y todavía está pendiente.

### Primera ejecución en otra computadora

Se necesita Python 3.12. Clonar o descargar el repositorio completo y abrir su carpeta en VS Code o una terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/execute_notebook.py 01_analisis_preparacion.ipynb
.\.venv\Scripts\python.exe scripts/execute_notebook.py 02_entrenamiento_comparacion.ipynb
.\.venv\Scripts\python.exe scripts/run_simulation.py --port 8771
```

El notebook 01 genera las particiones y el 02 guarda el modelo. Esos archivos se generan localmente y están excluidos de Git. El notebook 03 contiene la evaluación final; se ejecuta después del 02 cuando se desea reproducir también esa evaluación. La página utiliza el modelo guardado y no lo entrena mientras funciona.

## 2. Conocer las tres secciones

| Sección | Qué permite hacer |
| --- | --- |
| **Monitor** | Reproducir los registros, consultar mediciones y predicciones, revisar gráficos y alertas y exportar resultados. |
| **El proyecto** | Leer el objetivo, la metodología, las métricas y las limitaciones; acceder al informe y la documentación. |
| **Código** | Consultar archivos y notebooks en un visor de lectura, descargarlos y revisar las instrucciones de ejecución. |

Las secciones se seleccionan en el menú lateral o superior, según el tamaño de pantalla. Cambiar de sección **no pausa** una reproducción en marcha.

## 3. Iniciar y controlar la reproducción

| Control | Comportamiento |
| --- | --- |
| **Iniciar simulación** | Comienza a procesar la reserva, registro por registro. |
| **Pausar** | Detiene el avance y conserva los registros procesados. |
| **Continuar** | Reanuda desde la posición donde se pausó. |
| **Siguiente** | Procesa una sola observación cuando la sesión está lista o pausada. |
| **Reiniciar** | Vuelve al inicio y borra los resultados de la sesión en memoria. Exportar antes si se desea conservarlos. |
| **Intervalo** | Elige la pausa entre observaciones. Se modifica antes de iniciar o mientras la reproducción está pausada. |

El contador indica cuántos registros se han procesado de los **2 000** reservados para prueba. Al terminar, es necesario reiniciar para comenzar otra reproducción.

## 4. Leer las mediciones y la clasificación

La ilustración de la máquina es una ayuda visual: **no está conectada a equipos físicos**. Las tarjetas muestran temperatura del aire y del proceso en kelvin (K), velocidad de rotación en rpm, torque en Nm y desgaste en minutos. El identificador **UDI** y el tipo de producto permiten reconocer la observación.

- **Con falla:** el modelo clasificó el registro como una condición de falla y activa una alerta.
- **Sin falla detectada:** el modelo no identificó una condición de falla. No garantiza que la observación esté realmente libre de ella.
- **Etiqueta real:** es la referencia del dataset. Se consulta después de predecir y no interviene como entrada del modelo.

La comparación posterior distingue **falla detectada**, **falsa alarma**, **falla omitida** y **acierto sin falla**. Por ejemplo, una falsa alarma aparece cuando el modelo predice falla pero la etiqueta indica sin falla. Una falla omitida ocurre cuando predice sin falla y la etiqueta indica falla.

## 5. Consultar los gráficos y las alertas

Los cinco gráficos pequeños acompañan las mediciones. En el gráfico principal se puede seleccionar **Rotación, Torque, Aire, Proceso o Desgaste**.

Se muestran hasta los **últimos 60 registros procesados**, en el orden de reproducción. Los puntos de alerta señalan una predicción de falla. La escala se ajusta a la variable elegida; no representa un umbral de seguridad. La secuencia **no es una serie temporal de una misma máquina real**.

El panel de alertas recientes muestra hasta cinco alertas de esa ventana de 60 registros. El contador de alertas de la sesión incluye todas las predicciones positivas procesadas, incluso las que resultan falsas alarmas.

## 6. Exportar resultados

Presionar **Exportar CSV** para descargar todos los registros procesados de la sesión, aunque la tabla muestre solo los ocho más recientes. El archivo incluye UDI, mediciones, tipo, predicción, etiqueta real, comparación y tiempos.

El archivo se descarga en la ubicación configurada por el navegador. Reiniciar o cerrar el servidor elimina la sesión en memoria; el CSV descargado se conserva.

Los tiempos de la interfaz corresponden a la llamada al pipeline: transformaciones y clasificación. Excluyen la carga, el pintado de pantalla y las pausas de reproducción; no garantizan tiempo real industrial.

## 7. Cambiar entre claro y oscuro

Usar el interruptor de la esquina superior derecha. La elección se conserva al recargar si el navegador permite almacenamiento local. Sin elección manual se utiliza la preferencia de color del sistema. El interruptor también se puede activar con teclado, usando Tab para enfocarlo y Espacio para cambiarlo.

Cambiar de tema no reinicia la sesión ni modifica los resultados.

## 8. Validar una copia de la reserva

Abrir **Datos de prueba y comprobaciones** en la parte inferior del monitor. Elegir una copia de `data/processed/test.csv` y pulsar **Validar y cargar CSV**.

Solo se admite la reserva completa, con sus columnas, valores y orden originales; no se carga directamente `ai4i2020.csv` ni otros datasets. Si la carga es correcta, la sesión se reinicia. Si el archivo es incorrecto, se muestra un mensaje y se conserva el avance. Pausar antes de cargarlo.

## 9. Resolver problemas habituales

| Situación | Qué revisar |
| --- | --- |
| La página no abre o pierde la conexión | Comprobar que la terminal del servidor siga abierta y utilizar la dirección que imprime. |
| El puerto 8771 está ocupado | Iniciar con `--port 8772` y abrir `http://127.0.0.1:8772`. |
| Faltan el modelo o los datos preparados | Ejecutar primero los notebooks 01 y 02 con las dependencias indicadas en `requirements.txt`. |
| El CSV es rechazado | Utilizar la copia original de `data/processed/test.csv`, sin modificarla. |
| Un control aparece desactivado | Revisar si la reproducción está en marcha o completada; pausar o reiniciar según corresponda. |
| Otra pestaña cambia el contador | Las pestañas que usan el mismo servidor comparten la sesión. |

## 10. Alcance de la herramienta

Los datos de AI4I 2020 son sintéticos. El proyecto demuestra clasificación y reproducción de observaciones; no estima vida útil restante ni anticipa horas hasta una avería. Las limitaciones de etiquetado y los errores del modelo se conservan documentados. Repetir la reproducción no crea una nueva evaluación independiente.
