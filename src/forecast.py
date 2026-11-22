"""Pronóstico de fallas: «¿esta máquina fallará en los próximos HORIZON pasos?».

A diferencia del árbol (que clasifica la lectura actual), este modelo mira la TENDENCIA reciente de cada máquina
(las últimas WINDOW lecturas) y estima la probabilidad de que falle pronto. Aprende de series de tiempo generadas
por la planta simulada; nunca recibe las reglas físicas de falla.

Honestidad: los datos de entrenamiento salen del mismo simulador que se usa para la demostración (otras semillas).
Es un resultado en un mundo sintético, no una validación con máquinas reales.
"""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np

HORIZON = 12   # pasos hacia el futuro que se pronostican
WINDOW = 8     # lecturas recientes que mira el modelo
SERIES = ("power", "dt", "wear", "strain", "rpm", "torque")
MEAN_OF = ("power", "dt", "strain")
TYPES = ("L", "M", "H")
FEATURE_NAMES = ([f"{s}_now" for s in SERIES] + [f"{s}_mean" for s in MEAN_OF] + [f"{s}_slope" for s in SERIES]
                 + [f"type_{t}" for t in TYPES])
GROUPS = {  # para explicar: qué factor empuja el riesgo
    "Potencia": ["power_now", "power_mean", "power_slope"],
    "Temperatura (refrigeración)": ["dt_now", "dt_mean", "dt_slope"],
    "Desgaste de la herramienta": ["wear_now", "wear_slope"],
    "Desgaste × torque": ["strain_now", "strain_mean", "strain_slope"],
    "Velocidad y torque": ["rpm_now", "rpm_slope", "torque_now", "torque_slope"],
}
VERSION_PACKAGES = ("numpy", "pandas", "scikit-learn")
_I = {n: i for i, n in enumerate(FEATURE_NAMES)}


def window_features(series, kind):
    """Variables de una máquina a partir de sus últimas lecturas.

    series: dict con listas/arreglos 'power','dt','wear','rpm','torque' (la más reciente al final).
    """
    n = min(WINDOW, len(series["power"]))
    v = {k: np.asarray(series[k][-n:], dtype=float) for k in ("power", "dt", "wear", "rpm", "torque")}
    v["strain"] = v["wear"] * v["torque"]
    x = np.zeros(len(FEATURE_NAMES))
    i = np.arange(n) - (n - 1) / 2
    den = float((i ** 2).sum())
    for s in SERIES:
        x[_I[f"{s}_now"]] = v[s][-1]
        x[_I[f"{s}_slope"]] = float((i * v[s]).sum() / den) if den > 0 else 0.0
    for s in MEAN_OF:
        x[_I[f"{s}_mean"]] = v[s].mean()
    x[_I[f"type_{kind}"]] = 1.0
    return x


# ---------------------------------------------------------------------------------------------- datos
def simulate_runs(seeds, ticks):
    """Ejecuta la planta sin modelos y devuelve episodios: [{'series':{...},'fail':bool,'kind':str}].

    Un episodio es la vida de una máquina entre reinicios. Si termina en falla, 'fail' es True y la última
    lectura es la de la falla; si la simulación termina antes, el episodio está censurado (fail=False, 'censored').
    """
    from src.plant import DOWN_TICKS, Plant, power_w

    class Headless(Plant):
        def _infer(self):  # sin árbol ni autoencoder: solo la dinámica de la planta
            pass

        def _export(self, sel):  # no hace falta construir la respuesta de la API
            return None

    episodes = []
    for seed in seeds:
        plant = Headless(SimpleNamespace(ae=None), seed)
        open_eps, last = {}, {}
        for _ in range(ticks):
            plant.tick(0)
            for m in plant.machines:
                just_failed = m["status"] == "down" and m["fail_now"] and m["down_left"] == DOWN_TICKS
                if m["status"] != "run" and not just_failed:
                    continue
                if last.get(m["id"]) is not m:
                    last[m["id"]] = m
                    open_eps[m["id"]] = {"series": {k: [] for k in ("power", "dt", "wear", "rpm", "torque")}, "fail": False,
                                         "kind": m["type"], "seed": seed}
                ep, x = open_eps[m["id"]], m["reading"]
                ep["series"]["power"].append(power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"]))
                ep["series"]["dt"].append(x["Process temperature [K]"] - x["Air temperature [K]"])
                ep["series"]["wear"].append(x["Tool wear [min]"])
                ep["series"]["rpm"].append(x["Rotational speed [rpm]"]); ep["series"]["torque"].append(x["Torque [Nm]"])
                if m["fail_now"]:
                    ep["fail"] = True; ep["cause"] = m["cause_now"]
                    episodes.append(open_eps.pop(m["id"])); last.pop(m["id"])
        for ep in open_eps.values():
            ep["censored"] = True
            episodes.append(ep)
    return episodes


def build_rows(episodes):
    """Filas (X, y, meta) listas para entrenar. y=1 si la máquina falla en los próximos HORIZON pasos."""
    X, y, meta = [], [], []
    for e_id, ep in enumerate(episodes):
        n = len(ep["series"]["power"])
        last = n - 1 if ep["fail"] else n          # la lectura de la falla misma no se usa (ya falló)
        for idx in range(last):
            if not ep["fail"] and idx > n - 1 - HORIZON:
                break                                # sin desenlace conocido: se descarta
            win = {k: ep["series"][k][max(0, idx + 1 - WINDOW):idx + 1] for k in ep["series"]}
            X.append(window_features(win, ep["kind"]))
            y.append(int(ep["fail"] and n - 1 - idx <= HORIZON))
            meta.append((e_id, idx, n - 1 - idx if ep["fail"] else -1))
    return np.array(X), np.array(y), np.array(meta)


# ---------------------------------------------------------------------------------------------- uso
def proba(bundle, X):
    return bundle["model"].predict_proba(np.atleast_2d(X))[:, 1]


def explain(bundle, x):
    """¿Cuánto bajaría el riesgo si cada factor tuviera valores normales? (ablación contra una máquina sana)."""
    base = float(proba(bundle, x)[0])
    ref, out = bundle["reference"], []
    rows = []
    for g, names in GROUPS.items():
        z = np.array(x, dtype=float).copy()
        for n in names:
            z[_I[n]] = ref[n]
        rows.append(z)
    probs = proba(bundle, np.array(rows))
    for (g, _), p in zip(GROUPS.items(), probs):
        out.append({"group": g, "drop": max(0.0, base - float(p))})
    return sorted(out, key=lambda r: -r["drop"])


def load_forecast(root):
    """Pronosticador verificado, o None si el experimento no lo incluye."""
    root = Path(root)
    info_path, model_path = root / "reports/pronostico_selection.json", root / "models/pronostico.joblib"
    if not info_path.is_file() or not model_path.is_file():
        return None
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != info["model_sha256"]:
        raise ValueError("El pronosticador no coincide con el registrado en reports/pronostico_selection.json.")
    for package, expected in info["versions"].items():
        if version(package) != expected:
            raise ValueError(f"Versión diferente de {package}; utilizar requirements.txt.")
    bundle = joblib.load(model_path)
    ev = root / "reports/pronostico_evaluation.json"
    bundle["info"] = info
    bundle["info"]["evaluation"] = json.loads(ev.read_text(encoding="utf-8")) if ev.is_file() else None
    return bundle
