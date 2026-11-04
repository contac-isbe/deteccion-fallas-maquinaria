# Preparación local del apartado 7.1

Esta carpeta es una copia independiente del repositorio en el commit `4406aae`. Aquí se prepara una alternativa para compararla con la versión del grupo. El desarrollo comenzó de forma local y ahora se prepara en la rama feature/monitor-interactivo para revisión. El pull request, la integración en main y el despliegue siguen pendientes.

## Contenidos organizados

| Apartado del profesor | Contenido de la pestaña local |
| --- | --- |
| 7.1.1 Documentación del Proyecto | Objetivo, dataset, metodología de los tres notebooks, resultados de prueba, limitaciones, informe Word y evidencia de comprobaciones. |
| 7.1.2 Código del Sistema | Visor de archivos locales de solo lectura, descarga de código y notebooks e instrucciones para ejecutar la aplicación. |
| 7.1.3 Ejecución y Pruebas del Sistema | Reproducción de la reserva, mediciones, clasificación, alertas, controles, CSV y consulta de los resultados de verificación. |

En el rediseño, los nombres visibles son Monitor (ejecución y pruebas), El proyecto (documentación) y Código. El monitor es la pantalla inicial.

La organización en pestañas es una interpretación práctica de los contenidos solicitados; no supone que GitHub genere automáticamente esas pestañas. La rama conserva la alternativa del 7.1 para revisión. Su integración en main y el despliegue del 7.2 siguen pendientes.

## Ejecutar esta alternativa

En una terminal situada en esta carpeta:

```powershell
.\.venv\Scripts\python.exe scripts/run_simulation.py --port 8771
```

Abrir `http://127.0.0.1:8771`. Mantener la terminal activa y usar `Ctrl+C` para detener el proceso. En Windows también se puede abrir `ABRIR_PORTAL.cmd`.

Esta copia contiene un entorno virtual independiente con los mismos paquetes ya instalados, el modelo y las particiones copiadas del proyecto original. No se reentrenó el modelo. Estos archivos continúan excluidos de Git. Si se prepara otra copia en otro equipo, crear un entorno Python 3.12, instalar `requirements.txt` y seguir el procedimiento de los notebooks 01 y 02 del README.

## Comprobar

```powershell
.\.venv\Scripts\python.exe scripts/verify_simulation.py
.\.venv\Scripts\python.exe scripts/verify_portal.py
```

El primer script comprueba la reproducción y la integración de la simulación; el segundo comprueba los contenidos, la consulta de código y las descargas locales. La revisión en el navegador y las capturas se registran por separado. Los resultados nuevos de esta carpeta no cambian los resultados ni el Word del proyecto original.

## Límites

El modelo, las seis variables y la reserva se conservan. No se reemplaza la evaluación final del notebook 03 ni se atribuye generalización industrial a estos datos sintéticos. El servidor escucha solo en este equipo y las pestañas conectadas al mismo proceso comparten una sesión de simulación. Consultar código o cambiar de pestaña no pausa automáticamente la reproducción.
