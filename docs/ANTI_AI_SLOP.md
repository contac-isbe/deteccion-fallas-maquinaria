# Reglas anti‑AI slop y anti‑vibe‑code slop

**Guía de diseño, UX, contenido y desarrollo asistido por IA**  
**Versión:** 1.0 · **Fecha:** 21 de noviembre de 2026  
**Uso:** instrucciones persistentes para agentes de IA, revisiones de interfaz y criterios de aceptación del equipo.

---

## 1. Objetivo y definición

El objetivo no es que la interfaz parezca «hecha a mano» a toda costa ni prohibir tendencias visuales. El objetivo es que el producto se vea y funcione como una solución diseñada para sus usuarios, su dominio y sus tareas; no como una plantilla genérica ensamblada por un modelo.

En esta guía se distinguen dos problemas:

- **AI slop visual:** patrones visuales y de contenido repetidos sin una razón funcional. La interfaz puede parecer moderna a primera vista, pero carece de identidad, jerarquía, intención o relación con el producto.
- **Vibe-code slop:** código generado y aceptado por apariencia o por una demostración superficial, sin comprenderlo, probarlo ni comprobar que respeta la arquitectura existente. Puede producir funcionalidades frágiles, dependencias innecesarias, errores ocultos y deuda técnica.

Un elemento no es slop por existir. Una tarjeta, un degradado, una animación, un emoji o una fuente popular pueden ser correctos. Se convierten en un problema cuando se usan por inercia, se repiten sin aportar información o no responden a una necesidad concreta.

### Principio rector

> **Cada decisión visual, textual y técnica debe tener una razón verificable relacionada con el usuario, el contenido, la tarea o la identidad del producto. Si no puedes explicar por qué existe un elemento, elimínalo o simplifícalo.**

### Jerarquía de prioridades

1. Resolver correctamente las tareas del usuario.
2. Mantener claridad, legibilidad, accesibilidad y consistencia.
3. Respetar la arquitectura, los datos y los flujos existentes.
4. Construir una identidad visual coherente y específica del producto.
5. Añadir decoración o movimiento únicamente cuando mejore la experiencia.

La estética nunca justifica romper una interacción, inventar contenido ni degradar el rendimiento.

---

## 2. Patrones visuales que deben tratarse como sospechosos

No son prohibiciones absolutas. Son señales de alerta: antes de mantener cualquiera de ellos, exige una justificación funcional o de identidad.

| Patrón sospechoso | Por qué suele parecer genérico | Regla de sustitución |
|---|---|---|
| Tarjetas para absolutamente todo | Convierte cada sección en una caja independiente y fragmenta la jerarquía. | Usa secciones sin marco, listas, tablas, divisores o agrupaciones espaciales. Reserva las tarjetas para elementos realmente independientes o repetidos. |
| Tarjetas dentro de otras tarjetas | Añade capas de contenedores sin aportar estructura nueva. | Elimina el contenedor exterior o interior; usa una sola superficie y una jerarquía tipográfica clara. |
| Línea vertical/acento de color pegada al borde izquierdo de cada tarjeta | Se convierte en decoración repetitiva, no en señal semántica. | Úsala solo si comunica un estado, categoría, selección o prioridad real y ese significado es consistente en todo el producto. |
| Degradado morado/azul sobre fondo blanco como identidad automática | Es una combinación muy asociada a plantillas de SaaS y resultados generados. | Define la paleta desde el dominio, la marca, el público y las condiciones de uso. Un degradado solo se conserva si tiene un papel concreto. |
| Orbes, blobs, bokeh y círculos difuminados decorativos | Ocupan espacio sin aclarar contenido ni navegación. | Retíralos. Usa fotografía, ilustración o textura contextual solo cuando aporte significado. |
| Filas de KPI con icono, cifra grande y etiqueta en tarjetas idénticas | Impone un dashboard de plantilla aunque las métricas no sean la tarea principal. | Muestra primero la información que ayuda a decidir. Utiliza tabla, lista, resumen compacto o visualización según el tipo de dato. |
| Todo con esquinas muy redondeadas o forma de píldora | Hace que controles, tarjetas, etiquetas y paneles pierdan diferenciación. | Establece una escala limitada de radios. Reserva la píldora para chips, estados compactos o controles que la necesiten. |
| Sombras y bordes en cada contenedor | Produce una interfaz con demasiadas capas y poca jerarquía. | Usa espacio, alineación y tipografía primero. Aplica borde o elevación solo para separar superficies que necesitan distinguirse. |
| Glassmorphism, blur o transparencias por defecto | Puede reducir contraste y convertir el contenido en decoración. | Aplica translucidez solo si la superposición tiene una función clara y el texto conserva contraste suficiente. |
| Hero gigante con título genérico en una herramienta operativa | Retrasa la tarea real y hace que una aplicación parezca una landing page. | Abre directamente en la vista de trabajo: contenido, filtros, acciones y estado. Usa un hero solo si el producto realmente necesita una portada. |
| Badge para cada etiqueta, número o palabra | Genera ruido y hace que los estados importantes dejen de destacar. | Usa texto normal para metadatos. Reserva badges para estados, categorías o alertas que deban reconocerse rápidamente. |
| Animación de entrada para cada bloque | El movimiento se vuelve repetitivo y retrasa la lectura. | Anima solo transiciones significativas, feedback o una secuencia que ayude a comprender el cambio. |
| Icono decorativo en cada título o párrafo | Compite con el contenido y no crea una semántica consistente. | Usa iconos para acciones, navegación o estados reconocibles, no para rellenar huecos. |

