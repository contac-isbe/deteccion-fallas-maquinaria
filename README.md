# Detección de fallas en maquinaria

Proyecto del curso **Inteligencia Artificial: Principios y Técnicas — UPAO**.

**Título:** Desarrollo de un sistema de detección de fallas en maquinaria mediante aprendizaje automático en un entorno simulado.

**Estado:** desarrollo completado hasta el apartado **7.2**, con informe, evaluación, interfaz y despliegue publicados.

## Accesos principales

- [Abrir la aplicación](https://deteccion-fallas-maquinaria.onrender.com).
- [Informe del proyecto hasta el 7.2](docs/Informe%20-%20Proyecto%20de%20IA.docx).
- [Manual de uso](docs/MANUAL_USUARIO.md).
- [Configuración y límites del despliegue](docs/DESPLIEGUE.md).

La aplicación se utiliza desde el navegador, sin instalar Python. El plan gratuito puede tardar en arrancar después de un periodo sin visitas. El avance es temporal: exportar CSV para conservar resultados.

## Qué hace el sistema

Clasifica observaciones de maquinaria como **sin falla o con falla** utilizando aprendizaje automático. La interfaz muestra mediciones, predicciones, alertas, gráficos y la comparación posterior con la etiqueta del dataset. Incluye controles de reproducción, exportación CSV, guía de uso y modo claro y oscuro.

Se utiliza únicamente **AI4I 2020**, con 10 000 observaciones sintéticas: 8 000 para desarrollo y 2 000 para prueba. El dataset original, su procedencia y licencia están en [data/README.md](data/README.md).

El sistema demuestra clasificación en un entorno simulado. No está conectado a maquinaria física, no estima vida útil restante ni anticipa horas hasta una avería. Los gráficos reproducen observaciones independientes, no una serie temporal de una misma máquina.

## Contenidos solicitados por el curso

| Apartado | Contenido y evidencia |
| --- | --- |
| I–II. Planteamiento y requerimientos | [Informe](docs/Informe%20-%20Proyecto%20de%20IA.docx): título, antecedentes, problema, objetivos y requisitos. |
| III. Dataset y preprocesamiento | [Notebook 01](notebooks/01_analisis_preparacion.ipynb): auditoría, variables, particiones y transformaciones. |
| IV. Aprendizaje | [Notebook 02](notebooks/02_entrenamiento_comparacion.ipynb): comparación y selección del modelo. |
| V y 6.1. Comprobación y evaluación del modelo | [Notebook 03](notebooks/03_comprobacion_prueba.ipynb), [métricas](reports/test_evaluation.json) y [predicciones](reports/test_predictions.csv). |
| 6.2. Evaluación del sistema | [Comprobaciones](reports/simulation_checks.json) y [revisión de la simulación](reports/simulation_review.md). |
| 7.1.1. Documentación del proyecto | Informe, [manual](docs/MANUAL_USUARIO.md) y sección **El proyecto** de la aplicación. |
| 7.1.2. Código del sistema | [Código Python](src/), [interfaz](web/), [notebooks](notebooks/) y sección **Código** de la aplicación. |
| 7.1.3. Ejecución y pruebas | Sección **Monitor**, instrucciones locales y [evidencia del portal](reports/portal_checks.json). |
| 7.2. Despliegue | [Aplicación pública](https://deteccion-fallas-maquinaria.onrender.com), [configuración](docs/DESPLIEGUE.md) y [verificación pública](reports/public_deployment_checks.json). |

## Modelo y resultados

Se compararon 34 configuraciones de regresión logística, árbol de decisión y Random Forest mediante validación cruzada de cinco pliegues, únicamente con desarrollo. Se seleccionó un **árbol de decisión**, con un mínimo de cinco observaciones por hoja, sin profundidad máxima prefijada y pesos uniformes.

| Resultado en 2 000 observaciones de prueba | Valor |
| --- | --- |
| Precisión | 79,37 % |
| Sensibilidad | 73,53 % |
| F1 | 0,7634 |
| Exactitud | 98,45 % |
| Fallas detectadas / fallas reales | 50 / 68 |
| Fallas omitidas | 18 |
| Falsas alarmas | 13 |

Las alertas conservan los errores del modelo. Se documentaron 27 discrepancias de etiquetado sin alterar el CSV original. La reserva ya fue evaluada y no se usa para reajustar parámetros; reproducirla en la interfaz no constituye otra evaluación independiente.

## Probar la interfaz localmente

Requiere **Python 3.12.14**. Clonar o descargar el repositorio completo, abrir una terminal en su carpeta y ejecutar en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\.venv\Scripts\python.exe scripts/prepare_deployment.py
.\.venv\Scripts\python.exe -m flask --app src.deployment:create_app run --host 127.0.0.1 --port 8772
```

Abrir **http://127.0.0.1:8772** y mantener la terminal activa; detener con `Ctrl+C`. Esta opción permite probar la interfaz con sesiones aisladas y restaura los artefactos verificados, **sin volver a entrenar**. Gunicorn se utiliza en Render; el comando de Flask anterior es solo para desarrollo local.

El servidor local original también está disponible con `scripts/run_simulation.py` o `ABRIR_PORTAL.cmd`, en el puerto 8771. Ese modo comparte una sesión entre todos sus visitantes.

## Reproducir los notebooks

Para reproducir el análisis y el entrenamiento, instalar `requirements.txt` en el entorno virtual y ejecutar los tres notebooks en orden:

1. `01_analisis_preparacion.ipynb`: audita y prepara los datos.
2. `02_entrenamiento_comparacion.ipynb`: compara modelos y guarda el seleccionado.
3. `03_comprobacion_prueba.ipynb`: evalúa el modelo fijado, sin reajustarlo.

En VS Code se utilizan las extensiones Python y Jupyter, seleccionando el entorno `.venv`. También pueden ejecutarse con `scripts/execute_notebook.py`. Los notebooks necesitan las carpetas del proyecto; subir únicamente un notebook a Colab no basta.

Las carpetas de trabajo `models/` y `data/processed/` están excluidas de Git. Las copias congeladas necesarias para publicar y probar la aplicación se conservan en `deployment/artifacts/`, con un manifiesto de integridad.

## Pruebas y evidencia

| Comprobación | Evidencia |
| --- | --- |
| Simulación: 21 comprobaciones | [monitor_simulation_checks.json](reports/monitor_simulation_checks.json) |
| Portal: ocho comprobaciones | [portal_checks.json](reports/portal_checks.json) |
| Aplicación web local: 17 comprobaciones | [deployment_checks.json](reports/deployment_checks.json) |
| Servicio público: 14 comprobaciones | [public_deployment_checks.json](reports/public_deployment_checks.json) |
| Revisión visual y alcance de las pruebas públicas | [deployment_review.md](reports/deployment_review.md) |

Los scripts de comprobación están en `scripts/`. La evidencia original del 6.2 se conserva separada de las ejecuciones posteriores. Las capturas y los registros históricos documentan cada etapa; el estado actual del proyecto es el indicado en este README.

## Cambios del grupo

Actualizar `main`, crear una rama para el cambio, probarlo localmente y abrir un **pull request**. Los cambios se revisan antes de hacer merge. La publicación automática en Render está desactivada: integrar un PR no actualiza por sí solo la aplicación pública.

Las instrucciones de uso, las sesiones temporales y los límites del servicio se detallan en el manual y en la documentación de despliegue.
