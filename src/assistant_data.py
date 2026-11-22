"""Datos para entrenar el modelo de lenguaje del asistente: preguntas etiquetadas con su INTENCIÓN y la FALLA mencionada.

Honestidad sobre los datos: no existe un corpus real de operadores de fresadoras, así que las preguntas de entrenamiento se
generan combinando frases escritas a mano (marcos de pregunta × descripciones de falla) con variaciones realistas
(cortesías, número de máquina, tildes omitidas, errores de tecleo).

Para que la evaluación no sea una trampa, la partición se hace por FAMILIAS DE FRASES: las frases base y los marcos de
pregunta de validación/prueba nunca aparecen en entrenamiento (solo cambian las variaciones). Además hay un conjunto
NATURAL de preguntas escritas aparte, a mano, que no sale de ninguna plantilla: es la prueba más exigente.
"""
import random
import re
import unicodedata

INTENTS = ["que_hago", "por_que", "cuanto", "seguir", "prevenir", "planta", "fuera"]
CAUSES = ["ninguna", "HDF", "PWF_high", "PWF_low", "OSF", "TWF"]

# --------------------------------------------------------------------------- frases base (sin falla concreta)
BASE = {
    "que_hago": [
        "qué hago", "qué debo hacer", "cómo lo soluciono", "cómo lo arreglo", "qué acción tomo", "qué me recomiendas", "ayúdame con esta falla",
        "qué puedo hacer", "qué hago con esta fresadora", "qué hago con esta máquina", "cómo la reparo", "cómo corrijo el problema", "qué hago ante esta falla",
        "dime qué hacer", "cómo actúo ahora", "necesito una solución", "qué medida tomo", "qué sugieres que haga", "cómo evito que falle ahora",
        "qué ajusto para que no falle", "cómo la salvo antes de que falle", "qué parámetro cambio", "aconséjame qué hacer", "qué hago para bajar el riesgo",
    ],
    "por_que": [
        "por qué sube el riesgo", "por qué va a fallar", "cuál es la causa", "qué está pasando", "por qué hay alerta", "qué causa el problema", "por qué falló",
        "explícame la alerta", "de dónde viene el riesgo", "qué significa esta falla", "por qué se puso en rojo", "a qué se debe la alerta", "qué provoca el riesgo",
        "cuál es el motivo de la alerta", "por qué me avisa la IA", "qué factor empuja el riesgo", "por qué la IA dice que va a fallar", "qué le pasa a esta fresadora",
        "por qué se detuvo", "cuál es el origen del problema", "por qué aumentó el riesgo",
    ],
    "cuanto": [
        "cuánto tiempo tengo", "cuándo va a fallar", "cuánto falta para la falla", "es urgente", "qué tan pronto falla", "cuántos pasos me quedan", "tengo tiempo",
        "en cuánto tiempo falla", "cuánto me queda", "cuándo debo actuar", "falla pronto", "qué tan grave es", "cuánto margen tengo", "es para ya o puede esperar",
        "cuánto puedo esperar", "me da tiempo de terminar el lote", "qué tan cerca está de fallar", "cuánto aguanta así",
    ],
    "seguir": [
        "puedo seguir produciendo", "es seguro seguir trabajando", "debo detener la máquina", "puedo seguir usándola", "la paro o sigo", "es peligroso seguir",
        "la apago", "puedo continuar con el trabajo", "conviene parar la fresadora", "sigo con el lote", "es seguro dejarla funcionando", "tengo que parar ya",
        "puedo terminar la pieza", "debo apagarla", "sigo cortando o paro", "me arriesgo a seguir",
    ],
    "prevenir": [
        "cómo evito que se repita", "cómo prevengo esta falla", "cómo lo evito a futuro", "qué mantenimiento preventivo hago", "qué hago para que no vuelva a pasar",
        "cómo evitar que ocurra de nuevo", "qué hago para prevenirlo", "cómo la mantengo para que no falle", "qué rutina de mantenimiento recomiendas", "cómo anticipo este problema",
        "cómo reduzco las fallas a largo plazo", "qué reviso cada semana para que no falle", "cómo evito paradas futuras", "qué buenas prácticas evitan esto",
    ],
    "planta": [
        "cómo está la planta", "cuál está peor", "cuál tiene más riesgo", "resumen de la planta", "cuáles están en alerta", "a cuál atiendo primero", "qué atiendo primero",
        "cómo está el taller", "cuáles están detenidas", "cuál es la más crítica", "dame un resumen del taller", "qué fresadoras tienen problemas", "cuántas máquinas fallan",
        "por cuál empiezo", "cuál es la prioridad", "cuáles están en riesgo ahora", "cómo van todas las fresadoras", "ordena las máquinas por riesgo",
    ],
    "fuera": [
        "hola", "buenos días", "buenas tardes", "gracias", "quiero pizza", "cuál es la capital de Perú", "cuéntame un chiste", "qué hora es", "cómo estás", "quién ganó el partido",
        "cómo está el clima", "recomiéndame una película", "cuánto es dos más dos", "quién eres", "cómo se hace un ceviche", "me aburro", "qué día es hoy", "háblame de fútbol",
        "cómo se dice hola en inglés", "escribe un poema", "adiós", "qué tal", "dónde compro una fresadora", "quién inventó la fresadora", "cuánto cuesta una fresadora CNC",
        "qué es el aprendizaje automático", "cuál es tu color favorito", "cómo apruebo el curso", "ayúdame con mi tarea de matemáticas", "traduce esta frase al inglés",
        "cuántos años tienes", "me puedes ayudar con mi tesis", "qué es una red neuronal", "cómo instalo Python", "dónde queda la universidad", "qué precio tiene el acero",
        "cómo se llama el profesor", "dime algo interesante", "qué opinas de la inteligencia artificial", "cuál es la mejor marca de herramientas",
    ],
}