**Regla de densidad:** no conviertas cada grupo de información en un panel. Si una página tiene más contenedores que relaciones de contenido claras, revisa su estructura.

---

## 3. Sistema visual: reglas obligatorias

### 3.1 Identidad y dirección visual

- Antes de diseñar, identifica el tipo de producto: herramienta interna, sistema académico, e-commerce, portafolio, producto editorial, aplicación de consumo, etc.
- Define una dirección visual concreta con 3–5 atributos útiles, por ejemplo: `sobrio`, `técnico`, `denso`, `editorial`, `amigable`, `industrial` o `lúdico`.
- Explica cómo esos atributos se traducen en decisiones: tipografía, paleta, densidad, formas, iconos, imágenes y movimiento.
- No confundas “moderno”, “premium”, “minimalista” o “profesional” con una especificación. Son adjetivos demasiado vagos si no se acompañan de decisiones comprobables.
- No copies una referencia completa. Extrae lo que funciona de ella (jerarquía, proporciones, navegación, ritmo, tratamiento tipográfico) y adáptalo al producto.
- Evita mezclar estilos incompatibles sin intención: por ejemplo, iconografía outline con emojis 3D, tipografía editorial con controles futuristas y sombras de neumorfismo en el mismo sistema.

### 3.2 Color

- Define tokens semánticos: `background`, `surface`, `text`, `muted`, `border`, `primary`, `success`, `warning`, `danger` y `focus`.
- Usa una paleta intencional, no una colección de colores elegidos componente por componente.
- El color debe indicar jerarquía, interacción, categoría o estado. No añadas colores solo para “dar vida”.
- No uses el mismo color para significados distintos. Un color de éxito no debe convertirse también en decoración o en el color normal de enlaces sin una razón.
- No dependas únicamente del color para comunicar estados: añade texto, icono, forma o patrón cuando sea necesario.
- No adoptes automáticamente una estética morada, azul oscura, beige o monocromática. Tampoco la prohíbas: evalúa si corresponde a la identidad real del producto.
- Revisa los colores sobre sus fondos reales, incluyendo estados hover, focus, disabled, error y dark mode si existe.

### 3.3 Tipografía

- Define una jerarquía real: título de página, encabezado de sección, subtítulo, cuerpo, etiqueta y texto auxiliar.
- Limita las familias tipográficas. Una familia bien configurada suele ser suficiente; una segunda puede reservarse para display, código o una función editorial concreta.
- No elijas Inter, Roboto, Arial, Space Grotesk ni una fuente “de moda” automáticamente. Tampoco las prohíbas por ser populares. Escoge según legibilidad, tono, disponibilidad, idioma y rendimiento.
- No uses tamaños enormes dentro de paneles compactos ni títulos enormes para compensar una estructura vacía.
- Evita pesos `Thin` o `Light` para texto pequeño o de bajo contraste.
- No uses tracking negativo de forma indiscriminada ni conviertas todos los títulos en mayúsculas.
- Evita que el texto dependa de una altura fija. Debe poder crecer, partirse en líneas y adaptarse a traducciones o contenidos más largos.
- No reduzcas el tamaño del texto para hacer caber un layout mal planteado: cambia la distribución o permite que el contenedor crezca.

### 3.4 Espaciado, alineación y composición

