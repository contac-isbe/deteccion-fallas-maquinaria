# Despliegue del apartado 7.2

**Aplicación verificada:** [https://deteccion-fallas-maquinaria.onrender.com](https://deteccion-fallas-maquinaria.onrender.com). Primera publicación comprobada el 4 de noviembre de 2026.

La aplicación web utiliza Flask con Gunicorn en Render. La simulación y el modelo son los mismos de los apartados anteriores. El modelo no se entrena al publicar: `scripts/prepare_deployment.py` restaura los tres artefactos congelados de `deployment/artifacts/` y comprueba sus huellas y las versiones del experimento.

## Configuración de Render

- Tipo: Web Service, repositorio público `https://github.com/contac-isbe/deteccion-fallas-maquinaria`.
- Rama de preparación: `feature/despliegue-render`; después de revisar e integrar, utilizar `main`.
- Runtime: Python 3.12.14, definido en `.python-version`.
- Plan: Free.
- Build: `pip install -r requirements-deploy.txt && python scripts/prepare_deployment.py`.
- Inicio: `gunicorn 'src.deployment:create_app()' --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 60`.
- Health check: `/health`.
- Variables: `PYTHON_VERSION=3.12.14`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`.
- Publicación automática desactivada durante la revisión.

`render.yaml` conserva la configuración equivalente. No se necesitan claves privadas en el repositorio. Servicio Render: `srv-dblt3lmi0phs738bbo50`. El dominio respondió por HTTPS y se comprobaron su salud, las alertas y la separación entre clientes. El control de salud verifica que el modelo pudo cargarse.

## Sesiones y límites

Cada navegador recibe una cookie aleatoria HttpOnly y SameSite=Lax, marcada Secure en Render. Los navegadores distintos tienen simulaciones independientes; las pestañas del mismo perfil comparten su cookie. Se admiten hasta 12 sesiones activas, con expiración tras 15 minutos sin solicitudes. Una pestaña abierta consulta el estado periódicamente y mantiene su sesión activa.

Las sesiones están en memoria de un único proceso. No se debe aumentar `--workers` ni activar varias instancias sin implementar almacenamiento compartido. Un reinicio, una nueva publicación o la suspensión del servicio borra el avance. Exportar CSV antes de salir si se desea conservarlo. No hay cuentas de usuario ni historial permanente.

El plan gratuito puede suspender el servicio por inactividad y el primer acceso puede tardar mientras arranca. El almacenamiento temporal no se usa para conservar resultados de usuarios. El servicio es una demostración académica, sin garantía industrial ni validación en equipos físicos.

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe -m pip install Flask==3.1.2
.\.venv\Scripts\python.exe scripts/prepare_deployment.py
.\.venv\Scripts\python.exe scripts/verify_deployment.py
```

Las pruebas locales WSGI verifican aislamiento, cookies, límites, expiración, exportación, origen de las acciones, archivos y conservación del experimento. Se registran en `reports/deployment_checks.json`. Gunicorn se ejecuta en Linux en Render; estas pruebas de Windows no sustituyen la verificación del servicio publicado.

Para revisar la aplicación web localmente, sin usar Gunicorn en Windows:

```powershell
.\.venv\Scripts\python.exe -m flask --app src.deployment:create_app run --host 127.0.0.1 --port 8772
```

Ese comando es solo de desarrollo. El servidor local original en el puerto 8771 continúa disponible con `scripts/run_simulation.py`.

## Fuentes de configuración

- https://render.com/docs/deploy-flask
- https://render.com/docs/python-version
- https://render.com/docs/free
- https://flask.palletsprojects.com/en/stable/deploying/gunicorn/

## Verificación pública

`python scripts/verify_public_deployment.py https://deteccion-fallas-maquinaria.onrender.com` comprueba el servicio por HTTPS con dos clientes independientes. La ejecución inicial superó 14 comprobaciones: modelo, métricas, cookie, separación, alerta UDI 1392, prefijo de 22 predicciones, controles, CSV y descargas. La revisión visual está en `reports/deployment_review.md`. Las pruebas locales y públicas tienen alcances distintos y no constituyen una nueva evaluación del modelo.