# --------------------------------------------------------------------------- falla mencionada
NOUNS = {
    "HDF": ["el calor excesivo", "el sobrecalentamiento", "la temperatura alta", "la falla por calor", "la mala refrigeración", "el problema de refrigeración",
            "la falta de disipación de calor", "el calentamiento del husillo", "la fresadora caliente", "el refrigerante que no enfría", "la temperatura que no baja",
            "el exceso de temperatura", "la falla de enfriamiento"],
    "PWF_high": ["la sobrecarga de potencia", "el consumo de potencia muy alto", "la potencia por encima del límite", "la sobrecarga del motor", "el exceso de potencia",
                 "la potencia alta", "la potencia que se pasa del máximo", "la sobrecarga del husillo", "el motor exigido de más", "la demanda de potencia excesiva"],
    "PWF_low": ["la potencia muy baja", "la falta de potencia", "la caída de potencia", "la potencia por debajo del mínimo", "la fresadora que casi no corta", "la poca potencia",
                "la potencia que cayó", "el motor sin fuerza", "la baja de potencia", "la fresa que gira sin cortar"],
    "OSF": ["la sobretensión mecánica", "el exceso de torque", "la sobrecarga por desgaste y torque", "el esfuerzo excesivo en la herramienta", "la sobretensión",
            "el torque demasiado alto", "la falla por sobretensión", "el esfuerzo mecánico excesivo", "la carga mecánica excesiva", "el torque que se pasó del límite"],
    "TWF": ["el desgaste de la herramienta", "la fresa gastada", "la herramienta vieja", "el filo desgastado", "la herramienta al final de su vida", "la falla por desgaste",
            "la fresa que ya cumplió su vida útil", "la herramienta con muchas horas", "el desgaste de la fresa", "la herramienta que ya no corta bien", "la fresa muy usada",
            "la herramienta que lleva más de doscientos minutos"],
}
FRAMES = {
    "que_hago": ["qué hago con {n}", "cómo soluciono {n}", "{n}, qué hago", "cómo arreglo {n}", "qué acción tomo ante {n}", "ayúdame con {n}", "tengo {n}, qué puedo hacer",
                 "cómo corrijo {n}", "qué medida tomo frente a {n}", "necesito resolver {n}", "qué recomiendas ante {n}", "cómo atiendo {n}"],
    "por_que": ["por qué tengo {n}", "a qué se debe {n}", "qué causa {n}", "{n}, por qué pasa", "de dónde viene {n}", "por qué aparece {n}", "qué origina {n}",
                "explícame {n}", "cuál es el motivo de {n}", "por qué ocurre {n}"],
    "cuanto": ["cuánto tiempo tengo con {n}", "{n}, es urgente", "qué tan pronto falla con {n}", "cuánto aguanta con {n}", "{n}, cuánto margen tengo", "falla pronto por {n}",
               "cuándo debo actuar ante {n}", "qué tan grave es {n}", "cuánto puedo esperar con {n}"],
    "seguir": ["puedo seguir produciendo con {n}", "es seguro trabajar con {n}", "con {n}, la paro o sigo", "debo detener la máquina por {n}", "puedo continuar con {n}",
               "conviene parar por {n}", "con {n}, sigo con el lote", "es peligroso seguir con {n}", "tengo que apagarla por {n}"],
    "prevenir": ["cómo prevengo {n}", "cómo evito {n} a futuro", "qué hago para que no vuelva {n}", "cómo evito que se repita {n}", "qué mantenimiento evita {n}",
                 "cómo reduzco {n}", "qué rutina previene {n}", "cómo anticipo {n}", "qué buenas prácticas evitan {n}"],
}