- Define una escala de espaciado reutilizable. No ajustes cada margen de manera improvisada.
- Mantén alineaciones compartidas entre títulos, campos, tablas, tarjetas y acciones relacionadas.
- Usa el espacio en blanco para separar grupos de contenido; no lo uses para disimular que falta contenido útil.
- La densidad debe responder al trabajo. Una herramienta de gestión puede necesitar información compacta; una página editorial puede necesitar mayor aire.
- No centres todo por defecto. Usa alineación izquierda para lectura y escaneo cuando resulte natural.
- Evita layouts de tres o cuatro columnas solo porque “se ven equilibrados”. La cantidad de columnas debe derivarse de la prioridad, longitud y relación de los datos.
- No fuerces alturas idénticas cuando eso recorte texto o genere huecos artificiales.
- Diseña el responsive de forma deliberada: reorganiza, oculta solo lo secundario, colapsa navegación cuando sea necesario y conserva el acceso a las acciones importantes.

### 3.5 Tarjetas, contenedores y bordes

- Una tarjeta debe representar una unidad reconocible: un registro, producto, persona, tarea, evento, módulo o herramienta independiente.
- No uses una tarjeta para cada sección de una página. Para secciones, prefiere encabezados, separadores, bandas de ancho completo o grupos sin marco.
- No anides tarjetas. No envuelvas una sección en una tarjeta y luego cada uno de sus controles en otras tarjetas.
- No uses siempre borde + sombra + fondo + radio. Normalmente bastan uno o dos recursos para distinguir una superficie.
- La línea de acento izquierda no es un adorno estándar. Úsala solo con semántica consistente, como una prioridad o estado; no la repitas en cada bloque.
- No hagas que un contenedor parezca clicable si no lo es. Si toda la tarjeta es interactiva, debe tener foco visible y un comportamiento claro.

### 3.6 Iconos y emojis

- Usa una sola familia de iconos coherente con el proyecto (por ejemplo, Lucide, Material Symbols o la librería que ya esté instalada).
- No dibujes SVGs improvisados si el proyecto ya tiene una librería de iconos adecuada.
- No mezcles estilos de trazo, grosores, tamaños ni metáforas distintas sin una razón.
- No uses emojis como sustitutos de iconos funcionales en la interfaz. Su apariencia cambia según plataforma, pueden romper la consistencia visual y no siempre comunican una acción con precisión.
- Los emojis se permiten cuando el producto tiene un tono expresivo y su uso es parte deliberada de la experiencia o del contenido creado por usuarios. No deben ser el sistema de iconografía.
- No agregues un icono a cada tarjeta, título, botón o badge automáticamente.
- Los iconos sin texto deben ser reconocibles. Si su significado no es obvio, añade tooltip y nombre accesible.
- No uses iconos diferentes para la misma acción en distintas pantallas.

### 3.7 Botones, controles y estados

- Mantén una jerarquía clara: acción primaria, secundaria, terciaria y destructiva.
- No hagas que todos los botones sean primarios ni que todos tengan el mismo color y peso.
- Usa controles que correspondan al tipo de dato: checkbox/toggle para opciones binarias; select o menú para opciones; slider/stepper/input para valores numéricos; tabs para cambiar entre vistas relacionadas.
- No simules controles con `div` o elementos no semánticos cuando existe un elemento HTML adecuado.
- Los elementos interactivos deben mostrar estados hover, focus, active, disabled, loading y error cuando correspondan.
- No dejes botones sin acción, enlaces sin destino, filtros cosméticos o controles que solo aparentan funcionar.
- No ocultes acciones importantes dentro de iconos poco conocidos o menús difíciles de descubrir.

### 3.8 Imágenes, ilustraciones y gráficos

- Cada imagen debe representar el producto, objeto, lugar, persona, proceso o contexto real de la pantalla.
- No uses imágenes stock genéricas, fondos abstractos o ilustraciones aleatorias para llenar espacio.
- No uses gráficos sin datos reales o claramente marcados como demostración.
- No inventes cifras, reseñas, testimonios, avatares, logos de clientes, actividad reciente ni indicadores de confianza.
- Todo gráfico debe tener una pregunta que responde. Incluye unidades, escalas, leyendas y periodo de tiempo cuando apliquen.
- Si una tabla comunica mejor los datos que un gráfico, usa una tabla.
- Mantén recortes y proporciones consistentes; no recortes contenido que el usuario necesita inspeccionar.

---

## 4. Contenido y microcopy anti-slop

### Reglas de redacción

