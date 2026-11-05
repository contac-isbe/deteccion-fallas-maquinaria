# Revisión de la aplicación publicada

El 4 de noviembre de 2026 se publicó https://deteccion-fallas-maquinaria.onrender.com en el plan Free de Render, servicio srv-dblt3lmi0phs738bbo50. La primera construcción verificada corresponde al commit a44858e. Se instaló Python 3.12.14, se restauraron los artefactos congelados y se comprobó la huella del modelo. No hubo entrenamiento.

## Pruebas

Las 17 comprobaciones locales WSGI y las 14 comprobaciones HTTP públicas pasaron. Se usaron dos clientes con cookies independientes; avanzar y reiniciar uno no modificó el otro. El recorrido remoto de 22 registros conservó 20 TN, 0 FP, 1 FN y 1 TP, con alerta en UDI 1392. Se verificaron inicio, pausa, reinicio, CSV completo, rechazo de un origen ajeno y descargas.

La descarga del manual se contrastó con los bytes almacenados en Git: Windows puede convertir el Markdown a CRLF al trabajar localmente. El Word se contrastó como archivo binario. Las comprobaciones públicas iniciales se realizaron con el Word del 7.1, antes de añadir la sección de despliegue; se repitieron tras publicar main en el commit 528ab9a, y las 14 comprobaciones volvieron a pasar con el Word del 7.2.

En el navegador se inició y pausó la reproducción en el registro 15; siete avances manuales llegaron al registro 22 con alerta de falla. Se navegó por El proyecto y Código y se abrió y cerró la Guía de uso. Se alternó entre oscuro y claro sin perder los 22 registros. Se revisaron el ancho estrecho del navegador y una vista de escritorio de 1280 píxeles. Esto no equivale a probar un teléfono físico ni todos los navegadores.

## Evidencia

- [Monitor público en claro](evidence_deployment/publico-claro.png).
- [Monitor público en oscuro](evidence_deployment/publico-oscuro.png).
- [Vista estrecha](evidence_deployment/publico-movil.png).
- `deployment_checks.json`: pruebas locales de aislamiento, cookies, expiración y recursos.
- `public_deployment_checks.json`: comprobaciones por HTTPS.

## Límites

Un proceso Gunicorn con cuatro hilos atiende la demostración. Cada navegador tiene una sesión temporal; las pestañas del mismo perfil comparten cookie. Hay un límite de 12 sesiones y expiración tras 15 minutos sin solicitudes. Un reinicio o suspensión elimina el avance. El plan gratuito puede tardar en despertar tras inactividad. Los datos siguen siendo sintéticos y la reproducción no genera otra evaluación independiente.

## Cierre de la publicación

Render publicó main en el commit `528ab9a57a1eaa57803a5a278148a17b68fbc04e`, despliegue `dep-dblvkb08v5cc73d3g7i0`. La construcción confirmó las 2 000 predicciones históricas sin entrenamiento. El servicio respondió por HTTPS y las 14 pruebas públicas finales pasaron, incluida la descarga del Word 7.2 y el manual actualizado. La evidencia posterior al despliegue queda guardada en el repositorio; la publicación automática permanece desactivada.