# --------------------------------------------------------------------------- más paraphrases (ampliación del banco)
BASE["que_hago"] += ["cómo la arreglo ya", "qué se hace en este caso", "dime los pasos para solucionarlo", "cómo lo resuelvo", "qué hago primero", "cuál es la acción correcta",
                     "qué debo ajustar", "cómo bajo el riesgo", "indícame qué hacer", "qué opción me recomiendas", "cómo la ayudo", "qué corrijo", "cómo actúo ante esta alerta",
                     "necesito arreglar esto", "cómo lo controlo", "qué cambio en la máquina"]
BASE["por_que"] += ["a qué se debe esto", "por qué está pasando esto", "qué la está afectando", "por qué la IA marca riesgo", "explícame qué pasa", "cuál es la razón",
                    "qué lo provoca", "por qué está mal", "por qué se puso en alerta", "qué tiene la fresadora", "cuál es el problema", "por qué cambió el riesgo",
                    "qué variable causa el problema", "qué le pasó", "por qué marca rojo"]
BASE["cuanto"] += ["cuánto tiempo me da", "cuántos minutos me quedan", "falla ya o puede esperar", "qué tan inminente es", "cuánto falta", "me alcanza el tiempo", "en cuántos pasos falla",
                   "con cuánta urgencia debo actuar", "cuánto tiempo hay antes de la falla", "tengo margen", "cuánto margen hay", "qué tan rápido va a fallar"]
BASE["seguir"] += ["la dejo funcionando", "continúo con la producción", "paro la producción", "qué hago, paro o sigo", "puedo trabajar así", "debo parar ya la fresadora",
                   "es riesgoso seguir así", "la dejo prendida", "sigo o detengo", "me conviene parar", "puedo dejarla trabajando", "detengo el ciclo"]
BASE["prevenir"] += ["cómo evito esto en el futuro", "cómo evito que pase otra vez", "qué hago para que no ocurra más", "cómo mantengo la máquina sana", "qué se hace de forma preventiva",
                     "cómo prevenir fallas", "qué hacer para evitar paradas", "cada cuánto hago mantenimiento", "cómo cuido la fresadora", "cómo evito que vuelva a fallar"]