- Escribe para las personas que usan el producto, no para impresionar a un jurado o vender una idea abstracta.
- Usa el vocabulario real del dominio y del usuario. Evita jerga interna que el usuario no conoce.
- Prioriza verbos concretos: `Guardar cambios`, `Crear cuenta`, `Buscar cursos`, `Descargar informe`, `Eliminar registro`.
- Los botones deben decir qué ocurrirá. Evita etiquetas vagas como `Continuar`, `Explorar`, `Descubrir` o `Empezar` cuando se puede nombrar la acción concreta.
- Los títulos deben identificar el contenido o la tarea. Evita titulares grandilocuentes que podrían pertenecer a cualquier aplicación.
- Usa frases cortas, voz activa y una idea por oración.
- Elimina texto redundante. No expliques en un párrafo lo que la propia interfaz ya deja claro.
- No uses lorem ipsum, texto de relleno ni mensajes genéricos en una interfaz que se presenta como funcional.
- No inventes nombres, datos de usuario, estadísticas o contenido de ejemplo como si fueran reales. Marca explícitamente los datos ficticios.
- No agregues textos tipo “Bienvenido a tu experiencia”, “Todo lo que necesitas en un solo lugar”, “Lleva tu productividad al siguiente nivel” o “Descubre el poder de…” salvo que exista una razón de marca concreta y aprobada.
- No repitas adjetivos vacíos como `intuitivo`, `potente`, `innovador`, `revolucionario`, `fluido`, `sin esfuerzo` o `de última generación` sin explicar qué característica real los respalda.

### Ejemplos de microcopy

| Genérico / débil | Más claro y útil |
|---|---|
| `¡Bienvenido a tu panel!` | `Resumen de solicitudes` |
| `Comienza tu viaje` | `Crear cuenta` |
| `Explora tus opciones` | `Ver cursos disponibles` |
| `Algo salió mal` | `No se pudo guardar el archivo. Inténtalo de nuevo.` |
| `Enviar` | `Enviar solicitud` |
| `¿Estás seguro?` | `¿Eliminar este registro? Esta acción no se puede deshacer.` |
| `No hay datos` | `Todavía no hay solicitudes registradas.` |

### Mensajes de estado

- **Vacío:** explica por qué no hay elementos y qué acción puede realizar la persona.
- **Carga:** informa que el sistema está trabajando; usa skeletons solo si representan la estructura real que aparecerá.
- **Error:** indica qué falló y cómo recuperarse. No muestres únicamente códigos técnicos.
- **Éxito:** confirma la acción concreta, sin celebraciones exageradas.
- **Deshabilitado:** si no es evidente por qué una acción está deshabilitada, explica qué falta.

---

## 5. UX y accesibilidad: no negociables

- Prioriza las tareas principales del usuario y reduce pasos que no aportan valor.
- Mantén consistencia en navegación, nombres, iconos, comportamiento y ubicación de controles equivalentes.
- Muestra el estado del sistema después de acciones relevantes. No dejes a la persona preguntándose si se guardó, cargó o envió algo.
- Permite cancelar, volver o deshacer cuando sea razonable y seguro.
- Evita exigir memoria innecesaria: deja visibles etiquetas, opciones y contexto necesarios.
- Prevén errores antes de pedir confirmación; reserva las confirmaciones para acciones de riesgo o irreversibles.
- Todos los campos de formulario deben tener etiquetas visibles o nombres accesibles. No uses el placeholder como única etiqueta.
- Identifica errores junto al campo correspondiente y ofrece una corrección cuando se conozca.
- Asegura navegación por teclado, orden de foco lógico y foco visible.
- No comuniques información importante solo mediante color, posición, forma o animación.
- Revisa contraste, ampliación de texto, zoom, reflow y comportamiento con contenidos largos.
- Respeta `prefers-reduced-motion`; no hagas depender la comprensión de una animación.
- En móvil, los controles deben tener un área de interacción cómoda y suficiente separación.

### Referencias WCAG 2.2 para verificación

- Texto normal: contraste mínimo **4.5:1**; texto grande: **3:1** ([WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)).
- Foco de teclado visible ([WCAG 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible)).
- Objetivos de puntero de al menos **24 × 24 CSS px**, salvo excepciones definidas por el criterio ([WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)). Para controles táctiles importantes, considera objetivos mayores.
- Etiquetas e instrucciones para los campos ([WCAG 3.3.2](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html)).
- Identificación textual de errores ([WCAG 3.3.1](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html)).

