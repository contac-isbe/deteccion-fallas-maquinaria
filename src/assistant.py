"""Asistente de la planta: responde «¿qué hago con esta falla?» a partir de una pregunta escrita.

Cómo funciona (de verdad):
1. COMPRENDE la pregunta con TF-IDF de n-gramas de caracteres (aprendizaje automático clásico de lenguaje) contra
   ejemplos de cada intención y contra la guía de mantenimiento. No es un modelo de lenguaje.
2. CONSULTA AL PRONOSTICADOR ENTRENADO: prueba acciones del operador (bajar potencia, cambiar herramienta…) y mide
   el riesgo que resultaría de cada una (Plant.advise). Las cifras vienen del modelo, no de una plantilla.
3. REDACTA la respuesta. Por defecto con plantillas (funciona sin internet). Si existe la variable de entorno
   ANTHROPIC_API_KEY, Claude solo reescribe el texto con los datos ya calculados; las cifras no las inventa él.

Las recomendaciones de mantenimiento son una guía general; con una fresadora real, manda el manual del fabricante.
"""
import json
import os
import re
import unicodedata
import urllib.request
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

MAX_QUESTION = 300

# ----------------------------------------------------------------------------------- guía de mantenimiento
PLAYBOOK = {
    "PWF_high": {
        "title": "Sobrecarga de potencia",
        "meaning": "El husillo trabaja por encima de unos 9 000 W (torque × velocidad). El motor se sobrecalienta y la máquina puede detenerse.",
        "check": ["Reduce el avance o la profundidad de corte para bajar el torque.", "Revisa que la fresa no esté embotada: una herramienta sin filo aumenta la carga.",
                  "Verifica la sujeción de la pieza y la vibración (chatter).", "Comprueba la temperatura del motor del husillo y su ventilación."],
        "prevent": "Ajusta los parámetros de corte al material y vigila la carga del husillo en lugar de esperar la parada.",
        "keywords": "potencia alta sobrecarga motor husillo sobrecalienta demasiada carga torque exceso corte avance profundidad",
    },
    "PWF_low": {
        "title": "Potencia demasiado baja",
        "meaning": "La potencia cayó por debajo de unos 3 500 W: la fresadora trabaja muy por debajo de lo normal y casi no está cortando.",
        "check": ["Detén el ciclo y revisa si la herramienta se rompió o se soltó del portaherramientas.", "Revisa la correa o el acople del husillo: puede estar patinando.",
                  "Verifica que el programa de corte esté entrando en el material (avance y altura correctos)."],
        "prevent": "Inspecciona correas y portaherramientas con la frecuencia que indique el fabricante.",
        "keywords": "potencia baja cae poca debajo herramienta rota suelta correa patina no corta sin carga",
    },
    "HDF": {
        "title": "Disipación de calor insuficiente",
        "meaning": "La diferencia entre la temperatura del proceso y la del aire es pequeña mientras el husillo gira lento (menos de unos 1 380 rpm): el calor no se evacúa bien.",
        "check": ["Sube la velocidad del husillo por encima de ~1 380 rpm si el material y la herramienta lo permiten.", "Revisa el nivel de refrigerante, el flujo y que las boquillas no estén tapadas.",
                  "Limpia filtros y rejillas de ventilación del motor y del tablero eléctrico.", "Verifica la temperatura ambiente del taller."],
        "prevent": "Programa limpieza de filtros y revisión del circuito de refrigerante; evita trabajar de forma prolongada a bajas rpm.",
        "keywords": "calor temperatura refrigeracion refrigerante enfriamiento disipacion caliente sobrecalentamiento lento rpm baja ventilacion",
    },
    "OSF": {
        "title": "Sobretensión mecánica",
        "meaning": "El producto del desgaste de la herramienta por el torque superó el límite de su tipo de calidad (11 000 en L, 12 000 en M, 13 000 en H): la herramienta se está forzando.",
        "check": ["Reduce el torque: baja la demanda de potencia o aumenta la velocidad.", "Cambia la herramienta si lleva muchas horas: desgastada, el mismo corte exige más torque.",
                  "Evita cortes pesados con herramienta usada.", "Revisa la sujeción y el estado del portaherramientas."],
        "prevent": "Cambia herramientas por horas de uso y reduce el torque en cortes difíciles.",
        "keywords": "sobretension tension torque fuerza esfuerzo desgaste carga mecanica rotura forzada",
    },
    "TWF": {
        "title": "Herramienta al final de su vida",
        "meaning": "La herramienta acumuló entre 200 y 240 minutos de uso, la zona donde suele fallar (desgaste, filo roto). En los datos esa falla es aleatoria: no se anuncia con ninguna otra medición.",
        "check": ["Cambia la herramienta en cuanto puedas, mejor en un paro programado.", "Inspecciona el filo: desgaste de flanco, filos astillados, acabado superficial peor.",
                  "Registra las horas de uso de cada herramienta."],
        "prevent": "Cambia por tiempo de uso antes de entrar a la zona de 200 minutos.",
        "keywords": "herramienta desgaste fresa filo cambiar cambio vida util gastada usada minutos",
    },
    "OK": {
        "title": "Sin señales de falla",
        "meaning": "El pronosticador no ve una falla cercana en esta fresadora.",
        "check": ["Sigue vigilando: el riesgo se actualiza en cada paso."],
        "prevent": "Mantén el cambio de herramientas y la limpieza del refrigerante al día.",
        "keywords": "normal sano bien funciona ok estable",
    },
}
INTENTS = {
    "que_hago": ["que hago", "que debo hacer", "como lo soluciono", "como lo arreglo", "que accion tomo", "que recomiendas", "ayudame con esta falla",
                 "como evito la falla", "que puedo hacer", "que hago para que no falle", "soluciona esto", "que me aconsejas", "que hago con esta maquina", "que hago con esta fresadora", "que hago con la fresadora",
                 "que hago con ella", "que accion tomo con esta fresadora", "como la reparo", "como corrijo el problema", "que hago con el error", "que hago ante esta falla"],
    "por_que": ["por que sube el riesgo", "por que va a fallar", "cual es la causa", "que esta pasando", "por que alerta", "que causa el problema", "por que fallo",
                "explicame la alerta", "de donde viene el riesgo", "que significa esta falla"],
    "cuanto": ["cuanto tiempo tengo", "cuando va a fallar", "cuanto falta para la falla", "es urgente", "que tan pronto falla", "cuantos pasos me quedan", "tengo tiempo"],
    "seguir": ["puedo seguir produciendo", "es seguro seguir trabajando", "debo detener la maquina", "puedo seguir usando", "la paro o sigo", "es peligroso seguir"],
    "prevenir": ["como evito que se repita", "como prevengo esta falla", "como lo evito a futuro", "mantenimiento preventivo", "que hago para que no vuelva a pasar"],
    "planta": ["como esta la planta", "cual esta peor", "cual tiene mas riesgo", "resumen de la planta", "cuales estan en alerta", "a cual atiendo primero", "que atiendo primero", "como esta el taller", "cuales estan detenidas"],
}
SUGGESTIONS = ["¿Qué hago con esta fresadora?", "¿Por qué sube el riesgo?", "¿Cuánto tiempo tengo?", "¿Puedo seguir produciendo?", "¿Qué fresadora atiendo primero?"]