BASE["planta"] += ["cuál reviso primero", "qué máquina está peor", "cuál está más crítica", "qué fresadoras están en rojo", "estado general", "cómo anda el taller",
                   "cuáles requieren atención", "cuáles están bien", "dime las máquinas con problemas", "quiero ver todas las alertas", "cuál es la peor fresadora"]
BASE["fuera"] += ["cuál es el sentido de la vida", "ponme música", "quién es el presidente", "dime un dato curioso", "cómo se prepara un pisco sour", "explícame la fotosíntesis",
                  "qué es Python", "dónde puedo estudiar", "cómo me llamo", "cuál es tu nombre", "ayúdame a escribir un correo", "recomiéndame un libro",
                  "cuánto mide el Everest", "qué se come hoy", "quién descubrió América", "cómo hago una tesis", "te quiero", "eres inteligente"]
FRAMES["que_hago"] += ["qué se hace ante {n}", "cómo enfrento {n}", "dime cómo resolver {n}", "qué pasos sigo con {n}"]
FRAMES["por_que"] += ["qué hay detrás de {n}", "por qué me pasa {n}", "a qué atribuyo {n}"]
FRAMES["cuanto"] += ["cuánto tiempo hay con {n}", "con {n}, falla ya", "qué tan inminente es {n}"]
FRAMES["seguir"] += ["con {n}, puedo trabajar", "continúo con {n}", "paro por {n}"]
FRAMES["prevenir"] += ["cómo evito en el futuro {n}", "qué hago para no tener {n}", "cómo prevenir {n}"]
NOUNS["HDF"] += ["el calor", "la temperatura", "el sobrecalentamiento del proceso", "que se calienta mucho", "que no se enfría"]
NOUNS["PWF_high"] += ["la sobrecarga", "la potencia excesiva", "que consume demasiada potencia", "el motor que jala de más"]
NOUNS["PWF_low"] += ["la baja potencia", "que no tiene fuerza", "que casi no corta", "la potencia insuficiente"]
NOUNS["OSF"] += ["el torque excesivo", "el exceso de esfuerzo", "que se fuerza la herramienta", "la tensión mecánica excesiva"]
NOUNS["TWF"] += ["el desgaste", "la fresa que ya no sirve", "la herramienta que se gastó", "que la herramienta está gastada"]

# --------------------------------------------------------------------------- variaciones
PREFIX = ["", "", "", "oye, ", "disculpa, ", "por favor, ", "urgente: ", "ayuda, ", "una consulta: ", "profe, ", "hola, ", "mira, ", "ey ", "buenas, "]
SUFFIX = ["", "", "", " por favor", " porfa", " ahora", " rápido", " gracias", " en esta máquina", " aquí", " hoy", " ya"]
MACHINE = ["", "", "", "", " en la fresadora {k}", " de la máquina {k}", " en la {k}", " de Fresadora {k:02d}", " en M-{k:02d}", " en la fresadora número {k}"]


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def vary(text, rng, level=1.0):
    """Variaciones de escritura: cortesías, máquina mencionada, tildes, mayúsculas, signos y errores de tecleo."""
    text = rng.choice(PREFIX) + text + rng.choice(SUFFIX)
    m = rng.choice(MACHINE)
    if m:
        text += m.format(k=rng.randint(1, 12))
    if rng.random() < .35 * level:
        text = strip_accents(text)
    r = rng.random()
    text = text.lower() if r < .3 else text.upper() if r < .35 else text.capitalize() if r < .6 else text
    if rng.random() < .5:
        text += rng.choice(["?", "??", "", "...", "!"])
    if rng.random() < .5 * level and len(text) > 6:  # error de tecleo: borrar o intercambiar una letra
        i = rng.randint(1, len(text) - 3)
        text = text[:i] + text[i + 1:] if rng.random() < .5 else text[:i] + text[i + 1] + text[i] + text[i + 2:]
    return re.sub(r"\s+", " ", text).strip()


