"""Auditoría y particiones reproducibles; este módulo no entrena clasificadores."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
TEST_SIZE = 0.20
N_FOLDS = 5
RAW_SHA256 = "dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e"
NUMERIC_FEATURES = [
    "Air temperature [K]", "Process temperature [K]",
    "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
]
CATEGORICAL_FEATURES = ["Type"]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "Machine failure"
FAILURE_FLAGS = ["TWF", "HDF", "PWF", "OSF", "RNF"]
EXCLUDED = ["UDI", "Product ID", TARGET] + FAILURE_FLAGS


def load_dataset(path: Path) -> pd.DataFrame:
    """Valida la copia original antes de continuar; no corrige ni elimina filas."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != RAW_SHA256:
        raise ValueError("El CSV cambió respecto de la copia oficial registrada.")
    frame = pd.read_csv(path)
    if set(frame.columns) != set(FEATURES + EXCLUDED) or len(frame) != 10_000:
        raise ValueError("El esquema o número de registros no coincide con AI4I.")
    if frame.isna().any().any() or not frame["UDI"].is_unique:
        raise ValueError("Hay valores ausentes o identificadores repetidos.")
    if not frame["Type"].isin(["L", "M", "H"]).all():
        raise ValueError("Se encontró un tipo de producto desconocido.")
    numeric = frame[NUMERIC_FEATURES].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or (numeric < 0).any():
        raise ValueError("Hay mediciones negativas o no finitas.")
    if (frame[NUMERIC_FEATURES[:-1]] <= 0).any().any():
        raise ValueError("Hay temperaturas, velocidades o torque no positivos.")
    if not frame[[TARGET] + FAILURE_FLAGS].isin([0, 1]).all().all():
        raise ValueError("Hay etiquetas fuera del dominio binario.")
    return frame


def audit_dataset(frame: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Registra calidad y discrepancias sin reconstruir la etiqueta principal."""
    disagreement = frame[TARGET].ne(frame[FAILURE_FLAGS].max(axis=1))
    cases = frame.loc[disagreement, ["UDI", TARGET] + FAILURE_FLAGS].copy()
    summary = {
        "rows": len(frame), "columns": len(frame.columns),
        "sha256": RAW_SHA256,
        "missing_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_feature_vectors": int(frame.duplicated(FEATURES).sum()),
        "target_counts": {str(k): int(v) for k, v in frame[TARGET].value_counts().sort_index().items()},
        "target_flag_disagreements": len(cases),
        "failure_without_flag": int(((frame[TARGET] == 1) & (frame[FAILURE_FLAGS].max(axis=1) == 0)).sum()),
        "flag_without_failure": int(((frame[TARGET] == 0) & (frame[FAILURE_FLAGS].max(axis=1) == 1)).sum()),
        "label_policy": "Conservar Machine failure; documentar discrepancias; no usar indicadores de falla como entradas.",
    }
    return summary, cases


def make_partitions(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reserva 20 % para prueba y asigna los cinco pliegues dentro del 80 %."""
    development, test = train_test_split(
        frame, test_size=TEST_SIZE, stratify=frame[TARGET], random_state=SEED,
    )
    development = development.reset_index(drop=True)
    test = test.reset_index(drop=True)
    folds = pd.DataFrame({"UDI": development["UDI"], "validation_fold": -1})
    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    for fold, (train_indices, validation_indices) in enumerate(
        splitter.split(development[FEATURES], development[TARGET]), start=1,
    ):
        assert set(train_indices).isdisjoint(validation_indices)
        folds.loc[validation_indices, "validation_fold"] = fold
    assert set(development["UDI"]).isdisjoint(test["UDI"])
    assert set(development["UDI"]) | set(test["UDI"]) == set(frame["UDI"])
    assert folds["validation_fold"].between(1, N_FOLDS).all()
    return development, test, folds


def make_preprocessor(scale_numeric: bool = False) -> ColumnTransformer:
    """Devuelve un transformador NUEVO, sin ajustar, para cada pipeline/pliegue."""
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler() if scale_numeric else "passthrough", NUMERIC_FEATURES),
            ("type", OneHotEncoder(handle_unknown="error", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop", verbose_feature_names_out=False,
    )


def partition_summary(development, test, folds) -> pd.DataFrame:
    """Cuenta clases para verificar el muestreo; no calcula rendimiento del modelo."""
    groups = {"development": development, "test": test}
    for fold in range(1, N_FOLDS + 1):
        groups[f"cv_{fold}_train"] = development.loc[folds["validation_fold"] != fold]
        groups[f"cv_{fold}_validation"] = development.loc[folds["validation_fold"] == fold]
    rows = []
    for name, group in groups.items():
        count = int(group[TARGET].sum())
        rows.append({"partition": name, "rows": len(group), "no_failure": len(group)-count,
                     "failure": count, "failure_percent": round(100*count/len(group), 4)})
    return pd.DataFrame(rows)
