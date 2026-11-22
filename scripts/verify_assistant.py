"""Comprobaciones del asistente: comprensión de preguntas, acciones probadas con el pronosticador y modo Claude (simulado)."""
import io
import json
import os
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.assistant import reply, understand  # noqa: E402
from src.runtime import load_runtime  # noqa: E402
from src.simulation import Simulator  # noqa: E402


def check(ok, text):
    if not ok:
        raise SystemExit(f"FALLÓ: {text}")
    print("ok  ", text)


def main():
    os.environ.pop("ANTHROPIC_API_KEY", None)
    model, test, hashes, ae, ref = load_runtime(ROOT)
    plant = Simulator(model, test, hashes, ae, ref).plant
    for _ in range(40):
        plant.tick(0)
    for q, intent in [("¿Qué hago con esta fresadora?", "que_hago"), ("¿Por qué sube el riesgo?", "por_que"), ("¿Cuánto tiempo tengo?", "cuanto"),
                      ("¿Puedo seguir produciendo?", "seguir"), ("¿Qué fresadora atiendo primero?", "planta")]:
        check(understand(q)[0] == intent, f"entiende «{q}» como {intent}")
    check(understand("quiero pizza")[:2] == (None, None), "rechaza una pregunta fuera de tema")
    from src.assistant import language_model
    check(language_model() is not None, "el modelo de lenguaje entrenado está cargado y verificado (hash y versiones)")
    ev = json.loads((ROOT / "reports/asistente_evaluation.json").read_text(encoding="utf-8"))
    nat, base = ev["natural_a_mano"]["modelo_entrenado"], ev["natural_a_mano"]["linea_base_similitud"]
    check(nat["intent_accuracy"] >= 0.7 and nat["cause_accuracy"] >= 0.85, f"precisión en preguntas naturales: intención {nat['intent_accuracy']:.0%}, falla {nat['cause_accuracy']:.0%}")
    check(nat["intent_accuracy"] > base["intent_accuracy"], "entrenar mejora la comprensión frente a la versión por similitud")
    check(understand("cómo prevengo el calor excesivo")[1] == "HDF", "reconoce la falla por calor")
    risky = max((m for m in plant.snapshot(0)["machines"] if m["status"] == "run"), key=lambda m: m["fc"])["id"]
    r = reply(plant, {"question": "¿Qué hago con esta fresadora?", "sel": risky})
    check(r["mode"] == "propio" and r["machine"] == risky, "responde sobre la fresadora seleccionada sin clave")
    check(r["p_idle"] is not None and r["actions"] and all(0 <= a["p"] <= 1 for a in r["actions"]), "las acciones traen riesgos del pronosticador")
    check(r["actions"][0]["p"] < r["p_idle"], "la mejor acción baja el riesgo proyectado")
    check(reply(plant, {"question": "por qué falla la fresadora 12", "sel": 0})["machine"] == 11, "entiende «fresadora 12»")
    for bad in ("", "x" * 400, 5):
        try:
            reply(plant, {"question": bad}); check(False, "rechaza preguntas inválidas")
        except ValueError:
            pass
    check(True, "rechaza preguntas vacías, demasiado largas o no textuales")
    # Modo Claude con la red simulada: solo redacta; las cifras siguen siendo las del modelo
    fake = io.BytesIO(json.dumps({"content": [{"type": "text", "text": "Texto redactado por Claude."}]}).encode())
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "clave-de-prueba"}), mock.patch("urllib.request.urlopen", return_value=fake):
        r2 = reply(plant, {"question": "¿Qué hago con esta fresadora?", "sel": risky})
    print("   modo:", r2["mode"], "| texto:", r2["text"][:40])
    check(r2["mode"] == "claude" and r2["text"] == "Texto redactado por Claude.", "con clave, Claude redacta el texto")
    check(r2["actions"] == r["actions"], "las acciones y cifras siguen siendo las del modelo")
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "clave-de-prueba"}), mock.patch("urllib.request.urlopen", side_effect=OSError("sin red")):
        check(reply(plant, {"question": "¿Qué hago con esta fresadora?", "sel": risky})["mode"] == "propio", "si Claude falla, vuelve al asistente propio")
    print("Asistente: comprobaciones correctas.")


if __name__ == "__main__":
    main()
