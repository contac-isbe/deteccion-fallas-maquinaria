"""Autoencoder no supervisado: encoder -> espacio latente -> decoder.

Se entrena solo con observaciones SIN falla de desarrollo. Una observación cuyo error de
reconstrucción supera el umbral se marca como atípica. No reemplaza al árbol: es una segunda opinión.
"""
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

SEED = 42


def fit_autoencoder(Z_normal, hidden, seed=SEED):
    """Z_normal: matriz ya transformada por el preprocesador del pipeline."""
    scaler = StandardScaler().fit(Z_normal)
    S = scaler.transform(Z_normal)
    mlp = MLPRegressor(hidden_layer_sizes=tuple(hidden), activation="relu", max_iter=800,
                       random_state=seed, early_stopping=True, n_iter_no_change=30).fit(S, S)
    return scaler, mlp


def forward(bundle, Z):
    """Activaciones de cada capa: entrada, capas del encoder, latente, capas del decoder y salida."""
    scaler, mlp = bundle["scaler"], bundle["mlp"]
    a = scaler.transform(np.atleast_2d(Z))
    layers = [a]
    last = len(mlp.coefs_) - 1
    for i, (W, b) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        a = a @ W + b
        if i != last:
            a = np.maximum(a, 0)  # ReLU; la salida es lineal
        layers.append(a)
    return layers


def reconstruction_error(bundle, Z):
    layers = forward(bundle, Z)
    return ((layers[0] - layers[-1]) ** 2).mean(axis=1)


def describe(bundle, Z):
    """Detalle de una observación para dibujar la red en la interfaz."""
    layers = forward(bundle, Z)
    x, y = layers[0][0], layers[-1][0]
    err = float(((x - y) ** 2).mean())
    return {
        "input": [round(float(v), 4) for v in x],
        "encoder": [[round(float(v), 4) for v in layer[0]] for layer in layers[1:len(layers) // 2 + 1]],
        "decoder": [[round(float(v), 4) for v in layer[0]] for layer in layers[len(layers) // 2 + 1:-1]],
        "output": [round(float(v), 4) for v in y],
        "feature_error": [round(float(v), 4) for v in (x - y) ** 2],
        "error": err, "threshold": float(bundle["threshold"]), "alert": err > bundle["threshold"],
    }


def architecture(bundle):
    mlp = bundle["mlp"]
    return [mlp.coefs_[0].shape[0]] + [w.shape[1] for w in mlp.coefs_]


def load_autoencoder(root):
    """Devuelve el autoencoder verificado, o None si el experimento no lo incluye."""
    root = Path(root)
    info_path = root / "reports/autoencoder_selection.json"
    model_path = root / "models/autoencoder.joblib"
    if not info_path.is_file() or not model_path.is_file():
        return None
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != info["model_sha256"]:
        raise ValueError("El autoencoder no coincide con el registrado en reports/autoencoder_selection.json.")
    for package, expected in info["versions"].items():
        if version(package) != expected:
            raise ValueError(f"Versión diferente de {package}; utilizar requirements.txt.")
    bundle = joblib.load(model_path)
    bundle["info"] = info
    return bundle
