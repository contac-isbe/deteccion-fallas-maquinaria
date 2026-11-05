# Detección de fallas en maquinaria

**Aplicación publicada:** [https://deteccion-fallas-maquinaria.onrender.com](https://deteccion-fallas-maquinaria.onrender.com). Se utiliza desde el navegador, sin instalar Python. El plan gratuito puede tardar en arrancar tras un periodo sin visitas. Las sesiones se guardan temporalmente; exportar CSV para conservar resultados.

Proyecto del curso Inteligencia Artificial: Principios y Técnicas, UPAO.

**Título:** Desarrollo de un sistema de detección de fallas en maquinaria mediante aprendizaje automático en un entorno simulado.

## Alcance

Clasificar observaciones de funcionamiento como sin falla o con falla utilizando AI4I 2020. Se compararon regresión logística, árbol de decisión y Random Forest. La demostración reproduce observaciones reservadas para prueba y muestra predicciones y alertas.

La tarea no incluye estimar la vida útil restante ni controlar maquinaria física. Los datos son sintéticos y la evaluación se limita a las condiciones que representan.

## Trabajo local en VS Code

Requiere Python 3.12 y las extensiones Python y Jupyter de VS Code.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Abrir `notebooks/01_analisis_preparacion.ipynb`, seleccionar el kernel del entorno `.venv` y ejecutar las celdas en orden. La configuración de la carpeta indica la ruta del intérprete local.

También se puede ejecutar el notebook completo desde la raíz:

```powershell
.\.venv\Scripts\python.exe scripts/execute_notebook.py
.\.venv\Scripts\python.exe scripts/execute_notebook.py 02_entrenamiento_comparacion.ipynb
.\.venv\Scripts\python.exe scripts/execute_notebook.py 03_comprobacion_prueba.ipynb
```

El notebook necesita las carpetas `src/` y `data/` del repositorio. Para usar Colab hay que cargar una copia del proyecto completo e instalar `requirements.txt`; subir únicamente el notebook no basta. No se deben guardar tokens de GitHub en las celdas.

## Estado

El primer notebook audita los datos y prepara una reserva de prueba del 20 %, con validación cruzada estratificada de cinco pliegues dentro del 80 % de desarrollo. Comprueba el preprocesamiento para regresión logística y para árboles sin entrenar clasificadores.

La auditoría documenta discrepancias entre la etiqueta principal y los indicadores de tipos de falla. Se conserva `Machine failure` sin alterar el CSV original. Este problema de etiquetado limita la interpretación de los resultados.

El segundo notebook compara 34 configuraciones de regresión logística, árbol de decisión y Random Forest, usando los cinco pliegues fijados en desarrollo. El criterio principal es F1 medio, con sensibilidad y tasa de falsas alarmas para desempates. Se incluye una referencia que siempre predice sin falla.

El pipeline seleccionado se reajusta con desarrollo y se guarda en `models/modelo_seleccionado.joblib`. Los resúmenes de selección y los resultados de todas las configuraciones quedan en `reports/`. Las métricas de selección por validación cruzada no sustituyen la evaluación independiente final.

La reserva de prueba no se carga en el notebook 02. El notebook 03 evalúa el pipeline ya fijado, sin entrenarlo ni reajustarlo. En las 2 000 observaciones de prueba detectó 50 de las 68 fallas, omitió 18 y produjo 13 falsas alarmas. Obtuvo sensibilidad del 73,53 %, precisión del 79,37 %, F1 de 0,7634 y tasa de falsas alarmas del 0,67 %. Los conteos y tiempos locales completos están en `reports/test_evaluation.json`; las predicciones individuales, en `reports/test_predictions.csv`.

`model_selection.json` conserva la selección histórica anterior a la prueba. El reporte separado `test_evaluation.json` registra que la reserva ya fue evaluada. No se deben usar estos resultados para volver a elegir parámetros y seguir llamando independiente a la misma reserva.

La simulación local está implementada y cuenta con comprobaciones funcionales, pruebas HTTP y revisión visual del navegador. Reproduce la reserva ya evaluada con el modelo guardado, sin reentrenarlo. La evidencia está en `reports/simulation_checks.json` y `reports/simulation_review.md`. El informe Word se actualiza por separado, después de comprobar los resultados.

## Simulación local

Desde la raíz del repositorio, con el entorno virtual preparado:

```powershell
.\.venv\Scripts\python.exe scripts/run_simulation.py
```

Abrir [la interfaz local](http://127.0.0.1:8771) en un navegador. El servidor escucha únicamente en este equipo. Detenerlo con `Ctrl+C` en la terminal. Si el puerto está ocupado, utilizar `--port 8772` y abrir el puerto indicado.

La interfaz muestra las cinco mediciones con sus unidades, el tipo de producto, UDI y la predicción. Permite iniciar, pausar, continuar, avanzar un registro y reiniciar. Una alerta se activa cuando el modelo predice falla; la etiqueta real se muestra después para comparar y nunca entra al modelo. Una predicción sin falla no garantiza ausencia de una condición de falla.

`Exportar resultados CSV` descarga todos los registros procesados de la sesión, aunque la tabla muestre solo los ocho más recientes. Incluye identificadores, entradas, etiqueta real, predicción, alerta, acierto/error y tiempos. Reiniciar borra la sesión en memoria: exportar antes si se desea conservarla. Las pestañas conectadas al mismo servidor comparten una sesión; no es una aplicación multiusuario.

La reserva verificada ya se carga al iniciar. El control de carga permite comprobar una copia de `data/processed/test.csv`: solo acepta la reserva completa con las columnas, valores y orden originales. Un archivo incorrecto muestra un mensaje y conserva el avance. No se admiten otros datasets ni nuevas mediciones en esta demostración.

Si faltan `data/processed/` o `models/` en una copia nueva, ejecutar primero los notebooks 01 y 02, en ese orden. Esos archivos se generan localmente y están excluidos de Git. La aplicación comprueba la integridad del modelo y la reserva antes de funcionar; no entrena automáticamente.

## Comprobación de la simulación

```powershell
.\.venv\Scripts\python.exe scripts/verify_simulation.py
```

El script reproduce las 2 000 observaciones mediante avance manual automatizado, compara cada predicción con el notebook 03, verifica alertas y exportación, y prueba inicio, pausa, continuación y errores a través del servidor HTTP. Escribe el resumen en `reports/monitor_simulation_checks.json` y el CSV de comprobación en `outputs/simulation_checked_predictions.csv` (excluido de Git). No modifica el modelo ni la evaluación histórica. Las capturas y las comprobaciones manuales del navegador se documentan por separado en `reports/simulation_review.md`.

Los tiempos diferencian la llamada al pipeline, el procesamiento de una observación y el recorrido HTTP local. Ninguno incluye el pintado de la pantalla ni las pausas entre registros. No se fijó un umbral de latencia ni se afirma cumplimiento de tiempo real industrial. Reproducir la prueba ya consultada no constituye una nueva evaluación independiente del modelo.

## Organización

- `notebooks/`: análisis explicado y resultados de ejecución.
- `src/preparation.py`: auditoría, particiones y transformaciones reutilizables.
- `src/training.py`: búsquedas, comparación y selección usando únicamente desarrollo.
- `src/evaluation.py`: verificación del experimento congelado, evaluación final y tiempos locales de predicción.
- `src/simulation.py`: validación, reproducción y exportación de la sesión, sin entrenamiento.
- `src/simulation_server.py`: servidor HTTP local de la interfaz.
- `web/`: interfaz en español con HTML, CSS y JavaScript, sin dependencias web adicionales.
- `scripts/execute_notebook.py`: ejecución completa desde un kernel limpio.
- `scripts/run_simulation.py`: inicio de la simulación local.
- `scripts/verify_simulation.py`: comprobaciones funcionales y de integración reproducibles.
- `reports/`: auditoría, particiones, selección, evaluación y evidencia de la simulación.
- `data/processed/`: CSV preparados, regenerables y excluidos de Git.
- `outputs/`: gráficos y archivos temporales, excluidos de Git.

En el notebook 01 las transformaciones se comprueban con el entrenamiento de un pliegue de demostración. El notebook 02 crea transformadores nuevos dentro de cada pipeline de clasificación. No se utilizan los datos de prueba para elegir el modelo ni sus parámetros.

En la comparación ejecutada, el árbol de decisión obtuvo el mayor F1 medio de validación (0,7229), seguido de Random Forest (0,6564) y regresión logística (0,3304). El árbol seleccionado usa un mínimo de cinco observaciones por hoja, sin profundidad máxima prefijada y con pesos uniformes. Su sensibilidad media de validación fue 67,16 %; aún omite una parte de las fallas. Estos resultados corresponden a la selección por validación cruzada. La evaluación final se realizó en el notebook 03 sobre las 2 000 observaciones de prueba y se resume en la sección Estado. Los valores completos y su variación están en `reports/model_comparison.csv`.

## Datos

El archivo original se encuentra en `data/raw/ai4i2020.csv`. Su procedencia y licencia están documentadas en [data/README.md](data/README.md).

## Informe del proyecto

La copia del informe desarrollada hasta el apartado 7.2 está disponible en [Informe - Proyecto de IA.docx](docs/Informe%20-%20Proyecto%20de%20IA.docx). Descargar el archivo para revisarlo en Word.

El original editable se conserva en la carpeta superior `Informe - Proyecto de IA`. Cuando se actualice, también debe actualizarse la copia de `docs/` para mantener ambas versiones iguales.

## Interfaz de monitoreo

Space Grotesk e Inter se sirven desde `web/fonts/`, con sus licencias incluidas. Las cifras usan una fuente monoespaciada del sistema. No se necesita conexión a Google Fonts durante el uso. La revisión del monitor y sus capturas están en [reports/monitor_review.md](reports/monitor_review.md).

## Modo claro y oscuro

El interruptor de la esquina superior derecha permite alternar entre ambos temas y conserva la elección al recargar, si el navegador permite almacenamiento local. Sin una elección manual se utiliza la preferencia del sistema. El control también funciona con teclado y no modifica la sesión ni las predicciones. Las comprobaciones visuales están en [reports/theme_review.md](reports/theme_review.md).

## Manual de uso

[Consultar el manual completo](docs/MANUAL_USUARIO.md). La interfaz incluye el botón **Guía de uso**, disponible en Monitor y El proyecto, con instrucciones rápidas y descarga del manual.

La evidencia original del apartado 6.2 se conserva en `reports/simulation_checks.json`. Las nuevas ejecuciones del monitor se registran en `reports/monitor_simulation_checks.json`, sin reemplazar ese registro histórico.

## Publicación del apartado 7.1

El repositorio reúne documentación, código, notebooks y evidencia de ejecución. La interfaz organiza estos contenidos en El proyecto, Código y Monitor. El manual completo está en `docs/MANUAL_USUARIO.md`; la página también ofrece una guía rápida. El código se integra mediante una rama de trabajo y un pull request. La aplicación pública del apartado 7.2 está disponible en el enlace indicado al inicio.

## Despliegue 7.2

La aplicación Flask se publica en Render con sesiones separadas por navegador, sin reentrenamiento. La configuración, los límites y los pasos están en [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md). Las comprobaciones locales se guardan en `reports/deployment_checks.json`; las comprobaciones HTTP del enlace público están en `reports/public_deployment_checks.json`.
