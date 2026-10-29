"""Reproducción de la reserva verificada con el pipeline congelado, sin entrenamiento."""

import io
import threading
import time
from collections import Counter

import numpy as np
import pandas as pd

from src.preparation import FEATURES, NUMERIC_FEATURES, TARGET

CSV_COLUMNS = ["UDI"] + FEATURES + [TARGET]
EXPORT_COLUMNS = CSV_COLUMNS + ["prediction", "alert", "outcome", "predict_ms", "processing_ms"]


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

    def __init__(self, model, test, fingerprints):
        validate_observations(test)
        self.model = model
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
        # Calentamiento excluido de los tiempos de las observaciones.
        for i in range(3):
            self.model.predict(self.test.iloc[[i]][FEATURES])

    def snapshot(self):
        with self.lock:
            counts = Counter(row["outcome"] for row in self.records)
            timings = [row["predict_ms"] for row in self.records]
            processing = [row["processing_ms"] for row in self.records]
            return {
                "status": self.status, "processed": len(self.records), "total": len(self.test),
                "interval_seconds": self.interval, "error": self.error,
                "last": self.records[-1].copy() if self.records else None,
                "recent": [row.copy() for row in reversed(self.records[-8:])],
                "counts": {key: counts.get(key, 0) for key in ("TN", "FP", "FN", "TP")},
                "alerts": counts.get("TP", 0) + counts.get("FP", 0),
                "predict_mean_ms": float(np.mean(timings)) if timings else None,
                "predict_p95_ms": float(np.percentile(timings, 95)) if timings else None,
                "processing_mean_ms": float(np.mean(processing)) if processing else None,
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
            return pd.DataFrame(self.records, columns=EXPORT_COLUMNS).to_csv(index=False)