def _norm(text):
    text = unicodedata.normalize("NFKD", str(text).lower())
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


@lru_cache(maxsize=1)
def _index():
    """Vectorizador TF-IDF sobre ejemplos de intención y guía de mantenimiento."""
    docs, labels = [], []
    for intent, examples in INTENTS.items():
        for e in examples:
            docs.append(_norm(e)); labels.append(("intent", intent))
    for key, entry in PLAYBOOK.items():
        if key == "OK":
            continue
        docs.append(_norm(entry["keywords"] + " " + entry["title"])); labels.append(("cause", key))
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(docs)
    return vec, vec.transform(docs), labels


CAUSE_STEMS = [("HDF", r"calor|calient|calent|temperatur|refriger|enfri|ventila"), ("OSF", r"sobretens|torque|esfuerzo"),
               ("TWF", r"herramienta|fresa\b|filo|desgast"), ("PWF_low", r"potencia (baja|poca|insuficiente)|poca potencia|baja potencia"),
               ("PWF_high", r"sobrecarga|potencia|sobrepotencia")]


def _cause_by_words(question):
    """Respaldo por palabras clave cuando la similitud TF-IDF no alcanza para identificar la falla mencionada."""
    q = _norm(question)
    for key, pattern in CAUSE_STEMS:
        if re.search(pattern, q):
            return key
    return None


