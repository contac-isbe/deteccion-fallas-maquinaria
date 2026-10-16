# Detección de fallas en maquinaria

Proyecto del curso Inteligencia Artificial: Principios y Técnicas, UPAO.

**Título:** Desarrollo de un sistema de detección de fallas en maquinaria mediante aprendizaje automático en un entorno simulado.

## Alcance

Clasificar observaciones de funcionamiento como sin falla o con falla utilizando AI4I 2020. Se compararán regresión logística, árbol de decisión y Random Forest. La demostración reproducirá observaciones reservadas para prueba y mostrará predicciones y alertas.

La tarea no incluye estimar la vida útil restante ni controlar maquinaria física. Los datos son sintéticos y la evaluación se limitará a las condiciones que representan.

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
```

El notebook necesita las carpetas `src/` y `data/` del repositorio. Para usar Colab hay que cargar una copia del proyecto completo e instalar `requirements.txt`; subir únicamente el notebook no basta. No se deben guardar tokens de GitHub en las celdas.

## Estado

El primer notebook audita los datos y prepara una reserva de prueba del 20 %, con validación cruzada estratificada de cinco pliegues dentro del 80 % de desarrollo. Comprueba el preprocesamiento para regresión logística y para árboles sin entrenar clasificadores.

La auditoría documenta discrepancias entre la etiqueta principal y los indicadores de tipos de falla. Se conserva `Machine failure` sin alterar el CSV original. Este problema de etiquetado limita la interpretación de resultados futuros.

El segundo notebook compara 34 configuraciones de regresión logística, árbol de decisión y Random Forest, usando los cinco pliegues fijados en desarrollo. El criterio principal es F1 medio, con sensibilidad y tasa de falsas alarmas para desempates. Se incluye una referencia que siempre predice sin falla.

El pipeline seleccionado se reajusta con desarrollo y se guarda en `models/modelo_seleccionado.joblib`. Los resúmenes de selección y los resultados de todas las configuraciones quedan en `reports/`. Las métricas de selección por validación cruzada no sustituyen la evaluación independiente final.

La reserva de prueba no se carga en el notebook 02. Su evaluación y la simulación corresponden a las etapas siguientes.

## Organización

- `notebooks/`: análisis explicado y resultados de ejecución.
- `src/preparation.py`: auditoría, particiones y transformaciones reutilizables.
- `src/training.py`: búsquedas, comparación y selección usando únicamente desarrollo.
- `scripts/execute_notebook.py`: ejecución completa desde un kernel limpio.
- `reports/`: resúmenes verificables de auditoría y particiones.
- `data/processed/`: CSV preparados, regenerables y excluidos de Git.
- `outputs/`: gráficos y archivos temporales, excluidos de Git.

En el notebook 01 las transformaciones se comprueban con el entrenamiento de un pliegue de demostración. El notebook 02 crea transformadores nuevos dentro de cada pipeline de clasificación. No se utilizan los datos de prueba para elegir el modelo ni sus parámetros.

En la comparación ejecutada, el árbol de decisión obtuvo el mayor F1 medio de validación (0,7229), seguido de Random Forest (0,6564) y regresión logística (0,3304). El árbol seleccionado usa un mínimo de cinco observaciones por hoja, sin profundidad máxima prefijada y con pesos uniformes. Su sensibilidad media de validación fue 67,16 %; aún omite una parte de las fallas. Estos resultados corresponden a selección por validación cruzada, con evaluación final pendiente. Los valores completos y su variación están en `reports/model_comparison.csv`.

## Datos

El archivo original se encuentra en `data/raw/ai4i2020.csv`. Su procedencia y licencia están documentadas en [data/README.md](data/README.md).

El informe se conserva en la carpeta superior `Informe - Proyecto de IA`, fuera de este repositorio.