WCAG es una base comprobable de accesibilidad, no una garantía de que el diseño completo sea usable o atractivo.

---

## 6. Reglas anti-vibe-code slop

La IA no debe tratar el repositorio como un lienzo vacío ni asumir que una solución que compila es una solución correcta.

### Antes de modificar código

1. Inspecciona la estructura, las rutas, los componentes existentes, los estilos globales, los tokens y las dependencias relevantes.
2. Identifica el framework, las convenciones y los patrones ya establecidos.
3. Localiza la pantalla y el flujo exactos que se van a modificar.
4. Distingue errores reales de preferencias estéticas.
5. Presenta un plan breve y el alcance de archivos que probablemente cambiarán antes de implementar cambios amplios.

### Durante la implementación

- Conserva el stack, las convenciones y el sistema de diseño existente, salvo que se haya aprobado un cambio.
- No reescribas páginas o componentes completos cuando un cambio localizado resuelve el problema.
- No inventes funcionalidades, rutas, roles, datos o comportamientos que no estén en los requisitos.
- No agregues dependencias para resolver algo que el proyecto ya puede hacer de forma sencilla.
- Verifica que cada paquete nuevo exista, esté mantenido y sea compatible con el proyecto.
- Reutiliza componentes cuando compartan comportamiento y significado; no conviertas cada bloque en un componente abstracto innecesario.
- Evita componentes monolíticos, lógica duplicada, nombres opacos y CSS contradictorio.
- Centraliza tokens y estilos repetidos. No crees valores de color, spacing o radius distintos para cada componente sin necesidad.
- No ocultes errores con `any`, `@ts-ignore`, `eslint-disable`, comentarios engañosos o supresión de tests sin justificarlo.
- No reemplaces datos reales por mocks silenciosamente. Si necesitas datos de prueba, delimítalos y etiquétalos como tales.
- No afirmes que una función funciona solo porque el código fue generado o la pantalla se renderiza.
- No modifiques archivos fuera del alcance acordado sin explicar por qué.

### Después de implementar

- Ejecuta el build, lint y tests disponibles; informa exactamente qué se ejecutó y qué no.
- Prueba el flujo real: acciones, navegación, formularios, filtros, estados de error, carga y vacío.
- Revisa errores de consola y solicitudes fallidas.
- Comprueba el resultado en al menos un viewport de escritorio y uno móvil; revisa también un tamaño intermedio cuando el layout sea complejo.
- Inspecciona capturas de pantalla, no solo el DOM o el hecho de que el servidor arranque.
- Verifica que no existan solapamientos, texto cortado, scroll horizontal accidental ni cambios de layout al cargar datos.
- Revisa el diff para identificar cambios no solicitados, duplicación, dependencias innecesarias o regresiones.
- Explica limitaciones y pruebas no ejecutadas. Nunca declares “terminado” si no has validado el resultado.

---

## 7. Ingeniería de prompts para obtener mejores resultados

La calidad del prompt depende más de la información concreta y las restricciones que de adjetivos como “increíble”, “premium” o “moderno”. Para tareas de frontend, especifica tres bloques: **qué producto/pantalla**, **quién lo usa y para qué**, y **qué restricciones visuales y técnicas debe respetar**.

### Información que debe incluir un buen prompt

1. **Contexto:** qué hace el producto y qué problema resuelve.
2. **Usuarios:** quién utilizará la pantalla y qué conocimientos o limitaciones tiene.
3. **Tarea principal:** qué necesita completar o decidir el usuario.
4. **Contenido real:** datos, campos, estados, acciones y relaciones entre elementos.
5. **Alcance:** qué pantalla o componentes se pueden tocar y qué queda fuera.
6. **Dirección visual:** atributos visuales concretos y referencias con explicación de qué se toma de ellas.
7. **Restricciones:** stack, componentes disponibles, responsive, accesibilidad y compatibilidad.
8. **Anti-patrones:** qué elementos no debe introducir por defecto.
9. **Criterios de aceptación:** cómo se verificará que el trabajo está bien hecho.
10. **Proceso:** analizar primero, proponer el plan, implementar, ejecutar pruebas y revisar capturas/diff.

### Cómo describir una dirección visual

No escribas únicamente: `Hazlo moderno, bonito y profesional.`

Especifica decisiones observables, por ejemplo:

