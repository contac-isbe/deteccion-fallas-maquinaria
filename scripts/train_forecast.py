"""Entrena y evalúa el pronosticador de fallas con series de la planta simulada.

Protocolo:
- Entrenamiento: semillas 100-219. Selección de hiperparámetros y umbral: semillas 300-339 (validación).
- Prueba: semillas 500-539, usadas UNA vez al final. La demostración usa otras semillas (por defecto 12).
- Ablación: el mismo modelo sin tendencias, para medir si mirar la evolución aporta.
"""
import hashlib
import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import forecast as F  # noqa: E402

TRAIN, VAL, TEST = list(range(100, 220)), list(range(300, 340)), list(range(500, 540))
TICKS = 500
GRID = [dict(max_depth=d, max_iter=i) for d in (3, 5) for i in (80, 200)]


def fit(params, X, y):
    return HistGradientBoostingClassifier(learning_rate=0.1, random_state=0, **params).fit(X, y)


def best_threshold(p, y):
    cands = np.linspace(0.05, 0.95, 91)
    f1 = [precision_recall_fscore_support(y, p >= c, average="binary", zero_division=0)[2] for c in cands]
    return float(cands[int(np.argmax(f1))])


def event_metrics(episodes, alerts_by_episode):
    """Por evento: ¿hubo alerta en los HORIZON pasos anteriores a la falla (con adelanto ≥ 1)? ¿cuántas falsas alarmas?"""
    fails = warned = 0
    leads, alert_runs, false_runs, healthy_ticks = [], 0, 0, 0
    causes = {}
    for ep_id, ep in enumerate(episodes):
        a = alerts_by_episode[ep_id]       # alerta por lectura utilizable (excluye la lectura de la falla)
        n = len(ep["series"]["power"])
        if ep["fail"]:
            fails += 1
            window = [i for i in range(len(a)) if a[i] and n - 1 - i <= F.HORIZON]
            ok = bool(window)
            warned += ok
            c = causes.setdefault(ep["cause"], [0, 0]); c[0] += 1; c[1] += ok
            if ok:
                leads.append(n - 1 - min(window))
        healthy_ticks += sum(1 for i in range(len(a)) if not (ep["fail"] and n - 1 - i <= F.HORIZON))
        i = 0
        while i < len(a):                   # corridas continuas de alerta
            if a[i]:
                j = i
                while j + 1 < len(a) and a[j + 1]:
                    j += 1
                alert_runs += 1
                if not (ep["fail"] and n - 1 - j <= F.HORIZON):
                    false_runs += 1
                i = j + 1
            else:
                i += 1
    return {"failures": fails, "warned": warned, "recall_events": warned / max(1, fails),
            "mean_lead": float(np.mean(leads)) if leads else None, "median_lead": float(np.median(leads)) if leads else None,
            "alert_runs": alert_runs, "false_runs": false_runs, "false_runs_per_1000_ticks": 1000 * false_runs / max(1, healthy_ticks),
            "by_cause": {k: {"failures": v[0], "warned": v[1]} for k, v in sorted(causes.items())}}


def per_episode(meta, flags, episodes):
    out = {i: [] for i in range(len(episodes))}
    for (e, idx, _), f in zip(meta, flags):
        out[int(e)].append(bool(f))
    return out