@lru_cache(maxsize=1)
def language_model():
    """Modelo de lenguaje propio (entrenado con scripts/train_assistant.py), verificado con hash y versiones. None si no está."""
    import hashlib
    from importlib.metadata import version
    from pathlib import Path
    import joblib
    root = Path(__file__).resolve().parents[1]
    sel, path = root / "reports/asistente_selection.json", root / "models/asistente_lenguaje.joblib"
    if not sel.is_file() or not path.is_file():
        return None
    info = json.loads(sel.read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != info["model_sha256"]:
        raise ValueError("El modelo del asistente no coincide con el registrado en reports/asistente_selection.json.")
    for package, expected in info["versions"].items():
        if version(package) != expected:
            raise ValueError(f"Versión diferente de {package}; utilizar requirements.txt.")
    from src import assistant_features  # noqa: F401  (clase necesaria para cargar el modelo)
    return joblib.load(path)


def understand(question):
    """(intención, falla mencionada, confianza). Usa el Transformer ajustado (ONNX); si no está, el TF-IDF entrenado; y si
    tampoco, la versión por similitud."""
    try:
        from src import assistant_transformer
        result = assistant_transformer.understand(question)
        if result is not None:
            return result
    except Exception:  # noqa: BLE001  (cualquier fallo del Transformer -> respaldo TF-IDF)
        pass
    bundle = language_model()
    if bundle is None:
        return understand_retrieval(question)
    text = [question]
    pi, pc = bundle["intent"].predict_proba(text)[0], bundle["cause"].predict_proba(text)[0]
    intent, cause = bundle["intent"].classes_[pi.argmax()], bundle["cause"].classes_[pc.argmax()]
    if pi.max() < bundle["threshold"] or intent == "fuera":
        return None, None, float(pi.max())
    return str(intent), (None if cause == "ninguna" else str(cause)), float(pi.max())


def understand_retrieval(question):
    """Versión anterior (sin entrenamiento propio): similitud TF-IDF con ejemplos. Se conserva como respaldo y como línea base."""
    vec, matrix, labels = _index()
    sims = (matrix @ vec.transform([_norm(question)]).T).toarray().ravel()
    best = {"intent": (None, 0.0), "cause": (None, 0.0)}
    for (kind, name), s in zip(labels, sims):
        if s > best[kind][1]:
            best[kind] = (name, float(s))
    intent, i_s = best["intent"]; cause, c_s = best["cause"]
    cause = cause if c_s >= .3 else _cause_by_words(question)
    return (intent if i_s >= .3 else None), cause, max(i_s, c_s)


def _machine_from(question, default):
    m = re.search(r"(?:fresadora|maquina|m)[\s\-]*0*(\d{1,2})\b", _norm(question))
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(1)) - 1, True
    return default, False


