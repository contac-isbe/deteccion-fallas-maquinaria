"""Pruebas funcionales y de integración sobre el modelo ya congelado.

No entrena modelos ni sustituye la evaluación del notebook 03.
"""

import csv
import io
import json
import platform
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import file_sha256, load_frozen_experiment
from src.preparation import FEATURES, NUMERIC_FEATURES, TARGET
from src.simulation import Simulator
from src.simulation_server import create_server


def main():
    cases = []
    protected = ["models/modelo_seleccionado.joblib", "reports/model_selection.json",
                 "reports/test_evaluation.json", "reports/test_predictions.csv",
                 "data/raw/ai4i2020.csv", "data/processed/test.csv"]
    before = {name: file_sha256(ROOT / name) for name in protected}
    model, test, selection, fingerprints = load_frozen_experiment(ROOT)
    simulator = Simulator(model, test, fingerprints)

    def passed(name, requirements, evidence):
        cases.append({"test": name, "requirements": requirements, "status": "passed", "evidence": evidence})

    def reject(name, frame):
        prior = simulator.snapshot()["processed"]
        try:
            simulator.load_csv(frame.to_csv(index=False))
        except ValueError as exc:
            assert simulator.snapshot()["processed"] == prior
            passed(name, ["RF1"], str(exc))
        else:
            raise AssertionError(f"No se rechazó: {name}")

    # Validación de errores que impide inferencias sobre entradas inválidas.
    simulator.step()
    reject("Columna requerida ausente", test.drop(columns=[FEATURES[0]]))
    damaged = test.copy(); damaged.loc[0, NUMERIC_FEATURES[0]] = np.nan
    reject("Medición ausente", damaged)
    damaged = test.copy(); damaged.loc[0, NUMERIC_FEATURES[0]] = np.inf
    reject("Medición infinita", damaged)
    damaged = test.copy(); damaged.loc[0, "Type"] = "X"
    reject("Tipo de producto desconocido", damaged)
    damaged = test.copy(); damaged.loc[0, "Torque [Nm]"] = -1
    reject("Medición fuera del dominio", damaged)
    damaged = test.copy(); damaged.loc[0, "UDI"] = damaged.loc[1, "UDI"]
    reject("Identificador duplicado", damaged)
    damaged = test.copy(); damaged.loc[0, TARGET] = 2
    reject("Etiqueta fuera del dominio binario", damaged)
    reject("Reserva reordenada", test.iloc[::-1].reset_index(drop=True))
    reject("Reserva incompleta", test.iloc[:-1])
    damaged = test.copy(); damaged.loc[0, "Torque [Nm]"] += 0.1
    reject("Medición alterada respecto de la reserva", damaged)
    assert simulator.load_csv(test.to_csv(index=False))["processed"] == 0
    passed("Carga correcta y reinicio de sesión", ["RF1", "RF3"], "CSV completo aceptado; avance = 0.")

    # Asegura que los identificadores y etiquetas no llegan al pipeline.
    class InspectModel:
        def __init__(self, underlying):
            self.underlying = underlying
            self.calls = 0
        def predict(self, X):
            assert list(X.columns) == FEATURES
            assert "UDI" not in X and TARGET not in X
            self.calls += 1
            return self.underlying.predict(X)
    inspected = InspectModel(model)
    probe = Simulator(inspected, test, fingerprints)
    probe.step()
    assert inspected.calls == 4  # Tres calentamientos y una observación.
    passed("Entradas del modelo separadas de la etiqueta", ["RF2", "RNF2"], "predict recibió exactamente las seis variables, también durante el calentamiento.")

    # Predicciones repetidas y exportación completa, sin entrenamiento con prueba.
    for _ in range(len(test)):
        simulator.step()
    full = pd.read_csv(io.StringIO(simulator.export_csv()))
    recorded = pd.read_csv(ROOT / "reports/test_predictions.csv")
    assert list(full["UDI"]) == list(recorded["UDI"]) == list(test["UDI"])
    np.testing.assert_array_equal(full["prediction"], recorded["prediction"])
    np.testing.assert_array_equal(full[TARGET], test[TARGET])
    assert list(full["outcome"]) == list(recorded["outcome"])
    np.testing.assert_array_equal(full["alert"], full["prediction"].eq(1))
    assert (full["processing_ms"] >= full["predict_ms"]).all()
    state = simulator.snapshot()
    assert state["status"] == "completed" and state["processed"] == 2000
    assert state["counts"] == {"TN": 1919, "FP": 13, "FN": 18, "TP": 50}
    assert state["alerts"] == 63
    assert len(state["series"]) == 60
    assert [row["UDI"] for row in state["series"]] == list(test["UDI"].tail(60))
    assert state["series"][-1] == state["last"]
    passed("Reproducción completa y predicciones sin cambios", ["RF2", "RF3", "RF6", "RNF1", "RNF2"], "2 000 UDI en el mismo orden y 2 000 predicciones idénticas al notebook 03; TN 1919, FP 13, FN 18, TP 50.")
    passed("Alerta activada por la predicción", ["RF4"], "63 alertas = 50 verdaderos positivos + 13 falsos positivos; las 18 omisiones no activan alerta.")
    passed("Exportación completa y trazabilidad", ["RF5"], "CSV con 2 000 filas; UDI, seis entradas, etiqueta posterior, predicción, alerta, resultado y dos tiempos por fila.")
    try:
        simulator.start()
    except ValueError:
        passed("Bloqueo de reproducción al finalizar", ["RF3"], "Se requiere reiniciar antes de una nueva sesión.")
    else:
        raise AssertionError("La sesión completada se reinició implícitamente.")
    simulator.reset()
    assert simulator.snapshot()["last"] is None and simulator.snapshot()["alerts"] == 0
    assert simulator.snapshot()["series"] == []
    empty_export = list(csv.reader(io.StringIO(simulator.export_csv())))
    assert len(empty_export) == 1
    passed("Reinicio sin resultados residuales", ["RF3", "RF5"], "Contadores, último registro y filas exportadas vacíos; encabezado conservado.")

    # Integración HTTP y trabajador real; no se asume que cada tick tarda exactamente lo previsto.
    server = create_server(simulator, ROOT / "web", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    simulator.start_worker()
    address = f"http://127.0.0.1:{server.server_port}"
    http_timings = []

    def request(path, data=None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = Request(address + path, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return response.status, response.read(), response.headers

    try:
        code, html, _ = request("/")
        assert code == 200 and b'lang="es"' in html
        for asset in ("/app.js", "/style.css"):
            assert request(asset)[0] == 200
        request("/api/start", {"interval": 0.2})
        timeout = time.monotonic() + 5
        while simulator.snapshot()["processed"] < 2 and time.monotonic() < timeout:
            time.sleep(0.025)
        assert simulator.snapshot()["processed"] >= 2
        paused = json.loads(request("/api/pause", {})[1])
        time.sleep(0.35)
        assert json.loads(request("/api/state")[1])["processed"] == paused["processed"]
        request("/api/start", {"interval": 0.2})
        timeout = time.monotonic() + 5
        while simulator.snapshot()["processed"] == paused["processed"] and time.monotonic() < timeout:
            time.sleep(0.025)
        resumed = json.loads(request("/api/pause", {})[1])
        assert resumed["processed"] > paused["processed"]
        assert len({row["UDI"] for row in simulator.records}) == len(simulator.records)
        passed("Inicio, pausa y continuación mediante HTTP", ["RF3"], "El trabajador avanzó; la pausa conservó el contador durante 350 ms; continuar no duplicó UDI.")
        request("/api/reset", {})
        for _ in range(20):
            started = time.perf_counter_ns()
            result = json.loads(request("/api/step", {})[1])
            http_timings.append((time.perf_counter_ns() - started) / 1_000_000)
        assert result["processed"] == 20
        code, exported, headers = request("/api/export")
        assert code == 200 and 'attachment;' in headers["Content-Disposition"]
        downloaded_csv = io.StringIO(exported.decode("utf-8-sig"))
        downloaded_rows = list(csv.DictReader(downloaded_csv))
        assert len(downloaded_rows) == 20
        passed("Avance manual y descarga HTTP", ["RF3", "RF5"], "20 pasos generan 20 filas descargables con Content-Disposition de archivo CSV.")
        for path, payload in [("/api/load", {"csv": "columna_incorrecta\n1\n"}),
                              ("/api/start", {"interval": -1}),
                              ("/api/load", {"csv": 12})]:
            try:
                request(path, payload)
            except HTTPError as exc:
                assert exc.code == 400 and json.loads(exc.read())["error"]
            else:
                raise AssertionError("La API aceptó una entrada incorrecta.")
        assert simulator.snapshot()["processed"] == 20
        passed("Mensajes HTTP ante entradas incorrectas", ["RF1"], "CSV inválido, intervalo negativo y cuerpo de carga incorrecto devuelven HTTP 400 con mensaje; conservan 20 registros.")
        request("/api/reset", {})
    finally:
        simulator.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    after = {name: file_sha256(ROOT / name) for name in protected}
    assert before == after
    passed("Modelo y evaluación histórica sin modificaciones", ["RNF1", "RNF2"], "Huellas idénticas antes y después en modelo, selección, evaluación histórica, predicciones, CSV original y reserva.")

    def timing_summary(values):
        return {"observations": len(values), "mean_ms": float(np.mean(values)),
                "median_ms": float(np.median(values)), "p95_ms": float(np.percentile(values, 95))}

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Comprobación funcional de la simulación local, sin entrenamiento ni selección de modelo.",
        "all_checks_passed": True, "checks": cases,
        "confusion_counts": state["counts"], "alerts": state["alerts"],
        "timing": {
            "predict": timing_summary(full["predict_ms"]),
            "processing": timing_summary(full["processing_ms"]),
            "http_step_roundtrip": timing_summary(http_timings),
            "definitions": {
                "predict": "Transformaciones y clasificación de una fila, después de tres calentamientos excluidos.",
                "processing": "Selección, validación y preparación de una fila, predict y construcción del registro. Excluye espera del bloqueo, añadir al historial, CSV, HTTP, pantalla y pausas.",
                "http_step_roundtrip": "20 solicitudes secuenciales locales: petición HTTP, procesamiento, snapshot, JSON y recepción de respuesta. No mide actualización de pantalla ni pausas. Sin objetivo de latencia preestablecido; no se determina cumplimiento de tiempo real.",
            },
        },
        "environment": {"platform": platform.platform(), "processor": platform.processor(),
                        "python": platform.python_version(), "versions": selection["versions"]},
        "protected_file_sha256_before": before, "protected_file_sha256_after": after,
        "limitations": ["Reproducción de una reserva sintética ya evaluada; no es una nueva evaluación independiente.",
                        "Los tiempos dependen del equipo y de la carga; no son garantías industriales.",
                        "La revisión visual y los controles del navegador se documentan por separado; este script no certifica usabilidad con usuarios."]
    }
    (ROOT / "reports/monitor_simulation_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True)
    full.to_csv(output / "simulation_checked_predictions.csv", index=False)
    print(f"Correcto: {len(cases)} comprobaciones. reports/monitor_simulation_checks.json")
    print(json.dumps(report["timing"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
