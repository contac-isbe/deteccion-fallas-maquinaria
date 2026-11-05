# Publicación del apartado 7.1

El monitor se desarrolló a partir de la revisión `4406aae`, en la rama `feature/monitor-interactivo`. El repositorio reúne el código, la documentación y las comprobaciones del apartado 7.1. La publicación del código en GitHub permite revisarlo y descargarlo; el alojamiento de la aplicación con un enlace externo corresponde al 7.2 y sigue pendiente.

## Contenidos organizados

| Apartado del profesor | Contenido de la pestaña local |
| --- | --- |
| 7.1.1 Documentación del Proyecto | Objetivo, dataset, metodología de los tres notebooks, resultados de prueba, limitaciones, informe Word y evidencia de comprobaciones. |
| 7.1.2 Código del Sistema | Visor de archivos locales de solo lectura, descarga de código y notebooks e instrucciones para ejecutar la aplicación. |
| 7.1.3 Ejecución y Pruebas del Sistema | Reproducción de la reserva, mediciones, clasificación, alertas, controles, CSV y consulta de los resultados de verificación. |

En el rediseño, los nombres visibles son Monitor (ejecución y pruebas), El proyecto (documentación) y Código. El monitor es la pantalla inicial.

La organización en pestañas es una interpretación práctica de los contenidos solicitados; no supone que GitHub genere automáticamente esas pestañas. El flujo de cambios utiliza ramas y pull requests antes de integrar en main.

## Ejecutar la aplicación

En una terminal situada en esta carpeta:

```powershell
.\.venv\Scripts\python.exe scripts/run_simulation.py --port 8771
```

Abrir `http://127.0.0.1:8771`. Mantener la terminal activa y usar `Ctrl+C` para detener el proceso. En Windows también se puede abrir `ABRIR_PORTAL.cmd`.

El modelo y las particiones se generan localmente y están excluidos de Git. En otra computadora, crear un entorno Python 3.12, instalar `requirements.txt` y ejecutar los notebooks 01 y 02 del README. Consultar también el [manual de uso](MANUAL_USUARIO.md).

## Comprobar

```powershell
.\.venv\Scripts\python.exe scripts/verify_simulation.py
.\.venv\Scripts\python.exe scripts/verify_portal.py
```

El primer script comprueba la reproducción y la integración de la simulación; el segundo comprueba los contenidos, la consulta de código y las descargas locales. La revisión en el navegador y las capturas se registran por separado. La evidencia original del 6.2 se conserva en reports/simulation_checks.json; las nuevas comprobaciones del monitor se guardan en reports/monitor_simulation_checks.json.

## Límites

El modelo, las seis variables y la reserva se conservan. No se reemplaza la evaluación final del notebook 03 ni se atribuye generalización industrial a estos datos sintéticos. El servidor escucha solo en este equipo y las pestañas conectadas al mismo proceso comparten una sesión de simulación. Consultar código o cambiar de pestaña no pausa automáticamente la reproducción.