def _cause_key(info):
    """Causa más probable de la máquina: la dice la explicación del modelo (qué factor empuja el riesgo)."""
    if info["status"] == "down" and info["cause"]:
        key = info["cause"]
        if key == "PWF":
            return "PWF_low" if info["reading"] and info["reading"]["power"] < 6000 else "PWF_high"
        return key
    if info["p_idle"] is not None and max(info["p_idle"], info["p_now"]) < .15:
        return "OK"
    top = info["why"][0]["group"] if info["why"] and info["why"][0]["drop"] > 0.01 else None
    r = info["reading"] or {}
    if top == "Potencia":
        return "PWF_low" if r.get("power", 6000) < 6000 else "PWF_high"
    if top == "Temperatura (refrigeración)":
        return "HDF"
    if top == "Desgaste × torque":
        return "OSF"
    if top == "Desgaste de la herramienta":
        return "TWF"
    if top == "Velocidad y torque":
        return "HDF" if r.get("rpm", 1500) < 1500 else "OSF"
    return "OK"


def pct(p):
    return f"{round(100 * p)} %"


def _apply_payload(idx, action):
    return {"id": idx, **{k: v for k, v in action.items()}}


def build(plant, idx, question, intent, cause_hint):
    info = plant.advise(idx)
    key = cause_hint if cause_hint else _cause_key(info)
    guide = PLAYBOOK[key]
    out = {"machine": idx, "name": info["name"], "cause": key, "title": guide["title"], "meaning": guide["meaning"],
           "check": guide["check"], "prevent": guide["prevent"], "p_now": info["p_now"], "p_idle": info["p_idle"],
           "status": info["status"], "actions": [], "notes": []}
    down = info["status"] == "down"
    if down:
        out["notes"].append(f"{info['name']} está detenida ({info['cause_text'] or 'falla'}). Se reinicia sola en {info['down_left']} pasos, o puedes reiniciarla ahora.")
        out["actions"] = [{"label": "Reiniciar la fresadora (herramienta nueva y parámetros restablecidos)", "p": None, "delta": None, "safe": True, "apply": {"action": "restart"}}]
        return out
    if not info["forecast"]:
        out["notes"].append("El pronosticador no está disponible; las recomendaciones salen solo de la guía de mantenimiento.")
        return out
    if (info["p_idle"] or 0) < .1:
        out["notes"].append("Sin riesgo relevante ahora: no hace falta intervenir.")
        return out
    good = [a for a in info["actions"] if a["safe"]]
    out["actions"] = [a for a in good if a["p"] <= max(.05, info["p_idle"] - .05)][:3]
    for a in out["actions"]:
        a["apply"] = _apply_payload(idx, a["apply"])
    if key == "OK" and not out["actions"]:
        out["actions"] = []
    elif not out["actions"]:
        out["notes"].append("Ninguna acción probada baja el riesgo de forma clara; conviene detener la fresadora y revisarla.")
    return out


def compose(question, intent, data):
    """Texto de la respuesta (plantillas). Todas las cifras salen de `data`, calculado con el pronosticador."""
    n, p_idle, p_now = data["name"], data["p_idle"], data["p_now"]
    acts = data["actions"]
    risk = f"El riesgo actual de falla en los próximos 12 pasos es {pct(p_now)}" + (f" y, si no cambias nada, se proyecta a {pct(p_idle)}." if p_idle is not None and not data["status"] == "down" else ".")
    best = (f" La mejor acción probada es «{acts[0]['label'].lower()}»: baja el riesgo a {pct(acts[0]['p'])}." if acts and acts[0]["p"] is not None else "")
    if data.get("focus_cause") and (p_idle or 0) < .1 and data["status"] != "down":
        return (f"{n} no tiene riesgo relevante ahora ({pct(p_now)}). En general, ante «{data['title'].lower()}»: {data['meaning']} "
                f"Primero: {data['check'][0]} Para prevenir: {data['prevent']}")
    if intent == "por_que":
        return f"{n}: {data['title'].lower()}. {data['meaning']} {risk}"
    if intent == "cuanto":
        if data["status"] == "down":
            return f"{n} ya falló. {data['notes'][0] if data['notes'] else ''}"
        urgency = "Es urgente: actúa ya." if (p_idle or 0) >= .6 else "Tienes margen, pero conviene actuar pronto." if (p_idle or 0) >= .25 else "No hay urgencia ahora."
        return f"{risk} El pronóstico mira los próximos 12 pasos. {urgency}{best}"
    if intent == "seguir":
        if data["status"] == "down":
            return f"No: {n} está detenida. Reiníciala solo después de revisar la causa ({data['title'].lower()})."
        if (p_idle or 0) >= .5:
            return f"Yo no seguiría igual: {risk}{best}"
        if (p_idle or 0) >= .15:
            return f"Puedes seguir con vigilancia: {risk}{best}"
        return f"Sí, no hay señales de falla cercana en {n}. {risk}"
    if intent == "prevenir":
        return f"Para evitar «{data['title'].lower()}» a futuro: {data['prevent']}"
    return f"{n} — {data['title']}. {data['meaning']} {risk}{best}"


