"""Reproducción de la reserva verificada con el pipeline congelado, sin entrenamiento."""

import io
import threading
import time
from collections import Counter

import numpy as np
import pandas as pd

from src.autoencoder import architecture, describe as describe_ae
from src.features import DERIVED_RANGES, SHORT_LABELS
from src.plant import Plant
from src.preparation import FEATURES, NUMERIC_FEATURES, TARGET

CSV_COLUMNS = ["UDI"] + FEATURES + [TARGET]
EXPORT_COLUMNS = CSV_COLUMNS + ["prediction", "alert", "outcome", "predict_ms", "processing_ms"]

# Rango observado en AI4I 2020; limita el laboratorio a valores que el dataset contiene.
RANGES = {
    "Air temperature [K]": (295.0, 305.0),
    "Process temperature [K]": (305.0, 314.0),
    "Rotational speed [rpm]": (1100.0, 2900.0),
    "Torque [Nm]": (3.0, 77.0),
    "Tool wear [min]": (0.0, 254.0),
}


def describe_tree(model, ae=None, reference=None):
    """Estructura del árbol congelado; solo lectura, no entrena ni modifica el modelo."""
    pre, tree = model.named_steps["preprocess"], model.named_steps["model"]
    t = tree.tree_
    names = [str(n).split("__", 1)[-1] for n in pre.get_feature_names_out()]
    counts = t.value[:, 0, :] * t.weighted_n_node_samples[:, None]
    nodes = []
    for i in range(t.node_count):
        leaf = t.children_left[i] == -1
        nodes.append({
            "f": -1 if leaf else int(t.feature[i]),
            "t": None if leaf else round(float(t.threshold[i]), 4),
            "l": int(t.children_left[i]), "r": int(t.children_right[i]),
            "n": int(round(counts[i].sum())), "fail": int(round(counts[i][1])),
        })
    return {
        "features": names,
        "importances": [round(float(x), 5) for x in tree.feature_importances_],
        "ranges": {**{k: list(v) for k, v in RANGES.items()}, **{k: list(v) for k, v in DERIVED_RANGES.items()}},
        "reference": reference, "nodes": nodes, "depth": int(tree.get_depth()), "leaves": int(tree.get_n_leaves()),
        "train_rows": int(round(counts[0].sum())), "train_failures": int(round(counts[0][1])),
        "autoencoder": None if ae is None else {
            "architecture": architecture(ae), "threshold": float(ae["threshold"]),
            "input_names": [SHORT_LABELS.get(name, name) for name in names],
            "trained_on": ae["info"]["trained_on"], "evaluation": ae["info"].get("evaluation")},
    }


def validate_observations(frame):
    """Comprueba el esquema y los dominios antes de llamar al modelo."""
    if list(frame.columns) != CSV_COLUMNS:
        raise ValueError("Columnas incorrectas. Utiliza data/processed/test.csv, sin cambiar su encabezado.")
    if frame.empty or frame.isna().any().any():
        raise ValueError("El CSV está vacío o contiene valores ausentes.")
    if not frame["UDI"].is_unique:
        raise ValueError("El CSV contiene identificadores repetidos.")
    numeric_columns = ["UDI"] + NUMERIC_FEATURES + [TARGET]
    try:
        numbers = frame[numeric_columns].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Las mediciones, UDI y la etiqueta deben ser numéricos.") from exc
    if not np.isfinite(numbers).all():
        raise ValueError("Hay valores numéricos no finitos.")
    if not frame["Type"].isin(["L", "M", "H"]).all():
        raise ValueError("Tipo de producto inválido: solo se admiten L, M y H.")
    if not frame[TARGET].isin([0, 1]).all():
        raise ValueError("Machine failure debe ser 0 o 1.")
    ids = frame["UDI"].to_numpy(dtype=float)
    if (ids <= 0).any() or (ids != np.floor(ids)).any():
        raise ValueError("UDI debe contener identificadores enteros positivos.")
    if (frame[NUMERIC_FEATURES[:-1]].to_numpy(dtype=float) <= 0).any():
        raise ValueError("Temperaturas, velocidad y torque deben ser positivos.")
    if (frame["Tool wear [min]"].to_numpy(dtype=float) < 0).any():
        raise ValueError("El desgaste no puede ser negativo.")


