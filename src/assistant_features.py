"""Variables de texto del asistente. Viven en src/ (no en el script de entrenamiento) para que el modelo guardado pueda cargarse en cualquier parte."""
import re
import unicodedata

import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin

STEMS = {"HDF": r"calor|calient|calent|temperatur|refriger|enfri|ventila", "OSF": r"sobretens|torque|esfuerzo|tension|fuerza mecanica",
         "TWF": r"herramienta|fresa\b|filo|desgast|gastad", "PWF_low": r"potencia (baja|poca|insuficiente)|poca potencia|baja potencia|baja de potencia|falta de potencia|sin fuerza|no corta",
         "PWF_high": r"sobrecarga|potencia (alta|excesiva)|exceso de potencia|demasiada potencia"}


class KeywordFlags(BaseEstimator, TransformerMixin):
    """Variables binarias: ¿aparece una raíz típica de cada falla? El modelo aprende cuánto pesa cada una."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for t in X:
            t = "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))
            rows.append([1.0 if re.search(p, t) else 0.0 for p in STEMS.values()])
        return sparse.csr_matrix(np.array(rows))
