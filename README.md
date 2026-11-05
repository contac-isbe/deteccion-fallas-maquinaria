# Detección de fallas en maquinaria

**Universidad Privada Antenor Orrego — UPAO**

Facultad de Ingeniería · Programa de Estudio de Ingeniería de Sistemas e Inteligencia Artificial

**Curso:** Inteligencia Artificial: Principios y Técnicas

**Docente:** Sagastegui Chigne, Hernán

**Integrantes:**

- Bejarano Benites, Isaí Samuel
- Carranza Ortiz, Alejandro Gabriel
- Cieza Llanos, Luis Eduardo
- Chunqui Angulo, Daniela Cristina
- Orozco Lopez, Alfredo Jhosep

**Título del proyecto:** Desarrollo de un sistema de detección de fallas en maquinaria mediante aprendizaje automático en un entorno simulado

## Accesos principales

- [Abrir la aplicación](https://deteccion-fallas-maquinaria.onrender.com).
- [Informe del proyecto](docs/Informe%20-%20Proyecto%20de%20IA.docx).
- [Manual de uso](docs/MANUAL_USUARIO.md).
- [Configuración y límites del despliegue](docs/DESPLIEGUE.md).

La aplicación se utiliza desde el navegador, sin instalar Python. El plan gratuito puede tardar en arrancar después de un periodo sin visitas. El avance es temporal: exportar CSV para conservar resultados.

## Qué hace el sistema

Clasifica observaciones de maquinaria como **sin falla o con falla** utilizando aprendizaje automático. La interfaz muestra mediciones, predicciones, alertas, gráficos y la comparación posterior con la etiqueta del dataset. Incluye controles de reproducción, exportación CSV, guía de uso y modo claro y oscuro.

Se utiliza únicamente **AI4I 2020**, con 10 000 observaciones sintéticas: 8 000 para desarrollo y 2 000 para prueba. El dataset original, su procedencia y licencia están en [data/README.md](data/README.md).

El sistema demuestra clasificación en un entorno simulado. No está conectado a maquinaria física, no estima vida útil restante ni anticipa horas hasta una avería. Los gráficos reproducen observaciones independientes, no una serie temporal de una misma máquina.

## Estructura del proyecto

| Sección del informe | Contenido y recursos |
| --- | --- |
| I. Introducción | [Informe](docs/Informe%20-%20Proyecto%20de%20IA.docx): título, antecedentes, problema y objetivos. |
| II. Requerimientos | [Informe](docs/Informe%20-%20Proyecto%20de%20IA.docx): dominio y requisitos funcionales y no funcionales. |
| III. Dataset y preprocesamiento | [Notebook 01](notebooks/01_analisis_preparacion.ipynb): auditoría, variables, particiones y transformaciones. |
| IV. Aprendizaje | [Notebook 02](notebooks/02_entrenamiento_comparacion.ipynb): comparación, entrenamiento y selección del modelo. |
| V. Comprobación | [Notebook 03](notebooks/03_comprobacion_prueba.ipynb): aplicación del modelo seleccionado al conjunto de prueba y [predicciones obtenidas](reports/test_predictions.csv). |
| VI. Evaluación | [Métricas del modelo](reports/test_evaluation.json), [comprobaciones del sistema](reports/simulation_checks.json) y [revisión funcional](reports/simulation_review.md). |
| VII. Despliegue | [Documentación](docs/), [código](src/), [interfaz](web/), [evidencia de ejecución](reports/portal_checks.json) y [aplicación publicada](https://deteccion-fallas-maquinaria.onrender.com). |

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

## Ejecución local

Requiere **Python 3.12.14**. Clonar o descargar el repositorio completo, abrir una terminal en su carpeta y ejecutar en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\.venv\Scripts\python.exe scripts/prepare_deployment.py
.\.venv\Scripts\python.exe -m flask --app src.deployment:create_app run --host 127.0.0.1 --port 8772
```

Abrir **http://127.0.0.1:8772** y mantener la terminal activa; detener con `Ctrl+C`. Esta opción permite probar la interfaz con sesiones aisladas y restaura los artefactos verificados, **sin volver a entrenar**. Gunicorn se utiliza en Render; el comando de Flask anterior es solo para desarrollo local.

## Reproducción del experimento

Para reproducir el análisis y el entrenamiento, instalar `requirements.txt` en el entorno virtual y ejecutar los tres notebooks en orden:

1. `01_analisis_preparacion.ipynb`: audita y prepara los datos.
2. `02_entrenamiento_comparacion.ipynb`: compara modelos y guarda el seleccionado.
3. `03_comprobacion_prueba.ipynb`: evalúa el modelo fijado, sin reajustarlo.

En VS Code se utilizan las extensiones Python y Jupyter, seleccionando el entorno `.venv`. También pueden ejecutarse con `scripts/execute_notebook.py`. La reproducción requiere el repositorio completo y sus dependencias.

Las carpetas de trabajo `models/` y `data/processed/` están excluidas de Git. Las copias congeladas necesarias para publicar y probar la aplicación se conservan en `deployment/artifacts/`, con un manifiesto de integridad.

## Pruebas y evidencia

| Comprobación | Evidencia |
| --- | --- |
| Simulación: 21 comprobaciones | [monitor_simulation_checks.json](reports/monitor_simulation_checks.json) |
| Portal: ocho comprobaciones | [portal_checks.json](reports/portal_checks.json) |
| Aplicación web local: 17 comprobaciones | [deployment_checks.json](reports/deployment_checks.json) |
| Servicio público: 14 comprobaciones | [public_deployment_checks.json](reports/public_deployment_checks.json) |
| Revisión visual y alcance de las pruebas públicas | [deployment_review.md](reports/deployment_review.md) |

Los scripts de comprobación están en `scripts/`. Los resultados, capturas y registros de verificación se conservan en `reports/`, diferenciando la evaluación del modelo, las pruebas locales y las pruebas del servicio publicado.