- `Herramienta operativa y sobria, con densidad media-alta, fondo neutro, un único color de acción y jerarquía tipográfica compacta.`
- `Evita el aspecto de landing page. La primera pantalla debe priorizar la tabla de registros, filtros y acciones.`
- `Usa secciones sin marco para agrupar contenido; reserva tarjetas para registros independientes.`
- `Iconografía outline consistente de una sola librería; no emojis como iconos funcionales.`
- `La interfaz debe sentirse propia del dominio, no como un dashboard de SaaS genérico.`

### Uso de referencias visuales

Cuando proporciones capturas o URLs de referencia:

- Indica qué característica se debe estudiar: navegación, jerarquía, proporción, densidad, tabla, tipografía o interacción.
- Indica qué NO se debe copiar: marca, colores, composición completa, contenido o elementos ajenos al producto.
- Da más de una referencia si buscas combinar cualidades distintas.
- No pidas “hazlo igual” sin describir qué propiedad debe reproducirse.

### Divide tareas grandes

No pidas “rediseña toda la aplicación y mejora todo”. Divide por pantalla o flujo:

1. Auditoría del estado actual, sin modificar código.
2. Propuesta de dirección visual y jerarquía.
3. Implementación de un área concreta.
4. Revisión responsive y de estados.
5. Auditoría final del diff, accesibilidad y consistencia.

---

## 8. Prompts listos para reutilizar

### A. Auditoría inicial — no modificar código

```text
Actúa como diseñador senior de producto digital y frontend engineer. Audita la interfaz existente de este proyecto para detectar AI slop visual, problemas de UX y deuda de implementación.

Primero inspecciona el código, las rutas, los componentes, el sistema de estilos y las dependencias relevantes. No modifiques ningún archivo todavía.

Evalúa:
- Jerarquía visual, layout, densidad y espaciado.
- Uso excesivo o injustificado de tarjetas, contenedores anidados, bordes, sombras y líneas de acento.
- Paleta, tipografía, iconografía, emojis, botones y badges.
- Textos genéricos, redundantes o que no describen acciones reales.
- Estados de carga, vacío, error, éxito, hover, focus y disabled.
- Responsive, accesibilidad, consistencia y patrones repetidos.
- Componentes duplicados, estilos improvisados y dependencias innecesarias.

No consideres un recurso visual incorrecto por sí solo: explica qué problema crea en este contexto y qué alternativa concreta propones.

Entrega:
1. Hallazgos ordenados por impacto (alto, medio, bajo).
2. Evidencia: pantalla/componente/archivo afectado.
3. Solución recomendada y motivo.
4. Elementos que sí conviene conservar.
5. Alcance mínimo de archivos que habría que modificar.
6. Riesgos de romper funcionalidades existentes.

No inventes datos ni funcionalidades. No implementes hasta que exista una propuesta clara.
```

### B. Implementación de una mejora concreta

```text
Implementa únicamente la mejora acordada para [PANTALLA / COMPONENTE / FLUJO].

CONTEXTO DEL PRODUCTO:
[Qué hace el producto y quién lo utiliza.]

TAREA DEL USUARIO:
[Qué necesita completar o decidir en esta pantalla.]

CONTENIDO Y FUNCIONES QUE DEBEN CONSERVARSE:
[Datos, campos, botones, filtros, rutas, estados y reglas de negocio actuales.]

DIRECCIÓN VISUAL:
[3–5 atributos concretos y cómo deben traducirse a la interfaz.]

REGLAS ANTI-SLOP:
- No conviertas cada sección en una tarjeta ni anides tarjetas.
- No uses la línea de acento izquierda como decoración repetida.
- No introduzcas degradados morados, orbes, blobs o fondos decorativos por defecto.
- No uses emojis como iconos funcionales ni mezcles librerías de iconos.
- No agregues métricas, textos, testimonios ni datos ficticios como si fueran reales.
- No añadas animaciones sin una función de interacción o feedback.
- No cambies el flujo, la lógica de negocio ni las rutas fuera del alcance solicitado.
- No agregues dependencias sin justificar su necesidad.

RESTRICCIONES TÉCNICAS:
[Framework, librerías permitidas, convenciones existentes y archivos que no se deben tocar.]

CRITERIOS DE ACEPTACIÓN:
[Qué debe poder hacer el usuario y cómo se comprobará visual y funcionalmente.]

Proceso:
1. Revisa el contexto y confirma qué archivos vas a modificar.
2. Implementa el cambio más pequeño que resuelva el objetivo.
3. Verifica build, lint y tests disponibles.
4. Comprueba escritorio y móvil, incluyendo texto largo y estados relevantes.
5. Revisa capturas, consola y diff.
6. Informa qué cambió, qué pruebas pasaron y qué quedó sin verificar.

No declares terminado algo que no hayas probado.
```

