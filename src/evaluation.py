"""Evaluación de prueba de un pipeline ya seleccionado; no contiene entrenamiento."""

import hashlib
import json
import time
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from src.preparation import FEATURES, NUMERIC_FEATURES, TARGET, RAW_SHA256


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_experiment(root):
    """Verifica modelo, versiones y reserva; rechaza alteraciones del experimento."""
    selection_path = root / "reports/model_selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    preparation = json.loads((root / "reports/preparation_summary.json").read_text(encoding="utf-8"))
    model_path = root / selection["model_artifact"]
    if file_sha256(model_path) != selection["model_sha256"]:
        raise ValueError("El modelo no coincide con el seleccionado en el notebook 02.")
    for package, expected in selection["versions"].items():
        if version(package) != expected:
            raise ValueError(f"Versión diferente de {package}; utilizar requirements.txt.")
    if selection["features"] != FEATURES or selection["positive_class"] != 1:
        raise ValueError("El esquema o la clase positiva no coincide con la selección.")
    test_path = root / "data/processed/test.csv"
    test = pd.read_csv(test_path)
    if list(test.columns) != ["UDI"] + FEATURES + [TARGET] or len(test) != 2000:
        raise ValueError("Esquema o tamaño de prueba inesperado.")
    ids_hash = hashlib.sha256(",".join(map(str, test["UDI"])).encode("ascii")).hexdigest()
    if ids_hash != preparation["test_id_sha256"]:
        raise ValueError("Cambió la composición o el orden de prueba.")
    if not test["UDI"].is_unique or test.isna().any().any():
        raise ValueError("Identificadores repetidos o datos incompletos.")
    development_ids = pd.read_csv(root / "data/processed/development.csv", usecols=["UDI"])
    if not set(test["UDI"]).isdisjoint(development_ids["UDI"]):
        raise ValueError("Hay identificadores compartidos entre desarrollo y prueba.")
    if not test[TARGET].isin([0, 1]).all() or not test["Type"].isin(["L", "M", "H"]).all():
        raise ValueError("Etiquetas o tipos no válidos.")
    if not np.isfinite(test[NUMERIC_FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Mediciones no finitas.")
    # Comparar con el original solo comprueba integridad; no ajusta decisiones.
    raw_path = root / "data/raw/ai4i2020.csv"
    if file_sha256(raw_path) != RAW_SHA256:
        raise ValueError("La copia del dataset original cambió.")
    original = pd.read_csv(raw_path).set_index("UDI")
    expected = original.loc[test["UDI"], FEATURES + [TARGET]].reset_index()
    pd.testing.assert_frame_equal(test, expected, check_exact=False, rtol=1e-12, atol=1e-12)
    model = joblib.load(model_path)
    if list(model.feature_names_in_) != FEATURES or list(model.classes_) != [0, 1]:
        raise ValueError("El pipeline guardado tiene un esquema distinto.")
    for parameter, expected_value in selection["selected_params"].items():
        if model.get_params()[parameter] != expected_value:
            raise ValueError(f"Cambió el parámetro {parameter}.")
    fingerprints = {
        "model_sha256": file_sha256(model_path),
        "selection_sha256": file_sha256(selection_path),
        "test_csv_sha256": file_sha256(test_path),
    }
    return model, test, selection, fingerprints


def classification_metrics(y_true, y_pred):
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel())
    return {
        "rows": tn + fp + fn + tp,
        "true_negative": tn, "false_positive": fp,
        "false_negative": fn, "true_positive": tp,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": fp / (tn + fp),
        "false_negative_rate": fn / (tp + fn),
    }


def evaluate_frozen_model(model, test):
    X, y = test[FEATURES], test[TARGET]
    predicted = model.predict(X)
    # Son salidas del árbol, no probabilidades calibradas ni garantías de falla.
    scores = model.predict_proba(X)[:, 1]
    assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
    assert set(predicted).issubset({0, 1})
    # El calentamiento y la selección de filas no se incluyen en el cronometraje.
    for i in range(3):
        model.predict(X.iloc[[i]])
    timings = np.empty(len(X), dtype=float)
    timed_predictions = np.empty(len(X), dtype=int)
    for i in range(len(X)):
        row = X.iloc[[i]]
        start = time.perf_counter_ns()
        timed_predictions[i] = model.predict(row)[0]
        timings[i] = (time.perf_counter_ns() - start) / 1_000_000
    np.testing.assert_array_equal(predicted, timed_predictions)
    predictions = test.copy()
    predictions["prediction"] = predicted
    predictions["failure_score_uncalibrated"] = scores
    predictions["predict_ms"] = timings
    predictions["outcome"] = np.select(
        [(y == 0) & (predicted == 0), (y == 0) & (predicted == 1),
         (y == 1) & (predicted == 0), (y == 1) & (predicted == 1)],
        ["TN", "FP", "FN", "TP"], default="INVALID",
    )
    assert "INVALID" not in set(predictions["outcome"])
    latency = {
        "observations": len(timings),
        "mean_ms": float(timings.mean()),
        "median_ms": float(np.median(timings)),
        "p95_ms": float(np.percentile(timings, 95)),
        "definition": "Una llamada predict por observación: incluye transformaciones y clasificación; excluye carga CSV, selección de fila, interfaz y pausas.",
        "warmup_calls_excluded": 3,
    }
    return predictions, classification_metrics(y, predicted), latency