def main():
    print("Simulando planta…")
    tr, va, te = (F.simulate_runs(s, TICKS) for s in (TRAIN, VAL, TEST))
    (Xtr, ytr, _), (Xva, yva, _), (Xte, yte, mte) = (F.build_rows(e) for e in (tr, va, te))
    print(f"filas: entrenamiento {len(ytr)} ({ytr.mean():.3f} positivas), validación {len(yva)}, prueba {len(yte)}")
    results = []
    for params in GRID:
        m = fit(params, Xtr, ytr)
        ap = average_precision_score(yva, m.predict_proba(Xva)[:, 1])
        results.append({**params, "val_average_precision": float(ap)}); print(results[-1])
    best = max(results, key=lambda r: (r["val_average_precision"], -r["max_depth"], -r["max_iter"]))
    params = {k: best[k] for k in ("max_depth", "max_iter")}
    model = fit(params, Xtr, ytr)
    threshold = best_threshold(model.predict_proba(Xva)[:, 1], yva)

    healthy = Xtr[ytr == 0]
    reference = {n: float(np.median(healthy[:, i])) for i, n in enumerate(F.FEATURE_NAMES) if not n.startswith("type_")}
    reference.update({n: 0.0 for n in F.FEATURE_NAMES if n.startswith("type_")})
    bundle = {"model": model, "threshold": threshold, "horizon": F.HORIZON, "window": F.WINDOW,
              "feature_names": F.FEATURE_NAMES, "reference": reference}

    # --- Prueba (una sola vez)
    p_te = model.predict_proba(Xte)[:, 1]
    pr, rc, f1, _ = precision_recall_fscore_support(yte, p_te >= threshold, average="binary", zero_division=0)
    forecast_events = event_metrics(te, per_episode(mte, p_te >= threshold, te))

    # Ablación: el mismo modelo sin tendencias (solo el valor actual y el tipo). Sirve para ver si mirar la evolución aporta.
    keep = [i for i, n in enumerate(F.FEATURE_NAMES) if n.endswith("_now") or n.startswith("type_")]
    flat = fit(params, Xtr[:, keep], ytr)
    p_flat_va = flat.predict_proba(Xva[:, keep])[:, 1]
    thr_flat = best_threshold(p_flat_va, yva)
    p_flat = flat.predict_proba(Xte[:, keep])[:, 1]
    fpr, frc, ff1, _ = precision_recall_fscore_support(yte, p_flat >= thr_flat, average="binary", zero_division=0)
    flat_events = event_metrics(te, per_episode(mte, p_flat >= thr_flat, te))

    evaluation = {
        "protocol": "Prueba con semillas 500-539 (nunca usadas para entrenar ni elegir); evaluada una sola vez.",
        "horizon": F.HORIZON, "window": F.WINDOW,
        "rows": {"test": int(len(yte)), "positives": int(yte.sum())},
        "row_level": {"precision": float(pr), "recall": float(rc), "f1": float(f1),
                      "average_precision": float(average_precision_score(yte, p_te)), "base_rate": float(yte.mean())},
        "forecast_events": forecast_events,
        "without_trend": {"description": "Mismo modelo pero solo con el valor actual (sin tendencias); umbral elegido en validación.",
                          "row_level": {"precision": float(fpr), "recall": float(frc), "f1": float(ff1),
                                        "average_precision": float(average_precision_score(yte, p_flat))},
                          "events": flat_events},
        "note": "El árbol v2 clasifica solo la lectura actual: por construcción no avisa antes de que se cumpla la condición de falla (adelanto 0).",
    }
    (ROOT / "models").mkdir(exist_ok=True)
    model_path = ROOT / "models/pronostico.joblib"
    joblib.dump(bundle, model_path)
    sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    selection = {"model_artifact": "models/pronostico.joblib", "model_sha256": sha, "grid": results, "chosen": params,
                 "threshold": threshold, "threshold_rule": "umbral que maximiza F1 en validación",
                 "seeds": {"train": [TRAIN[0], TRAIN[-1]], "validation": [VAL[0], VAL[-1]], "test": [TEST[0], TEST[-1]]},
                 "ticks_per_run": TICKS, "versions": {p: version(p) for p in F.VERSION_PACKAGES}}
    (ROOT / "reports/pronostico_selection.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "reports/pronostico_evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    art = ROOT / "deployment/artifacts"
    if art.is_dir():
        shutil.copyfile(model_path, art / "pronostico.joblib")
        mp = art / "manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        manifest["files"]["models/pronostico.joblib"] = {"sha256": sha, "bytes": model_path.stat().st_size}
        mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evaluation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
