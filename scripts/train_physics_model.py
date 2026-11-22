"""Árbol v2 con variables físicas. Ejecutar desde la raíz: python scripts/train_physics_model.py

Protocolo: hiperparámetros elegidos SOLO con desarrollo (CV de 5 pliegues, F1). La prueba se evalúa
una vez, al final, como SEGUNDA evaluación: el modelo v1 ya se había evaluado con esa misma prueba.
"""
import hashlib, json, shutil, sys, warnings
from importlib.metadata import version
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
from src.evaluation import load_frozen_experiment
from src.features import build_physical_pipeline
from src.preparation import FEATURES, TARGET


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp),
            "precision": float(p), "recall": float(r), "f1": float(f), "false_positive_rate": float(fp / (fp + tn))}


def main():
    v1, test, _, _ = load_frozen_experiment(ROOT)
    dev = pd.read_csv(ROOT / "data/processed/development.csv")
    X, y = dev[FEATURES], dev[TARGET].to_numpy()
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    rows = []
    for leaf, depth in product((1, 3, 5, 10, 20), (4, 6, 8, 10, None)):
        model = build_physical_pipeline(min_samples_leaf=leaf, max_depth=depth)
        pred = cross_val_predict(model, X, y, cv=cv)
        p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        rows.append({"min_samples_leaf": leaf, "max_depth": depth, "precision": float(p), "recall": float(r), "f1": float(f)})
        print(leaf, depth, "F1 %.3f R %.3f P %.3f" % (f, r, p), flush=True)
    # Mejor F1; con empate práctico (<0.005) se prefiere el árbol más pequeño (más fácil de explicar).
    top = max(r["f1"] for r in rows)
    near = [r for r in rows if top - r["f1"] < 0.005]
    best = min(near, key=lambda r: (r["max_depth"] or 99, -r["min_samples_leaf"]))
    model = build_physical_pipeline(min_samples_leaf=best["min_samples_leaf"], max_depth=best["max_depth"]).fit(X, y)
    pred, tree = model.predict(test[FEATURES]), model.named_steps["model"]
    proba = model.predict_proba(test[FEATURES])[:, 1]
    evaluation = {"protocol": "Hiperparámetros elegidos solo con desarrollo; la prueba se evaluó una vez (segunda evaluación: v1 ya la usó).",
                  "v2_test": metrics(test[TARGET], pred), "v1_test": metrics(test[TARGET], v1.predict(test[FEATURES])),
                  "auc_roc": float(roc_auc_score(test[TARGET], proba)),
                  "nodes": int(tree.tree_.node_count), "leaves": int(tree.get_n_leaves()), "depth": int(tree.get_depth())}
    path = ROOT / "models/modelo_fisico.joblib"
    joblib.dump(model, path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    selection = {"model_artifact": "models/modelo_fisico.joblib", "model_sha256": sha, "features": FEATURES, "positive_class": 1,
                 "derived_features": ["Power [W] = Torque × rpm × 2π/60", "Temp diff [K] = Process − Air", "Wear x torque [minNm]"],
                 "chosen": best, "cv_grid": rows,
                 "versions": {p: version(p) for p in ("scikit-learn", "numpy", "pandas", "joblib")}}
    (ROOT / "reports/modelo_fisico_selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "reports/modelo_fisico_evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bundle = ROOT / "deployment/artifacts"
    shutil.copyfile(path, bundle / "modelo_fisico.joblib")
    mp = bundle / "manifest.json"
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    manifest["files"]["models/modelo_fisico.joblib"] = {"sha256": sha, "bytes": path.stat().st_size}
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("elegido", best); print(json.dumps({k: evaluation[k] for k in ("v1_test", "v2_test", "auc_roc", "nodes", "leaves", "depth")}, indent=1))


if __name__ == "__main__":
    main()
