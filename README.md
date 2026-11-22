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

## Segunda opinión: autoencoder (aprendizaje no supervisado)

Además del árbol (supervisado), el sistema incluye un **autoencoder** 11 → 8 → 5 → 8 → 11 (encoder, espacio latente de 5 números y decoder) entrenado **solo con observaciones sin falla** de desarrollo. Una observación cuyo error de reconstrucción supera el umbral (percentil 99 del error en datos normales no vistos, 0,181) se marca como *atípica*. La interfaz muestra la red, la entrada frente a su reconstrucción y el error frente al umbral.

En las 2 000 observaciones de prueba, solo, detecta 8 de 68 fallas con 10 falsas alarmas (AUC 0,80). Sumarlo al árbol (v2) no rescata ninguna de las 16 fallas omitidas y agrega 10 falsas alarmas, así que **no mejora el resultado y no reemplaza al árbol**: es una segunda opinión explicativa. La arquitectura y el umbral se eligieron solo con desarrollo y la prueba se evaluó una vez ([evaluación](reports/autoencoder_evaluation.json), [selección](reports/autoencoder_selection.json)). Para repetirlo: `python scripts/train_autoencoder.py`.

## Modelo v2 y planta simulada

**Modelo v2 (variables físicas).** Se añaden potencia (par × velocidad angular), diferencia de temperatura y desgaste × par antes del árbol (`src/features.py`, `scripts/train_physics_model.py`). Hiperparámetros elegidos solo con validación cruzada del desarrollo (`min_samples_leaf=10`, `max_depth=6`). En prueba: 52 de 68 fallas detectadas, 0 falsas alarmas, F1 0,867 (el árbol original: 0,763), con 25 nodos. Es una **segunda evaluación** con el conjunto de prueba, declarada como tal ([evaluación](reports/modelo_fisico_evaluation.json)). Los cortes del árbol (≈ 9 004 W, 3 496 W, 8,65 K, 1 380 rpm, desgaste × par ≈ 10 998) coinciden con las reglas reales de AI4I 2020, que el modelo nunca recibió.

**Pronóstico de fallas (el modelo central de la planta).** `src/forecast.py` y `scripts/train_forecast.py`: un modelo de gradient boosting mira las últimas 8 lecturas de cada máquina (valores, medias y pendientes de potencia, diferencia de temperatura, desgaste, desgaste × torque, velocidad y torque) y estima la probabilidad de que falle en los **próximos 12 pasos**. Se entrena con series generadas por la planta simulada (semillas 100-219), hiperparámetros y umbral elegidos con otras semillas (300-339) y se evalúa una sola vez con semillas 500-539 ([evaluación](reports/pronostico_evaluation.json)). Resultado en esas 40 simulaciones (1 626 fallas): anticipa el **87 %** de las fallas, con una mediana de **12 pasos** de adelanto y 0,9 falsas alarmas por cada 1 000 pasos. Por causa: calor 178/178, potencia 532/532, sobretensión 5/5 y desgaste de herramienta 701/911 (la falla de herramienta es aleatoria entre 200 y 240 min: solo se puede avisar que está en la zona de riesgo). Ablación: el mismo modelo sin tendencias, solo con el valor actual, anticipa el 91 % pero con 6,9 falsas alarmas por cada 1 000 pasos (7,5 veces más); mirar la evolución es lo que reduce las falsas alarmas. La explicación («qué empuja el riesgo») se calcula reemplazando cada grupo de variables por valores normales y midiendo cuánto baja el riesgo. **Límite:** los datos de entrenamiento y de prueba vienen del mismo simulador (dinámica con deriva gradual); con máquinas reales los resultados serían distintos.

**Taller de fresado en vivo (pantalla principal).** `src/plant.py` simula 12 fresadoras CNC con las reglas de falla documentadas de AI4I 2020 como «realidad» (el conjunto es sintético pero imita fresadoras reales; la calidad L/M/H es la del producto que fabrican); la IA solo ve las lecturas. Cada fresadora muestra su riesgo de falla próxima. Al hacer clic se abre su gemelo digital: controles del operador (velocidad, demanda de potencia, refrigeración, cambio de herramienta, parámetros seguros), medidores de las reglas físicas, el pronóstico con sus factores, el historial y el árbol/autoencoder sobre esa fresadora. El marcador cuenta fallas anticipadas, no anticipadas, falsas alarmas y **fallas evitadas** (el operador corrigió después de un aviso). El árbol sigue siendo un detector de la lectura actual (adelanto 0) y el autoencoder una segunda opinión. «Datos de prueba» reproduce los 2 000 registros reales.

**Asistente («¿qué hago con esta falla?»).** `src/assistant.py`. Escribes una pregunta y el asistente: (1) la **entiende con un modelo propio entrenado** (`scripts/train_assistant.py`, `notebooks/04_entrenamiento_asistente.ipynb`): regresión logística sobre n-gramas de caracteres, palabras y señales de palabras clave, con dos cabezas (intención y falla mencionada). Se entrenó con 4 437 preguntas generadas (frases escritas a mano × variaciones), con partición por familias de frases, y se evaluó con 723 preguntas de frases no vistas y 69 preguntas naturales escritas a mano: comprende la intención en 83 % y 80 % de los casos (la versión anterior sin entrenar, 50 % y 49 %) y la falla mencionada en 86 % y 96 % ([evaluación](reports/asistente_evaluation.json)). **Limitaciones declaradas:** no existe un corpus real de operadores, así que los datos son sintéticos y de un solo autor; el entrenamiento se ejecutó dos veces (tras ver la primera evaluación se ampliaron las frases y se añadieron palabras clave), de modo que las cifras no son totalmente independientes de las decisiones de diseño; es un clasificador, no un modelo que genere texto. (2) **Consulta al pronosticador entrenado**: proyecta cada acción posible del operador (bajar potencia, cambiar herramienta, subir rpm…) y mide el riesgo resultante, de modo que las cifras salen del modelo y no de una plantilla. (3) Redacta la respuesta con plantillas y una guía general de mantenimiento; cada acción se puede aplicar con un botón. Funciona sin internet. **Opcional:** si defines la variable de entorno `ANTHROPIC_API_KEY` (y, si quieres, `ANTHROPIC_MODEL`), Claude solo reescribe el texto con los datos ya calculados; si falla o no hay clave, vuelve al asistente propio (el modo se indica en pantalla). Esa llamada a la API se probó únicamente con una red simulada (`scripts/verify_assistant.py`). La guía de mantenimiento es general y la proyección usa la dinámica del simulador; con una máquina real manda el manual del fabricante.


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