def _split_items(items, rng, fractions=(.6, .2, .2)):
    items = list(items)
    rng.shuffle(items)
    n = len(items)
    a, b = max(1, round(n * fractions[0])), max(1, round(n * fractions[1]))
    return {"train": items[:a], "val": items[a:a + b], "test": items[a + b:] or items[-1:]}


def build(seed=0, per_item=6):
    """Devuelve {'train','val','test'}: listas de (texto, intención, falla). Partición por familias de frases."""
    rng = random.Random(seed)
    out = {"train": [], "val": [], "test": []}
    base = {i: _split_items(v, rng) for i, v in BASE.items()}
    nouns = {c: _split_items(v, rng) for c, v in NOUNS.items()}
    frames = {i: _split_items(v, rng) for i, v in FRAMES.items()}
    for part in out:
        for intent, parts in base.items():
            for phrase in parts[part]:
                for _ in range(per_item):
                    out[part].append((vary(phrase, rng), intent, "ninguna"))
        for intent, fparts in frames.items():
            for cause, nparts in nouns.items():
                for fr in fparts[part]:
                    for n in nparts[part]:
                        for _ in range(max(1, per_item // 3)):
                            out[part].append((vary(fr.format(n=n), rng), intent, cause))
        # mezcla de falla sin pregunta explícita: «el calor excesivo» a secas (intención: que_hago por defecto)
        for cause, nparts in nouns.items():
            for n in nparts[part]:
                out[part].append((vary(n, rng), "que_hago", cause))
        rng.shuffle(out[part])
    return out


# --------------------------------------------------------------------------- conjunto natural (escrito a mano, fuera de las plantillas)
NATURAL = [
    ("la fresadora 4 se está calentando demasiado, ¿qué hago?", "que_hago", "HDF"),
    ("¿por qué me sale alerta en la 7?", "por_que", "ninguna"),
    ("me quedan pocos minutos antes de que falle?", "cuanto", "ninguna"),
    ("sigo cortando o la paro?", "seguir", "ninguna"),
    ("¿cómo hago para que no se me vuelva a gastar tan rápido la fresa?", "prevenir", "TWF"),
    ("¿cuál de todas las máquinas está más grave?", "planta", "ninguna"),
    ("quiero saber la receta del arroz con pollo", "fuera", "ninguna"),
    ("el motor está jalando muchísimo, creo que se sobrecarga", "que_hago", "PWF_high"),
    ("la máquina casi no está cortando, tiene poca potencia", "que_hago", "PWF_low"),
    ("el refrigerante no está enfriando como antes", "por_que", "HDF"),
    ("¿se podrá terminar el pedido con esta herramienta tan vieja?", "seguir", "TWF"),
    ("¿qué máquina reviso primero hoy?", "planta", "ninguna"),
    ("¿hay riesgo de que se me rompa la fresa?", "cuanto", "TWF"),
    ("auxilio, la 12 está en rojo", "que_hago", "ninguna"),
    ("por qué el torque está tan alto?", "por_que", "OSF"),
    ("¿cada cuánto debo cambiar la herramienta para evitar problemas?", "prevenir", "TWF"),
    ("dime cómo van las máquinas", "planta", "ninguna"),
    ("¿me puedes decir quién es el presidente?", "fuera", "ninguna"),
    ("la potencia se pasó del límite, ¿es grave?", "cuanto", "PWF_high"),
    ("qué pasa si la dejo funcionando así", "seguir", "ninguna"),
    ("se detuvo la fresadora 3, ¿qué tengo que hacer?", "que_hago", "ninguna"),
    ("¿por qué se paró sola?", "por_que", "ninguna"),
    ("cómo evito el sobrecalentamiento del husillo en verano", "prevenir", "HDF"),
    ("necesito ayuda con el exceso de torque", "que_hago", "OSF"),
    ("está muy caliente la temperatura del proceso", "por_que", "HDF"),
    ("cuánto me falta para que explote el riesgo", "cuanto", "ninguna"),
    ("¿conviene parar la 9?", "seguir", "ninguna"),
    ("a qué hora cierra el banco", "fuera", "ninguna"),
    ("resumen del turno por favor", "planta", "ninguna"),
    ("¿el desgaste de la fresa es la causa?", "por_que", "TWF"),
    ("¿cómo evito que la potencia caiga tanto?", "prevenir", "PWF_low"),
    ("la máquina gira pero no corta nada, ¿qué hago?", "que_hago", "PWF_low"),
    ("¿debo cambiar la herramienta ya?", "que_hago", "TWF"),
    ("¿es normal que el torque suba tanto con una fresa gastada?", "por_que", "OSF"),
    ("tengo prisa, ¿cuánto tiempo me da la IA?", "cuanto", "ninguna"),
    ("cuéntame algo de Machu Picchu", "fuera", "ninguna"),
    ("¿la dejo prendida mientras almuerzo?", "seguir", "ninguna"),
    ("qué mantenimiento le toca a las fresadoras para que no se calienten", "prevenir", "HDF"),
    ("¿cuáles están detenidas?", "planta", "ninguna"),
    ("que hago con la sobretension", "que_hago", "OSF"),
    ("xq sube el riesgo en la 5", "por_que", "ninguna"),
    ("la potencia está altísima, ¿la apago?", "seguir", "PWF_high"),
    ("dame consejos para mantener las fresas en buen estado", "prevenir", "TWF"),
    ("¿podrías explicarme qué es un gradiente descendente?", "fuera", "ninguna"),
    ("cuántas horas le quedan a la herramienta?", "cuanto", "TWF"),
    ("necesito bajar la temperatura ya", "que_hago", "HDF"),
    ("¿qué puede estar causando tanta potencia?", "por_que", "PWF_high"),
    ("¿cuál es la fresadora con más riesgo?", "planta", "ninguna"),
    ("ayúdame, algo anda mal con la 2", "que_hago", "ninguna"),
    ("¿es peligroso seguir con tanto calor?", "seguir", "HDF"),
    ("cómo evitar que se sobrecargue el motor", "prevenir", "PWF_high"),
    ("juguemos algo", "fuera", "ninguna"),
    ("¿cuánto falta para que la herramienta llegue a su límite?", "cuanto", "TWF"),
    ("¿qué hago si la fresa está muy usada?", "que_hago", "TWF"),
    ("¿por qué hay poca potencia en el husillo?", "por_que", "PWF_low"),
    ("¿hay alguna máquina que deba apagar?", "planta", "ninguna"),
    ("¿sigo con el pedido aunque la IA avise?", "seguir", "ninguna"),
    ("cómo mantengo el refrigerante para que no falle", "prevenir", "HDF"),
    ("¿me recomiendas un buen restaurante?", "fuera", "ninguna"),
    ("la fresadora 6 vibra mucho y el torque está altísimo", "por_que", "OSF"),
    ("¿qué hago con la falla de potencia baja?", "que_hago", "PWF_low"),
    ("falla pronto?", "cuanto", "ninguna"),
    ("¿hay peligro si trabajo con la herramienta gastada?", "seguir", "TWF"),
    ("¿cuáles máquinas están sanas?", "planta", "ninguna"),
    ("¿qué opinas del reggaetón?", "fuera", "ninguna"),
    ("qué hago, la fresadora se está sobrecalentando", "que_hago", "HDF"),
    ("¿cómo evito la sobretensión en piezas duras?", "prevenir", "OSF"),
    ("¿por qué se calienta tanto la fresadora 8?", "por_que", "HDF"),
    ("¿alcanzo a terminar antes de que falle?", "cuanto", "ninguna"),
]


def natural():
    return [(t, i, c) for t, i, c in NATURAL]
