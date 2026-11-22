"""Entrena y evalúa el modelo de lenguaje propio del asistente (intención + falla mencionada).

Protocolo: entrenar con la partición 'train'; elegir configuración y umbral de rechazo con 'val'; evaluar UNA vez con 'test'
(frases y marcos de pregunta nunca vistos) y con el conjunto NATURAL escrito a mano. Se compara con la versión anterior
por similitud (sin entrenamiento) para saber si entrenar realmente mejora.
"""
import hashlib
import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import assistant as A  # noqa: E402
from src import assistant_data as D  # noqa: E402
from src.assistant_features import KeywordFlags  # noqa: E402

SEED = 0


def features(kind):
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, strip_accents="unicode", lowercase=True)
    if kind == "char":
        return char
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode", lowercase=True)
    if kind == "char+word":
        return FeatureUnion([("char", char), ("word", word)])
    return FeatureUnion([("char", char), ("word", word), ("flags", KeywordFlags())])


def make(kind, C):
    return Pipeline([("tfidf", features(kind)), ("clf", LogisticRegression(C=C, max_iter=3000, class_weight="balanced"))])


def columns(rows):
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def predict(bundle, texts):
    pi, pc = bundle["intent"].predict_proba(texts), bundle["cause"].predict_proba(texts)
    ii, cc = bundle["intent"].classes_, bundle["cause"].classes_
    intent = ii[pi.argmax(1)].astype(object)
    intent[pi.max(1) < bundle["threshold"]] = "fuera"
    return intent, cc[pc.argmax(1)], pi.max(1), pc.max(1)


def metrics(y_i, y_c, p_i, p_c):
    return {"intent_accuracy": float(accuracy_score(y_i, p_i)), "intent_macro_f1": float(f1_score(y_i, p_i, average="macro")),
            "cause_accuracy": float(accuracy_score(y_c, p_c)), "cause_macro_f1": float(f1_score(y_c, p_c, average="macro"))}


def baseline(rows):
    """Versión anterior (similitud con ejemplos, sin entrenamiento propio) con la misma tarea."""
    pi, pc = [], []
    for text, _, _ in rows:
        intent, cause, _ = A.understand_retrieval(text)
        pi.append(intent or "fuera"); pc.append(cause or "ninguna")
    return pi, pc


def main():
    data = D.build(seed=SEED)
    nat = D.natural()
    sizes = {k: len(v) for k, v in data.items()}; sizes["natural"] = len(nat)
    print("Filas:", sizes)
    (Xtr, ytr_i, ytr_c), (Xva, yva_i, yva_c) = columns(data["train"]), columns(data["val"])
    grid, best = [], None
    for kind in ("char", "char+word", "char+word+palabras_clave"):
        for C in (1, 10, 100):
            mi, mc = make(kind, C).fit(Xtr, ytr_i), make(kind, C).fit(Xtr, ytr_c)
            fi, fc = f1_score(yva_i, mi.predict(Xva), average="macro"), f1_score(yva_c, mc.predict(Xva), average="macro")
            row = {"features": kind, "C": C, "val_intent_macro_f1": float(fi), "val_cause_macro_f1": float(fc), "score": float((fi + fc) / 2)}
            grid.append(row); print(row)
            if best is None or row["score"] > best[0]["score"] + 1e-9:
                best = (row, mi, mc)
    cfg, m_i, m_c = best
    bundle = {"intent": m_i, "cause": m_c, "threshold": 0.0}
    cands = []
    for t in (0.0, 0.3, 0.4, 0.5, 0.6):
        bundle["threshold"] = t
        pi, _, _, _ = predict(bundle, Xva)
        cands.append((float(f1_score(yva_i, pi, average="macro")), -t, t))
    bundle["threshold"] = max(cands)[2]
    print("Umbral de rechazo (validación):", bundle["threshold"], "| config:", cfg["features"], "C =", cfg["C"])

    out = {"nota": "Resultados de la SEGUNDA ejecución (ver reports/asistente_selection.json: limitación declarada). Primera ejecución, sin palabras clave ni frases ampliadas: "
                   "intención 77 % y falla 73 % en prueba; 65 % y 88 % en el conjunto natural.", "rows": sizes, "chosen": {"features": cfg["features"], "C": cfg["C"], "reject_threshold": bundle["threshold"]}, "grid": grid}
    for name, rows in (("test_plantillas_no_vistas", data["test"]), ("natural_a_mano", nat)):
        X, y_i, y_c = columns(rows)
        pi, pc, _, _ = predict(bundle, X)
        bi, bc = baseline(rows)
        out[name] = {"modelo_entrenado": metrics(y_i, y_c, pi, pc), "linea_base_similitud": metrics(y_i, y_c, bi, bc)}
        if name == "natural_a_mano":
            out[name]["errores"] = [{"texto": t, "esperado": [a, b], "predicho": [str(p), str(q)]} for (t, a, b), p, q in zip(rows, pi, pc) if (p, q) != (a, b)]
            print(classification_report(y_i, pi, zero_division=0))
    bundle["intents"], bundle["causes"] = list(m_i.classes_), list(m_c.classes_)
    path = ROOT / "models/asistente_lenguaje.joblib"
    joblib.dump(bundle, path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    selection = {"model_sha256": sha, "versions": {p: version(p) for p in ("numpy", "scikit-learn")}, "seed": SEED, "chosen": out["chosen"],
                 "protocol": ("Configuración y umbral elegidos con validación. LIMITACIÓN DECLARADA: el entrenamiento se ejecutó dos veces; tras ver los resultados de la primera "
                              "(comprensión de intención 65-77 %) se ampliaron las frases de entrenamiento y se añadieron variables de palabras clave. "
                              "Por eso la prueba y el conjunto natural ya no son totalmente independientes de las decisiones de diseño.")}
    (ROOT / "reports/asistente_selection.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "reports/asistente_evaluation.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    art = ROOT / "deployment/artifacts"
    if art.is_dir():
        shutil.copyfile(path, art / "asistente_lenguaje.joblib")
        mp = art / "manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        manifest["files"]["models/asistente_lenguaje.joblib"] = {"sha256": sha, "bytes": path.stat().st_size}
        mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for k in ("test_plantillas_no_vistas", "natural_a_mano"):
        print(k, json.dumps(out[k], indent=1, ensure_ascii=False) if k == "test_plantillas_no_vistas" else {x: out[k][x] for x in ("modelo_entrenado", "linea_base_similitud")})
    print("Errores en el conjunto natural:", len(out["natural_a_mano"]["errores"]), "de", len(nat))


if __name__ == "__main__":
    main()