def plant_summary(plant):
    snap = plant.snapshot(0)
    ms = sorted([m for m in snap["machines"] if m["status"] == "run"], key=lambda m: -m["fc"])
    down = [m for m in snap["machines"] if m["status"] == "down"]
    rows = [{"id": m["id"], "name": m["name"], "p": m["fc"]} for m in ms[:3]]
    text = "Atiende primero: " + (", ".join(f"{r['name']} ({pct(r['p'])})" for r in rows if r["p"] >= .15) or "ninguna fresadora tiene riesgo relevante") + "."
    if down:
        text += " Detenidas: " + ", ".join(m["name"] for m in down) + "."
    return text, rows


def llm_text(question, data, fallback):
    """Opcional: Claude redacta con los datos ya calculados. Devuelve None si no hay clave o falla."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    facts = {"fresadora": data["name"], "causa_probable": data["title"], "significado": data["meaning"], "riesgo_actual": data["p_now"],
             "riesgo_si_no_haces_nada": data["p_idle"], "acciones_probadas": [{"accion": a["label"], "riesgo_resultante": a["p"]} for a in data["actions"]],
             "que_revisar": data["check"], "notas": data["notes"]}
    body = {"model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 400,
            "system": ("Eres el asistente de mantenimiento de un taller de fresado. Responde en español, en máximo 110 palabras, directo y claro. "
                       "Usa SOLO los datos del JSON; no inventes cifras ni acciones. Las cifras de riesgo vienen de un modelo entrenado."),
            "messages": [{"role": "user", "content": f"Pregunta del operador: {question}\nDatos: {json.dumps(facts, ensure_ascii=False)}"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode())
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text").strip()
        return text or None
    except Exception:
        return None


def reply(plant, data):
    """Punto de entrada de la API. data: {question, sel}."""
    q = data.get("question")
    if not isinstance(q, str) or not q.strip():
        raise ValueError("Escribe una pregunta.")
    if len(q) > MAX_QUESTION:
        raise ValueError(f"La pregunta debe tener como máximo {MAX_QUESTION} caracteres.")
    sel = data.get("sel", 0)
    sel = sel if isinstance(sel, int) and 0 <= sel < 12 else 0
    intent, cause, sim = understand(q)
    idx, named = _machine_from(q, sel)
    if intent == "planta":
        text, rows = plant_summary(plant)
        return {"mode": "propio", "understood": "planta", "text": text, "ranking": rows, "suggest": SUGGESTIONS}
    if intent is None and cause is None:
        return {"mode": "propio", "understood": None, "suggest": SUGGESTIONS,
                "text": "No entendí bien la pregunta. Puedo ayudarte a saber qué hacer con una fresadora que tiene riesgo de falla, por qué sube, cuánto tiempo hay y si conviene seguir produciendo. Prueba con una de estas:"}
    result = build(plant, idx, q, intent, cause)
    intent = intent or "que_hago"
    result["focus_cause"] = cause is not None
    fallback = compose(q, intent, result)
    llm = llm_text(q, result, fallback)
    result.update({"mode": "claude" if llm else "propio", "understood": intent, "text": llm or fallback, "named": named, "suggest": SUGGESTIONS})
    return result
