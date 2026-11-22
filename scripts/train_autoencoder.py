"""Entrena y evalúa el autoencoder. Ejecutar desde la raíz: python scripts/train_autoencoder.py

Protocolo: la arquitectura y el umbral se eligen SOLO con desarrollo (validación cruzada de 5 pliegues).
La prueba se usa una única vez, al final, y no cambia ninguna decisión. El árbol congelado no se modifica.
"""
import hashlib
import json
import shutil
import sys
import warnings
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from src.autoencoder import SEED, fit_autoencoder, reconstruction_error
from src.evaluation import load_frozen_experiment
from src.features import load_physical_model
from src.preparation import FEATURES, TARGET

GRID = [(a, b, a) for a in (8, 10) for b in (3, 4, 5)]


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp),
            "precision": float(p), "recall": float(r), "f1": float(f), "false_positive_rate": float(fp / (fp + tn))}


def main():
    v1, test, _selection, _hashes = load_frozen_experiment(ROOT)
    physical = load_physical_model(ROOT)
    tree = physical[0] if physical else v1
    pre = tree.named_steps["preprocess"]
    dev = pd.read_csv(ROOT / "data/processed/development.csv")
    Zd, yd = pre.transform(dev[FEATURES]), dev[TARGET].to_numpy()
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(Zd, yd))

    table, oof_by_config = [], {}
    for hidden in GRID:
        oof, aucs = np.zeros(len(dev)), []
        for tr, va in folds:
            normal = tr[yd[tr] == 0]
            bundle = {k: v for k, v in zip(("scaler", "mlp"), fit_autoencoder(Zd[normal], hidden))}
            oof[va] = reconstruction_error(bundle, Zd[va])
            aucs.append(roc_auc_score(yd[va], oof[va]))
        oof_by_config[hidden] = oof
        table.append({"hidden": list(hidden), "auc_mean": float(np.mean(aucs)), "auc_sd": float(np.std(aucs))})
        print(hidden, "AUC %.3f ± %.3f" % (np.mean(aucs), np.std(aucs)), flush=True)
    best = max(table, key=lambda r: r["auc_mean"])
    hidden = tuple(best["hidden"])

    # Modelo final: se entrena con las observaciones normales del 80 % de desarrollo del primer pliegue y
    # el umbral se fija de antemano, sin ajustarlo a las fallas: percentil 99 del error de las
    # observaciones normales del 20 % restante, que ese modelo no vio (~1 % de falsas alarmas).
    tr, va = folds[0]
    scaler, mlp = fit_autoencoder(Zd[tr[yd[tr] == 0]], hidden)
    bundle = {"scaler": scaler, "mlp": mlp, "hidden": list(hidden)}
    held = reconstruction_error(bundle, Zd[va])
    threshold = float(np.quantile(held[yd[va] == 0], 0.99))
    bundle["threshold"] = threshold
    dev_metrics = metrics(yd[va], held > threshold)

    # Prueba: una sola evaluación; el árbol y el autoencoder sobre las mismas 2 000 observaciones.
    Zt, yt = pre.transform(test[FEATURES]), test[TARGET].to_numpy()
    err = reconstruction_error(bundle, Zt)
    ae_pred, tree_pred = (err > threshold).astype(int), tree.predict(test[FEATURES])
    missed = (tree_pred == 0) & (yt == 1)
    evaluation = {
        "protocol": "Arquitectura y umbral elegidos solo con desarrollo; la prueba se evaluó una vez.",
        "autoencoder_alone": metrics(yt, ae_pred),
        "auc_roc": float(roc_auc_score(yt, err)), "average_precision": float(average_precision_score(yt, err)),
        "base_rate": float(yt.mean()),
        "tree_alone": metrics(yt, tree_pred),
        "tree_or_autoencoder": metrics(yt, ((tree_pred == 1) | (ae_pred == 1)).astype(int)),
        "tree_and_autoencoder": metrics(yt, ((tree_pred == 1) & (ae_pred == 1)).astype(int)),
        "tree_missed_failures": int(missed.sum()), "tree_missed_caught_by_autoencoder": int((missed & (ae_pred == 1)).sum()),
        "development_holdout": dev_metrics,
    }

    model_path = ROOT / "models/autoencoder.joblib"
    joblib.dump(bundle, model_path)
    sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    selection = {"model_artifact": "models/autoencoder.joblib", "model_sha256": sha, "hidden_layers": list(hidden),
                 "architecture": [Zd.shape[1], *hidden, Zd.shape[1]], "activation": "relu (salida lineal)",
                 "threshold": threshold, "threshold_rule": "Percentil 99 del error de reconstrucción de las observaciones normales de desarrollo no vistas por el modelo (20 %)",
                 "trained_on": f"{int((yd[tr] == 0).sum())} observaciones sin falla del 80 % de desarrollo; umbral con el 20 % restante",
                 "seed": SEED, "cv_candidates": table,
                 "versions": {p: version(p) for p in ("scikit-learn", "numpy", "pandas", "joblib")}}
    (ROOT / "reports/autoencoder_selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "reports/autoencoder_evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Paquete de despliegue
    bundle_dir = ROOT / "deployment/artifacts"
    shutil.copyfile(model_path, bundle_dir / "autoencoder.joblib")
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["models/autoencoder.joblib"] = {"sha256": sha, "bytes": model_path.stat().st_size}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: evaluation[k] for k in ("autoencoder_alone", "auc_roc", "tree_alone", "tree_or_autoencoder", "tree_missed_failures", "tree_missed_caught_by_autoencoder")}, indent=1))


if __name__ == "__main__":
    main()