### C. Revisión anti-slop después de implementar

```text
Haz una revisión crítica de la interfaz implementada. No añadas nuevas funcionalidades ni rediseñes por gusto.

Busca específicamente:
- Elementos decorativos sin propósito.
- Tarjetas repetidas o anidadas, badges excesivos y líneas de acento arbitrarias.
- Paleta, tipografía, iconos o radios inconsistentes.
- Texto genérico, redundante o inventado.
- Jerarquía visual confusa o acciones importantes escondidas.
- Estados faltantes, controles falsos o feedback incompleto.
- Problemas de teclado, foco, contraste, etiquetas y tamaño de objetivos.
- Diferencias entre escritorio y móvil, overflow, recortes y solapamientos.
- Código duplicado, dependencia innecesaria, errores silenciados o pruebas debilitadas.

Para cada hallazgo indica: severidad, evidencia, impacto y corrección mínima. Distingue claramente entre defecto real y preferencia personal. Corrige solo los defectos de alta confianza y vuelve a probarlos.
```

### D. Revisión de código generado

```text
Revisa el diff como un reviewer responsable del mantenimiento del proyecto.

Comprueba:
- Si el cambio respeta la arquitectura y las convenciones existentes.
- Si hay archivos modificados fuera del alcance.
- Si se agregaron dependencias, APIs o componentes innecesarios o inexistentes.
- Si hay lógica duplicada, componentes monolíticos, nombres confusos o tipos débiles.
- Si se eliminaron, desactivaron o modificaron tests para ocultar fallos.
- Si los tests comprueban el comportamiento esperado y no solo detalles internos de implementación.
- Si los estados de error, carga, vacío y límites están cubiertos.

No asumas que el código es correcto porque compila. No modifiques el alcance para hacer pasar las pruebas. Devuelve primero hallazgos priorizados y después una corrección mínima con sus resultados de validación.
```

---

## 9. Checklist de aceptación

Antes de aprobar una pantalla o un PR, marca cada punto:

### Diseño y contenido

- [ ] Se entiende qué es esta pantalla y cuál es su tarea principal.
- [ ] La jerarquía visual refleja la importancia real de la información.
- [ ] No hay tarjetas, bordes, sombras, badges o acentos repetidos sin función.
- [ ] La paleta y la tipografía tienen una razón y son consistentes.
- [ ] Los iconos pertenecen a un sistema coherente; no se usaron emojis como sustitutos arbitrarios.
- [ ] Los textos son específicos, breves y verdaderos.
- [ ] No hay datos, reseñas, métricas o funcionalidades inventadas.
- [ ] Las imágenes y gráficos representan el contenido real.

### UX y accesibilidad

- [ ] Todos los controles hacen lo que indican.
- [ ] Existen estados de carga, vacío, error, éxito y disabled cuando se necesitan.
- [ ] Se puede navegar con teclado y el foco es visible.
- [ ] Los campos tienen etiquetas y los errores indican cómo recuperarse.
- [ ] El contraste cumple los mínimos aplicables de WCAG 2.2 AA.
- [ ] No se comunica información únicamente con color.
- [ ] El layout funciona con zoom, texto largo y tamaños de pantalla distintos.

### Código y validación

- [ ] Se inspeccionó el diff y no hay cambios ajenos al alcance.
- [ ] No se introdujeron dependencias injustificadas.
- [ ] No se silenciaron errores ni se eliminaron tests para aparentar éxito.
- [ ] Build, lint y tests disponibles se ejecutaron; los resultados se informaron.
- [ ] Se revisó visualmente la interfaz en escritorio y móvil.
- [ ] Se comprobaron consola, interacciones y estados relevantes.

**Criterio de rechazo:** no aprobar si existe un fallo funcional, una acción falsa, contenido inventado presentado como real, una regresión importante de responsive o un problema crítico de accesibilidad. Los defectos visuales de severidad alta también deben corregirse antes de integrar.

---

## 10. Rúbrica rápida de calidad

Puntúa cada categoría de 0 a 2:

- **0 — Deficiente:** genérico, inconsistente, incompleto o no verificado.
- **1 — Aceptable:** funciona, pero existen decisiones débiles o detalles importantes pendientes.
- **2 — Sólido:** intencional, coherente, probado y adaptado al contexto.