class Simulator:
    """Estado único local. Cada sesión recorre la misma reserva en su orden original."""

    def __init__(self, model, test, fingerprints, ae=None, reference=None):
        validate_observations(test)
        self.model = model
        self.ae = ae
        self._plant = None
        self.reference = reference
        self.test = test.copy(deep=True)
        self.fingerprints = fingerprints.copy()
        self.lock = threading.RLock()
        self.records = []
        self.status = "ready"
        self.interval = 0.5
        self.error = None
        self._deadline = 0.0
        self._stop = threading.Event()
        self._thread = None
        self._pre = model.named_steps["preprocess"]
        self._tree = model.named_steps["model"]
        self.node_hits = np.zeros(self._tree.tree_.node_count, dtype=int)
        # Calentamiento excluido de los tiempos de las observaciones.
        for i in range(3):
            self.model.predict(self.test.iloc[[i]][FEATURES])

    @property
    def plant(self):
        """Planta simulada de la sesión; se crea al usarla por primera vez."""
        if self._plant is None:
            self._plant = Plant(self)
        return self._plant

    @staticmethod
    def _light(row):
        return {k: v for k, v in row.items() if k != "ae"}

    def _ae_counts(self):
        if not self.ae:
            return None
        real = lambda r: r[TARGET]
        tp = sum(1 for r in self.records if real(r) and r["ae_alert"])
        fp = sum(1 for r in self.records if not real(r) and r["ae_alert"])
        fn = sum(1 for r in self.records if real(r) and not r["ae_alert"])
        tn = len(self.records) - tp - fp - fn
        both = sum(1 for r in self.records if r["alert"] and r["ae_alert"])
        only_ae = sum(1 for r in self.records if r["ae_alert"] and not r["alert"])
        rescued = sum(1 for r in self.records if real(r) and not r["alert"] and r["ae_alert"])
        return {"TN": tn, "FP": fp, "FN": fn, "TP": tp, "both": both, "only_ae": only_ae, "rescued": rescued}

    def trace(self, X):
        """Camino que recorre una observación por el árbol, calculado fuera del cronómetro del modelo."""
        Xt = self._pre.transform(X)
        path = [int(i) for i in self._tree.decision_path(Xt).indices]
        leaf = path[-1]
        t = self._tree.tree_
        n = float(t.weighted_n_node_samples[leaf])
        p_fail = float(t.value[leaf, 0, 1])
        return {"path": path, "leaf": leaf, "leaf_n": int(round(n)),
                "leaf_fail": int(round(p_fail * n)), "p_fail": p_fail}

    def explain(self, values):
        """Laboratorio: responde a una observación escrita por el usuario; no entra al registro."""
        if not isinstance(values, dict) or set(values) != set(FEATURES):
            raise ValueError("Envía las seis variables de entrada.")
        if values["Type"] not in ("L", "M", "H"):
            raise ValueError("Tipo de producto inválido: solo se admiten L, M y H.")
        row = {"Type": values["Type"]}
        for name, (low, high) in RANGES.items():
            value = values[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
                raise ValueError(f"{name} debe ser numérico.")
            if not low <= value <= high:
                raise ValueError(f"{name} debe estar entre {low:g} y {high:g}.")
            row[name] = float(value)
        X = pd.DataFrame([row])[FEATURES]
        started = time.perf_counter_ns()
        prediction = int(self.model.predict(X)[0])
        predict_ms = (time.perf_counter_ns() - started) / 1_000_000
        result = self.trace(X)
        result.update({"prediction": prediction, "alert": prediction == 1, "predict_ms": predict_ms})
        if self.ae:
            result["ae"] = describe_ae(self.ae, self._pre.transform(X))
        return result

    def snapshot(self):
        with self.lock:
            counts = Counter(row["outcome"] for row in self.records)
            timings = [row["predict_ms"] for row in self.records]
            processing = [row["processing_ms"] for row in self.records]
            return {
                "status": self.status, "processed": len(self.records), "total": len(self.test),
                "interval_seconds": self.interval, "error": self.error,
                "last": self.records[-1].copy() if self.records else None,
                "recent": [self._light(row) for row in reversed(self.records[-8:])],
                "series": [self._light(row) for row in self.records[-60:]],
                "ae_counts": self._ae_counts(),
                "counts": {key: counts.get(key, 0) for key in ("TN", "FP", "FN", "TP")},
                "alerts": counts.get("TP", 0) + counts.get("FP", 0),
                "predict_mean_ms": float(np.mean(timings)) if timings else None,
                "predict_p95_ms": float(np.percentile(timings, 95)) if timings else None,
                "processing_mean_ms": float(np.mean(processing)) if processing else None,
                "node_hits": self.node_hits.tolist(),
            }

    def start(self, interval=0.5):
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or not np.isfinite(interval) or not 0.2 <= interval <= 5:
            raise ValueError("El intervalo debe estar entre 0,2 y 5 segundos.")
        with self.lock:
            if self.status == "completed":
                raise ValueError("La reproducción terminó. Reinicia para comenzar otra sesión.")
            if self.status == "error":
                raise ValueError("Corrige el problema y reinicia antes de continuar.")
            self.interval = float(interval)
            self._deadline = time.monotonic()
            self.status = "running"
            return self.snapshot()

    def pause(self):
        with self.lock:
            if self.status == "running":
                self.status = "paused"
            return self.snapshot()

    def reset(self):
        with self.lock:
            self.status, self.error = "ready", None
            self.records.clear()
            self.node_hits[:] = 0
            return self.snapshot()

    def _process_next(self):
        started = time.perf_counter_ns()
        row = self.test.iloc[[len(self.records)]]
        validate_observations(row)
        X = row[FEATURES]  # Ni UDI ni la etiqueta real entran en predict.
        predict_start = time.perf_counter_ns()
        prediction = int(self.model.predict(X)[0])
        predict_ms = (time.perf_counter_ns() - predict_start) / 1_000_000
        if prediction not in (0, 1):
            raise ValueError("El modelo devolvió una clase inválida.")
        actual = int(row[TARGET].iloc[0])  # Comparación posterior a la inferencia.
        outcome = {(0, 0): "TN", (0, 1): "FP", (1, 0): "FN", (1, 1): "TP"}[(actual, prediction)]
        record = {"UDI": int(row["UDI"].iloc[0]), "Type": str(row["Type"].iloc[0])}
        record.update({name: float(row[name].iloc[0]) for name in NUMERIC_FEATURES})
        record.update({TARGET: actual, "prediction": prediction, "alert": prediction == 1,
                       "outcome": outcome, "predict_ms": predict_ms})
        record.update(self.trace(X))
        if (record["p_fail"] > 0.5) != (prediction == 1):
            raise ValueError("El camino del árbol no coincide con la predicción del pipeline.")
        self.node_hits[record["path"]] += 1
        if self.ae:
            detail = describe_ae(self.ae, self._pre.transform(X))
            record.update({"ae": detail, "ae_error": detail["error"], "ae_alert": detail["alert"]})
        record["processing_ms"] = (time.perf_counter_ns() - started) / 1_000_000
        self.records.append(record)
        if len(self.records) == len(self.test):
            self.status = "completed"

    def step(self):
        with self.lock:
            if self.status in ("running", "error", "completed"):
                raise ValueError("Pausa o reinicia antes de avanzar un registro manualmente.")
            try:
                self._process_next()
                if self.status != "completed":
                    self.status = "paused"
            except Exception:
                self.status = "error"
                self.error = "No se pudo procesar la observación. Comprueba el CSV y el modelo."
                raise
            return self.snapshot()

    def tick(self, now=None):
        with self.lock:
            now = time.monotonic() if now is None else now
            if self.status == "running" and now >= self._deadline:
                try:
                    self._process_next()
                except Exception:
                    self.status = "error"
                    self.error = "Se detuvo la reproducción por una observación o predicción inválida."
                self._deadline = time.monotonic() + self.interval

    def start_worker(self):
        def loop():
            while not self._stop.wait(0.025):
                self.tick()
        self._thread = threading.Thread(target=loop, daemon=True, name="ai4i-replay")
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def load_csv(self, text):
        """Acepta solo la reserva completa original, sin nuevas muestras ni etiquetas."""
        with self.lock:
            if self.status == "running":
                raise ValueError("Pausa la reproducción antes de cargar un CSV.")
            try:
                frame = pd.read_csv(io.StringIO(text.lstrip("\ufeff")))
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
                raise ValueError("No se pudo leer el CSV. Utiliza un archivo UTF-8 separado por comas.") from exc
            validate_observations(frame)
            try:
                pd.testing.assert_frame_equal(frame, self.test, check_dtype=False, check_exact=True)
            except AssertionError as exc:
                raise ValueError("El archivo no coincide con la reserva completa y su orden original. Utiliza data/processed/test.csv.") from exc
            # Solo una carga válida inicia una sesión vacía; un error conserva el avance.
            return self.reset()

    def export_csv(self):
        with self.lock:
            columns = EXPORT_COLUMNS + (["ae_error", "ae_alert"] if self.ae else [])
            return pd.DataFrame(self.records, columns=columns).to_csv(index=False)
