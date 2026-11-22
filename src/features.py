"""Variables físicas derivadas de las cinco mediciones (documentación pública de AI4I 2020).

Se calculan dentro del pipeline, así el modelo sigue recibiendo solo las seis variables originales.
"""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from src.preparation import NUMERIC_FEATURES

POWER, DELTA_T, STRAIN = "Power [W]", "Temp diff [K]", "Wear x torque [minNm]"
DERIVED = [POWER, DELTA_T, STRAIN]
MODEL_NUMERIC = NUMERIC_FEATURES + DERIVED
DERIVED_RANGES = {POWER: (1000.0, 11000.0), DELTA_T: (7.5, 12.5), STRAIN: (0.0, 17000.0)}
SHORT_LABELS = {
    "Air temperature [K]": "Aire", "Process temperature [K]": "Proceso", "Rotational speed [rpm]": "Rotación",
    "Torque [Nm]": "Torque", "Tool wear [min]": "Desgaste", POWER: "Potencia", DELTA_T: "ΔT",
    STRAIN: "Desg.×Torque", "Type_H": "Tipo H", "Type_L": "Tipo L", "Type_M": "Tipo M",
}


def add_physical_features(X):
    X = pd.DataFrame(X).copy()
    X[POWER] = X["Torque [Nm]"] * X["Rotational speed [rpm]"] * 2 * np.pi / 60  # W
    X[DELTA_T] = X["Process temperature [K]"] - X["Air temperature [K]"]
    X[STRAIN] = X["Tool wear [min]"] * X["Torque [Nm]"]
    return X


def _names_out(transformer, input_features):
    return list(input_features) + DERIVED


def build_physical_pipeline(**tree_params):
    columns = ColumnTransformer([
        ("numeric", "passthrough", MODEL_NUMERIC),
        ("type", OneHotEncoder(categories=[["H", "L", "M"]], handle_unknown="error"), ["Type"]),
    ])
    preprocess = Pipeline([
        ("physics", FunctionTransformer(add_physical_features, feature_names_out=_names_out)),
        ("columns", columns),
    ])
    return Pipeline([("preprocess", preprocess),
                     ("model", DecisionTreeClassifier(random_state=42, **tree_params))])


def load_physical_model(root):
    """Modelo v2 verificado (hash y versiones) con su evaluación, o None si el experimento no lo incluye."""
    root = Path(root)
    info_path, model_path = root / "reports/modelo_fisico_selection.json", root / "models/modelo_fisico.joblib"
    if not info_path.is_file() or not model_path.is_file():
        return None
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != info["model_sha256"]:
        raise ValueError("El modelo con variables físicas no coincide con el registrado.")
    for package, expected in info["versions"].items():
        if version(package) != expected:
            raise ValueError(f"Versión diferente de {package}; utilizar requirements.txt.")
    info["evaluation"] = json.loads((root / "reports/modelo_fisico_evaluation.json").read_text(encoding="utf-8"))
    return joblib.load(model_path), info
