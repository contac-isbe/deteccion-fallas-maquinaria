"""Comparación con desarrollo; nunca carga ni evalúa la reserva de prueba."""

import hashlib
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, make_scorer, precision_score
from sklearn.model_selection import GridSearchCV, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from src.preparation import FEATURES, TARGET, SEED, N_FOLDS, make_preprocessor


def false_positive_rate(y_true, y_pred):
    tn, fp, _, _ = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return float(fp / (tn + fp))


SCORING = {
    "f1": "f1", "precision": make_scorer(precision_score, zero_division=0), "recall": "recall",
    "accuracy": "accuracy",
    "neg_fpr": make_scorer(false_positive_rate, greater_is_better=False),
}


def best_index(results):
    """Mayor F1 medio; en empate numérico, mayor recall y menor FPR."""
    scores = np.asarray(results["mean_test_f1"])
    if not np.isfinite(scores).all():
        raise ValueError("Hay configuraciones con puntuaciones no válidas.")
    candidates = np.flatnonzero(np.isclose(scores, scores.max(), atol=1e-12, rtol=0))
    return int(sorted(candidates, key=lambda i: (
        -results["mean_test_recall"][i], -results["mean_test_neg_fpr"][i], i,
    ))[0])


def load_development(root):
    frame = pd.read_csv(root / "data/processed/development.csv")
    folds = pd.read_csv(root / "data/processed/cv_folds.csv")
    metadata = json.loads((root / "reports/preparation_summary.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(",".join(map(str, frame["UDI"])).encode("ascii")).hexdigest()
    if digest != metadata["development_id_sha256"]:
        raise ValueError("Cambió la composición u orden de desarrollo; ejecutar notebook 01.")
    if list(frame.columns) != ["UDI"] + FEATURES + [TARGET] or len(frame) != 8000:
        raise ValueError("Esquema inesperado de desarrollo.")
    if not frame["UDI"].is_unique or frame.isna().any().any():
        raise ValueError("Datos incompletos o identificadores repetidos.")
    if not frame["UDI"].equals(folds["UDI"]):
        raise ValueError("Los pliegues no corresponden al orden de desarrollo.")
    if set(folds.validation_fold) != set(range(1, N_FOLDS + 1)):
        raise ValueError("Asignación de pliegues inválida.")
    cv = []
    for fold in range(1, N_FOLDS + 1):
        validation = np.flatnonzero(folds.validation_fold.eq(fold))
        training = np.flatnonzero(folds.validation_fold.ne(fold))
        assert len(training) == 6400 and len(validation) == 1600
        assert set(training).isdisjoint(validation)
        assert set(frame.iloc[validation][TARGET]) == {0, 1}
        cv.append((training, validation))
    assert np.array_equal(np.sort(np.concatenate([v for _, v in cv])), np.arange(len(frame)))
    return frame, cv, metadata


def model_specs():
    return {
        "Regresión logística": (
            LogisticRegression(solver="lbfgs", max_iter=2000, random_state=SEED), True,
            {"model__C": [0.1, 1.0, 10.0], "model__class_weight": [None, "balanced"]},
        ),
        "Árbol de decisión": (
            DecisionTreeClassifier(random_state=SEED), False,
            {"model__max_depth": [4, 8, None], "model__min_samples_leaf": [1, 5],
             "model__class_weight": [None, "balanced"]},
        ),
        "Random Forest": (
            RandomForestClassifier(random_state=SEED, n_jobs=1), False,
            {"model__n_estimators": [100, 200], "model__max_depth": [8, None],
             "model__min_samples_leaf": [1, 3], "model__class_weight": [None, "balanced"]},
        ),
    }


def compare_models(frame, cv):
    X, y = frame[FEATURES], frame[TARGET]
    summaries, all_results, fold_results, searches = [], [], [], {}
    # La referencia siempre predice la clase mayoritaria; no participa en la selección.
    baseline = Pipeline([("preprocess", make_preprocessor()),
                         ("model", DummyClassifier(strategy="most_frequent"))])
    base = cross_validate(baseline, X, y, cv=cv, scoring=SCORING, n_jobs=1)
    base_summary = {metric: float(np.mean(base["test_" + metric])) for metric in SCORING}
    for name, (model, scale, grid) in model_specs().items():
        print(f"Comparando {name}...", flush=True)
        pipeline = Pipeline([("preprocess", make_preprocessor(scale)), ("model", model)])
        search = GridSearchCV(pipeline, grid, scoring=SCORING, refit=best_index,
                              cv=cv, n_jobs=1, return_train_score=True, error_score="raise")
        start = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            search.fit(X, y)
        elapsed = time.perf_counter() - start
        results = pd.DataFrame(search.cv_results_)
        results.insert(0, "model_name", name)
        results["params"] = results["params"].map(lambda p: json.dumps(p, ensure_ascii=False, sort_keys=True))
        all_results.append(results)
        idx = search.best_index_
        row = {"model_name": name, "candidates": len(results), "search_seconds": elapsed,
               "best_params": json.dumps(search.best_params_, ensure_ascii=False, sort_keys=True)}
        for metric in SCORING:
            row["mean_" + metric] = float(search.cv_results_["mean_test_" + metric][idx])
            row["std_" + metric] = float(search.cv_results_["std_test_" + metric][idx])
        row["mean_fpr"] = -row.pop("mean_neg_fpr")
        row["std_fpr"] = row.pop("std_neg_fpr")
        row["mean_train_f1"] = float(search.cv_results_["mean_train_f1"][idx])
        summaries.append(row)
        for fold in range(N_FOLDS):
            item = {"model_name": name, "fold": fold + 1}
            for metric in SCORING:
                item[metric] = float(search.cv_results_[f"split{fold}_test_{metric}"][idx])
            item["fpr"] = -item.pop("neg_fpr")
            fold_results.append(item)
        searches[name] = search
        print(f"F1 medio: {row['mean_f1']:.4f}; {elapsed:.1f} s.", flush=True)
    comparison = pd.DataFrame(summaries).sort_values(
        ["mean_f1", "mean_recall", "mean_fpr", "model_name"],
        ascending=[False, False, True, True], kind="stable",
    ).reset_index(drop=True)
    return comparison, pd.concat(all_results, ignore_index=True), pd.DataFrame(fold_results), searches, base_summary