| Categoría | Puntuación (0–2) |
|---|---:|
| Identidad visual y coherencia |  |
| Jerarquía y layout |  |
| Tipografía, color e iconografía |  |
| Claridad del contenido |  |
| UX y estados de interacción |  |
| Accesibilidad y responsive |  |
| Mantenibilidad del código |  |
| Pruebas y revisión del resultado |  |
| **Total (máximo 16)** |  |

**Interpretación sugerida:** 14–16 listo para revisión final; 11–13 requiere pulido; 8–10 requiere otra iteración; 0–7 no debería integrarse. Un promedio alto no compensa un fallo crítico: los criterios de rechazo anteriores prevalecen.

---

## 11. Fuentes y fundamento

Esta guía combina principios generales de UX y accesibilidad con recomendaciones específicas de ingeniería de prompts y revisión de código generado por IA. Las reglas de esta guía son una adaptación práctica para el proyecto, no una norma oficial única llamada “Anti-AI Slop”.

1. **OpenAI — Frontend prompt instructions.** Recomendaciones explícitas para orientar interfaces generadas: adecuar diseño al dominio, evitar secciones flotantes y tarjetas anidadas, no introducir orbes decorativos, usar controles apropiados y verificar la interfaz en varios tamaños.  
   https://developers.openai.com/api/docs/guides/frontend-prompt

2. **Anthropic — Prompting best practices, sección “Frontend design”.** Reconoce la tendencia de los modelos a producir patrones genéricos o “AI slop” y destaca tipografía, paleta, movimiento, fondos y carácter específico del contexto.  
   https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

3. **Nielsen Norman Group — 10 Usability Heuristics for User Interface Design.** Referencia para visibilidad del estado, lenguaje familiar, control del usuario, consistencia, prevención de errores, reconocimiento y diseño minimalista.  
   https://www.nngroup.com/articles/ten-usability-heuristics/

4. **W3C — Web Content Accessibility Guidelines (WCAG) 2.2.** Criterios verificables de contraste, foco visible, tamaño de objetivos, etiquetas e identificación de errores.  
   https://www.w3.org/TR/WCAG22/

5. **GOV.UK — Writing for user interfaces.** Recomendaciones para reducir carga cognitiva, usar lenguaje del usuario y escribir microcopy corto, directo y útil.  
   https://www.gov.uk/service-manual/design/writing-for-user-interfaces

6. **GOV.UK — Understand content design.** El contenido debe partir de necesidades reales del usuario, considerar la cantidad y formato adecuados y mantenerse actualizado.  
   https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/plan-manage-content/understand-content-design/

7. **Vercel — How to prompt v0 (15 diciembre 2025).** Estructura prompts de frontend a partir de superficie del producto, contexto de uso y restricciones/dirección visual.  
   https://vercel.com/blog/how-to-prompt-v0

8. **Visual Studio Code — Best practices for using AI in VS Code.** Recomienda delimitar tareas, proporcionar contexto, separar exploración/plan/implementación y verificar el resultado y el diff.  
   https://code.visualstudio.com/docs/agents/best-practices

9. **GitHub — Review AI-generated code.** Recalca comprobaciones funcionales, contexto y arquitectura, calidad, dependencias, revisión humana y detección de errores específicos de IA.  
   https://docs.github.com/en/copilot/tutorials/review-ai-generated-code

10. **Martin Fowler — Agentic Engineering y Vibe Coding (21 mayo 2026).** Distingue el uso supervisado de agentes del vibe coding sin revisar el código; advierte de riesgos de mantenibilidad, corrección y seguridad cuando se ignora el código generado.  
    https://martinfowler.com/bliki/AgenticEngineering.html  
    https://martinfowler.com/bliki/VibeCoding.html

11. **Matteo Vaccari / Martin Fowler — Tests as data (11 noviembre 2026).** Analiza el riesgo de confiar ciegamente en tests generados y modificados por agentes; recomienda contratos de prueba legibles y centrados en el comportamiento esperado.  
    https://www.martinfowler.com/articles/tests-as-data.html

---

## Regla final para cualquier agente

**No diseñes para demostrar que puedes generar una interfaz llamativa. Diseña para que una persona real entienda, confíe y complete su tarea. No implementes para demostrar que puedes producir mucho código. Implementa el cambio mínimo correcto, comprueba su comportamiento y deja el proyecto más fácil de mantener que antes.**
