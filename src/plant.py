"""Taller simulado: 12 fresadoras CNC que evolucionan en el tiempo y que la IA vigila.

IMPORTANTE (honestidad del experimento):
- Es un mundo SINTÉTICO. Las lecturas se generan con una dinámica sencilla y las fallas ocurren cuando se
  incumple alguna de las reglas físicas documentadas del dataset AI4I 2020 (calor, potencia, sobretensión,
  desgaste). Esas reglas coinciden al 100 % con las columnas HDF, PWF y OSF del dataset.
- El modelo NO conoce estas reglas: las aprendió de los datos. Aquí solo se compara lo que dice con lo que pasa.
- El árbol clasifica cada lectura por separado (detecta una condición de falla). El pronosticador (src/forecast.py)
  mira la tendencia reciente y estima si la máquina fallará en los próximos pasos; se entrenó con otras semillas.
"""
import threading
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src import forecast as fcst
from src.autoencoder import describe as describe_ae, reconstruction_error
from src.preparation import FEATURES

N_MACHINES = 12
DEFAULT_SEED = 12  # historia reproducible para ensayar la presentación
HISTORY, SPARK, DOWN_TICKS, WINDOW, AE_WINDOW = 150, 40, 10, 6, 10
LIMITS = {"power_low": 3500.0, "power_high": 9000.0, "delta_t": 8.6, "rpm": 1380.0,
          "strain": {"L": 11000.0, "M": 12000.0, "H": 13000.0}, "twf": (200.0, 240.0)}
CONTROL_RANGES = {"rpm": (1100.0, 2900.0), "power": (1500.0, 11500.0), "cool": (6.0, 12.0)}
CAUSES = {"OSF": "Sobretensión (desgaste × torque)", "PWF": "Potencia fuera de rango", "HDF": "Disipación de calor insuficiente",
          "TWF": "Herramienta desgastada"}
PROFILES = {
    "saludable": "Opera con normalidad",
    "desgaste": "Herramienta muy usada",
    "sobrecarga": "Demanda de potencia que sube poco a poco",
    "refrigeracion": "Refrigeración que se degrada",
    "baja_potencia": "Demanda de potencia que cae",
}
START_MIX = ["saludable"] * 7 + ["desgaste"] + ["sobrecarga"] * 2 + ["refrigeracion", "baja_potencia"]
RESTART_MIX = ["saludable"] * 5 + ["desgaste", "sobrecarga", "sobrecarga", "refrigeracion", "baja_potencia"]


@lru_cache(maxsize=1)
def forecaster():
    """Pronosticador verificado (None si el experimento no lo incluye)."""
    return fcst.load_forecast(Path(__file__).resolve().parents[1])


def power_w(torque, rpm):
    return torque * rpm * 2 * np.pi / 60


class Plant:
    def __init__(self, simulator, seed=DEFAULT_SEED):
        self.sim = simulator
        self.lock = threading.Lock()
        self.reset(seed)

    # ------------------------------------------------------------------ creación
    def reset(self, seed=None):
        with self.lock:
            self.seed = int(seed) if seed is not None else int(np.random.SeedSequence().entropy % 2**31)
            self.rng = np.random.default_rng(self.seed)
            self.t = 0
            profiles = list(self.rng.permutation(START_MIX))
            self.machines = [self._new_machine(i, profiles[i]) for i in range(N_MACHINES)]
            self.stats = {"failures": 0, "detected": 0, "missed": 0, "false_alarms": 0, "ae_detected": 0, "ae_flags": 0, "leads": [], "ae_leads": [],
                          "fc_warned": 0, "fc_missed": 0, "fc_false": 0, "averted": 0, "fc_leads": []}
            self.log = deque(maxlen=14)
            self._read_all()
            self._infer()
            self._forecast(self.machines, append=False)
            return self._export(0)

    def _new_machine(self, i, profile, keep=None):
        r = self.rng
        kind = keep["type"] if keep else str(r.choice(["L", "L", "L", "M", "M", "H"]))
        p = {
            "saludable": dict(rpm=r.uniform(1400, 1750), power=r.uniform(5000, 7200), cool=r.uniform(9.8, 10.4), wear=r.uniform(0, 70)),
            "desgaste": dict(rpm=r.uniform(1450, 1700), power=r.uniform(5000, 6500), cool=r.uniform(9.9, 10.3), wear=r.uniform(150, 185)),
            "sobrecarga": dict(rpm=r.uniform(1500, 1700), power=r.uniform(5400, 6400), cool=r.uniform(9.8, 10.3), wear=r.uniform(30, 100)),
            "refrigeracion": dict(rpm=r.uniform(1250, 1340), power=r.uniform(5000, 6500), cool=r.uniform(10.2, 10.5), wear=r.uniform(20, 90)),
            "baja_potencia": dict(rpm=r.uniform(1250, 1350), power=r.uniform(4700, 5200), cool=r.uniform(9.9, 10.3), wear=r.uniform(20, 90)),
        }[profile]
        return {
            "id": i, "name": f"Fresadora {i + 1:02d}", "type": kind, "profile": profile, "status": "run", "down_left": 0, "cause": None,
            "air_base": float(r.uniform(298.0, 301.5)), "phase": float(r.uniform(0, 6.28)),
            "rpm_set": float(p["rpm"]), "power_set": float(p["power"]), "cool_set": float(p["cool"]), "wear": float(p["wear"]),
            "twf_limit": float(r.uniform(*LIMITS["twf"])),
            "drift": float({"sobrecarga": r.uniform(30, 60), "refrigeracion": r.uniform(0.022, 0.034),
                            "baja_potencia": r.uniform(22, 38)}.get(profile, 0.0)),
            "alert_ticks": deque(maxlen=WINDOW), "ae_ticks": deque(maxlen=AE_WINDOW), "run_start": None,
            "reading": None, "risk": 0.0, "alert": False, "ae_error": 0.0, "ae_alert": False, "leaf": None, "path": [],
            "leaf_n": 0, "leaf_fail": 0, "fail_now": False, "ticks": 0,
            "fc": 0.0, "fc_alert": False, "fc_x": None, "fc_ticks": deque(), "fc_start": None, "op_tick": None, "fail_note": None,
            "hist": {k: deque(maxlen=HISTORY) for k in ("torque", "rpm", "wear", "power", "dt", "risk", "ae", "alert", "fail", "fc")},
        }

    # ------------------------------------------------------------------ dinámica
    def _read_all(self):
        for m in self.machines:
            if m["status"] == "run":
                self._read(m, advance=True)

    def _read(self, m, advance):
        """Genera la lectura de una máquina; con advance=False no mueve el desgaste ni la deriva (efecto inmediato del operador)."""
        r = self.rng
        if advance:
            if m["profile"] == "sobrecarga":
                m["power_set"] = min(CONTROL_RANGES["power"][1] - 1, m["power_set"] + m["drift"])
            elif m["profile"] == "refrigeracion":
                m["cool_set"] = max(CONTROL_RANGES["cool"][0], m["cool_set"] - m["drift"])
            elif m["profile"] == "baja_potencia":
                m["power_set"] = max(CONTROL_RANGES["power"][0], m["power_set"] - m["drift"])
            m["wear"] = min(253.0, m["wear"] + float(r.uniform(0.8, 1.2)) * (0.6 + 0.4 * m["power_set"] / 6400))
        air = m["air_base"] + 0.8 * np.sin(self.t / 40 + m["phase"]) + r.normal(0, 0.12)
        proc = air + m["cool_set"] + r.normal(0, 0.18)
        rpm = m["rpm_set"] + r.normal(0, 18)
        # La potencia demandada y la velocidad fijan el torque (como en los datos reales, donde rpm y torque van en sentido contrario).
        torque = float(np.clip(m["power_set"] / (rpm * 2 * np.pi / 60) + r.normal(0, 1.2), 3, 77))
        m["reading"] = {"Type": m["type"], "Air temperature [K]": float(air), "Process temperature [K]": float(proc),
                        "Rotational speed [rpm]": float(rpm), "Torque [Nm]": torque, "Tool wear [min]": float(m["wear"])}
        m["fail_now"], m["cause_now"] = self._physics(m)

    @staticmethod
    def _physics(m):
        x = m["reading"]
        p = power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"])
        dt = x["Process temperature [K]"] - x["Air temperature [K]"]
        strain = x["Tool wear [min]"] * x["Torque [Nm]"]
        if strain > LIMITS["strain"][m["type"]]:
            return True, "OSF"
        if p < LIMITS["power_low"] or p > LIMITS["power_high"]:
            return True, "PWF"
        if dt < LIMITS["delta_t"] and x["Rotational speed [rpm]"] < LIMITS["rpm"]:
            return True, "HDF"
        if x["Tool wear [min]"] >= m["twf_limit"]:
            return True, "TWF"
        return False, None

    def _infer(self):
        """El modelo y el autoencoder evalúan, por separado, la lectura actual de cada máquina en marcha."""
        running = [m for m in self.machines if m["status"] == "run" and m["reading"]]
        if not running:
            return
        X = pd.DataFrame([m["reading"] for m in running])[FEATURES]
        Z = self.sim._pre.transform(X)
        tree = self.sim._tree
        pred = tree.predict(Z)
        paths = tree.decision_path(Z)
        errors = reconstruction_error(self.sim.ae, Z) if self.sim.ae else np.zeros(len(running))
        t = tree.tree_
        for k, m in enumerate(running):
            path = [int(i) for i in paths.indices[paths.indptr[k]:paths.indptr[k + 1]]]
            leaf = path[-1]
            n = float(t.weighted_n_node_samples[leaf]); p_fail = float(t.value[leaf, 0, 1])
            m.update(path=path, leaf=leaf, leaf_n=int(round(n)), leaf_fail=int(round(p_fail * n)), risk=p_fail, alert=bool(pred[k] == 1),
                     ae_error=float(errors[k]), ae_alert=bool(self.sim.ae and errors[k] > self.sim.ae["threshold"]))

    def _account(self, m):
        """Compara, por evento, lo que dijo la IA con lo que ocurrió en la planta."""
        s, t = self.stats, self.t
        if m["ae_alert"]:
            m["ae_ticks"].append(t); s["ae_flags"] += 1
        if m["alert"]:
            m["alert_ticks"].append(t)
            if m["run_start"] is None:
                m["run_start"] = t
                if not m["fail_now"]:
                    self._note(m, "info", f"El detector marcó condición de falla en {m['name']}.")
        elif m["run_start"] is not None and not m["fail_now"]:
            s["false_alarms"] += 1; m["run_start"] = None
        if m["fail_now"]:
            s["failures"] += 1
            recent = [x for x in m["alert_ticks"] if t - x <= WINDOW]
            ae_recent = [x for x in m["ae_ticks"] if t - x <= AE_WINDOW]
            if ae_recent:
                s["ae_detected"] += 1; s["ae_leads"].append(t - min(ae_recent))
            cause = CAUSES[m["cause_now"]]
            if recent:
                lead = t - min(recent); s["detected"] += 1; s["leads"].append(lead)
                when = "en el mismo instante" if lead == 0 else f"{lead} {'paso' if lead == 1 else 'pasos'} antes"
                m["fail_note"] = ("fallo", f"{m['name']} falló: {cause}. El detector lo marcó {when}.")
            else:
                s["missed"] += 1
                m["fail_note"] = ("omitida", f"{m['name']} falló: {cause}. El detector NO lo marcó.")
            m["alert_ticks"].clear(); m["ae_ticks"].clear(); m["run_start"] = None

    def _note(self, m, kind, text):
        self.log.appendleft({"t": self.t, "machine": m["id"], "kind": kind, "text": text})

    def tick(self, sel=0):
        with self.lock:
            self.t += 1
            for m in self.machines:
                if m["status"] == "down":
                    m["down_left"] -= 1
                    if m["down_left"] <= 0:
                        profile = str(self.rng.choice(RESTART_MIX))
                        fresh = self._new_machine(m["id"], profile, keep=m)
                        fresh["hist"] = m["hist"]
                        self.machines[m["id"]] = fresh
                        self._note(fresh, "reparada", f"{fresh['name']} reparada: herramienta nueva y ajustes restablecidos.")
            self._read_all()
            self._infer()
            recorded = []
            for m in self.machines:
                if m["status"] != "run":
                    continue
                m["ticks"] += 1
                self._account(m)
                self._record(m)
                recorded.append(m)
            self._forecast(recorded, append=True)
            for m in recorded:
                self._account_forecast(m)
                if m["fail_now"]:
                    m["status"], m["down_left"], m["cause"] = "down", DOWN_TICKS, m["cause_now"]
            return self._export(sel)

    # ------------------------------------------------------------------ pronóstico
    def _series(self, m):
        """Últimas lecturas de ESTA máquina (la historia se hereda en los reinicios, por eso se acota con ticks)."""
        n = min(fcst.WINDOW, m["ticks"])
        if n == 0:
            x = m["reading"]
            return {"power": [power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"])], "dt": [x["Process temperature [K]"] - x["Air temperature [K]"]],
                    "wear": [x["Tool wear [min]"]], "rpm": [x["Rotational speed [rpm]"]], "torque": [x["Torque [Nm]"]]}
        return {k: list(m["hist"][k])[-n:] for k in ("power", "dt", "wear", "rpm", "torque")}

    def _forecast(self, machines, append):
        """Probabilidad de falla en los próximos pasos, por máquina (un solo lote)."""
        bundle = forecaster()
        machines = [m for m in machines if m["reading"]]
        if not bundle or not machines:
            for m in machines:
                if append:
                    m["hist"]["fc"].append(0.0)
            return
        X = np.array([fcst.window_features(self._series(m), m["type"]) for m in machines])
        p = fcst.proba(bundle, X)
        for m, x, v in zip(machines, X, p):
            m.update(fc=float(v), fc_alert=bool(v >= bundle["threshold"]), fc_x=x)
            if append:
                m["hist"]["fc"].append(round(float(v), 3))

    def _account_forecast(self, m):
        """Compara el pronóstico con lo que ocurrió: fallas anticipadas, omitidas, falsas alarmas y fallas evitadas."""
        bundle = forecaster()
        s, t, H = self.stats, self.t, fcst.HORIZON
        if not bundle:
            if m["fail_note"]:
                kind, text = m["fail_note"]; self._note(m, kind, text); m["fail_note"] = None
            return
        if m["fail_now"]:
            prior = [x for x in m["fc_ticks"] if 0 < t - x <= H]
            if prior:
                lead = t - min(prior); s["fc_warned"] += 1; s["fc_leads"].append(lead)
                extra = f" El pronóstico lo había anticipado {lead} {'paso' if lead == 1 else 'pasos'} antes."
            else:
                s["fc_missed"] += 1; extra = " El pronóstico no lo anticipó."
            kind, text = m["fail_note"] or ("fallo", f"{m['name']} falló.")
            self._note(m, kind, text + extra); m["fail_note"] = None
            m["fc_ticks"].clear(); m["fc_start"] = None
            return
        if m["fc_alert"]:
            m["fc_ticks"].append(t)
            if m["fc_start"] is None:
                m["fc_start"] = t
                self._note(m, "alerta", f"Pronóstico: {m['name']} probablemente falle en los próximos {H} pasos ({m['fc'] * 100:.0f} %).")
        elif m["fc_start"] is not None:
            if m["op_tick"] is not None and m["op_tick"] >= m["fc_start"] - 1:
                s["averted"] += 1
                self._note(m, "evitada", f"Falla evitada: el operador corrigió {m['name']} a tiempo.")
            else:
                s["fc_false"] += 1
                self._note(m, "info", f"El aviso de {m['name']} se apagó sin que hubiera falla (falsa alarma).")
            m["fc_start"] = None; m["fc_ticks"].clear()

    def _record(self, m):
        x, h = m["reading"], m["hist"]
        h["torque"].append(x["Torque [Nm]"]); h["rpm"].append(x["Rotational speed [rpm]"]); h["wear"].append(x["Tool wear [min]"])
        h["power"].append(power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"]))
        h["dt"].append(x["Process temperature [K]"] - x["Air temperature [K]"])
        h["risk"].append(m["risk"]); h["ae"].append(m["ae_error"]); h["alert"].append(int(m["alert"])); h["fail"].append(int(m["fail_now"]))

    # ------------------------------------------------------------------ operador
    def control(self, data, sel=0):
        with self.lock:
            if not isinstance(data, dict) or not isinstance(data.get("id"), int) or not 0 <= data["id"] < N_MACHINES:
                raise ValueError("Máquina no válida.")
            m = self.machines[data["id"]]
            action = data.get("action")
            if action is not None:
                if action == "tool" and m["status"] == "run":
                    m["wear"] = 0.0; m["twf_limit"] = float(self.rng.uniform(*LIMITS["twf"]))
                    self._note(m, "info", f"Operador: herramienta nueva en {m['name']}.")
                elif action == "stabilize" and m["status"] == "run":
                    m.update(profile="saludable", drift=0.0, rpm_set=1550.0, power_set=6000.0, cool_set=10.0)
                    self._note(m, "info", f"Operador: {m['name']} vuelve a parámetros seguros.")
                elif action == "restart" and m["status"] == "down":
                    m["down_left"] = 1
                else:
                    raise ValueError("Acción no disponible para el estado de la máquina.")
            for key, name in (("rpm", "rpm_set"), ("power", "power_set"), ("cool", "cool_set")):
                if key in data:
                    value, (low, high) = data[key], CONTROL_RANGES[key]
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or not low <= value <= high:
                        raise ValueError(f"{key} debe estar entre {low:g} y {high:g}.")
                    m[name] = float(value)
                    if m["profile"] != "saludable":
                        m["profile"], m["drift"] = "saludable", 0.0  # el operador toma el control
            if m["status"] == "run" and any(k in data for k in ("rpm", "power", "cool", "action")):
                # La lectura se recalcula en el acto con la nueva configuración, para que el efecto se vea de inmediato.
                m["op_tick"] = self.t
                self._read(m, advance=False); self._infer(); self._record_replace(m)
                self._forecast([m], append=False)
                m["hist"]["fc"].append(round(m["fc"], 3))  # _record_replace ya retiró el valor anterior
            return self._export(sel)

    def _record_replace(self, m):
        for k in m["hist"].values():
            if k:
                k.pop()
        self._record(m)

    # ------------------------------------------------------------------ asistente
    def advise(self, idx):
        """Prueba acciones del operador con el pronosticador y las ordena por riesgo resultante."""
        bundle = forecaster()
        with self.lock:
            if not isinstance(idx, int) or not 0 <= idx < N_MACHINES:
                raise ValueError("Máquina no válida.")
            m = self.machines[idx]
            x = m["reading"]
            info = {"id": idx, "name": m["name"], "status": m["status"], "type": m["type"], "cause": m["cause"], "cause_text": CAUSES.get(m["cause"]),
                    "down_left": m["down_left"], "p_now": m["fc"], "reading": None, "why": [], "p_idle": None, "actions": [], "forecast": bool(bundle),
                    "setpoints": {"rpm": m["rpm_set"], "power": m["power_set"], "cool": m["cool_set"]}, "profile": m["profile"], "ticks": m["ticks"]}
            if x:
                info["reading"] = {"power": power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"]), "rpm": x["Rotational speed [rpm]"],
                                   "dt": x["Process temperature [K]"] - x["Air temperature [K]"], "wear": x["Tool wear [min]"], "torque": x["Torque [Nm]"]}
                info["rules_bad"] = [r["id"] for r in self._rules(m) if r["bad"]]
            if not bundle or m["status"] != "run" or not x:
                return info
            info["why"] = fcst.explain(bundle, m["fc_x"]) if m["fc_x"] is not None else []
            base = self._series(m)
            keep = max(0, fcst.WINDOW - 5)

            def risk(changes):
                fut = _ahead(m, changes, self.t)
                series = {k: (list(base[k])[-keep:] if keep else []) + fut[k] for k in fut}
                p = float(fcst.proba(bundle, fcst.window_features(series, m["type"]))[0])
                last = {k: v[-1] for k, v in fut.items()}
                strain = last["wear"] * last["torque"]
                bad = (strain > LIMITS["strain"][m["type"]] or not LIMITS["power_low"] <= last["power"] <= LIMITS["power_high"]
                       or (last["dt"] < LIMITS["delta_t"] and last["rpm"] < LIMITS["rpm"]) or last["wear"] >= m["twf_limit"])
                return p, last, bad

            info["p_idle"], _, info["idle_bad"] = risk({})
            sp, lo, hi = info["setpoints"], CONTROL_RANGES, CONTROL_RANGES
            cands = [
                ("Parámetros seguros (1 550 rpm, 6 000 W, refrigeración normal)", {"action": "stabilize"}, {"action": "stabilize"}),
                ("Cambiar la herramienta", {"action": "tool"}, {"action": "tool"}),
                ("Bajar la demanda de potencia un 15 %", {"power": sp["power"] * .85}, None),
                ("Bajar la demanda de potencia un 30 %", {"power": sp["power"] * .70}, None),
                ("Subir la demanda de potencia un 20 %", {"power": sp["power"] * 1.2}, None),
                ("Subir la velocidad del husillo +150 rpm", {"rpm": sp["rpm"] + 150}, None),
                ("Bajar la velocidad del husillo −150 rpm", {"rpm": sp["rpm"] - 150}, None),
                ("Subir la diferencia de temperatura proceso–aire +0,8 K", {"cool": sp["cool"] + .8}, None),
            ]
            seen = []
            for label, change, apply in cands:
                ok = True
                for key, rng_ in (("rpm", lo["rpm"]), ("power", lo["power"]), ("cool", lo["cool"])):
                    if key in change:
                        if not rng_[0] <= change[key] <= rng_[1]:
                            ok = False
                        else:
                            change[key] = float(round(change[key], 1 if key == "cool" else 0))
                if not ok:
                    continue
                p, last, bad = risk(change)
                seen.append({"label": label, "p": p, "delta": p - info["p_idle"], "safe": not bad, "apply": apply or dict(change),
                             "after": {"power": last["power"], "rpm": last["rpm"], "dt": last["dt"], "wear": last["wear"]}})
            seen.sort(key=lambda a: (a["p"], not a["safe"]))
            info["actions"] = seen
            return info

    # ------------------------------------------------------------------ exportación
    def _rules(self, m):
        x = m["reading"]
        if not x:
            return []
        p = power_w(x["Torque [Nm]"], x["Rotational speed [rpm]"])
        dt = x["Process temperature [K]"] - x["Air temperature [K]"]
        strain = x["Tool wear [min]"] * x["Torque [Nm]"]
        lim = LIMITS["strain"][m["type"]]
        return [
            {"id": "PWF", "label": "Potencia", "unit": "W", "value": p, "min": 0, "max": 11000, "safe": [3500, 9000],
             "bad": p < 3500 or p > 9000, "rule": "Segura entre 3 500 y 9 000 W"},
            {"id": "HDF", "label": "Diferencia de temperatura", "unit": "K", "value": dt, "min": 7, "max": 13, "safe": [8.6, 13],
             "bad": dt < 8.6 and x["Rotational speed [rpm]"] < 1380, "rule": "Falla si es < 8,6 K y la velocidad < 1 380 rpm"},
            {"id": "OSF", "label": "Desgaste × torque", "unit": "min·Nm", "value": strain, "min": 0, "max": 15000, "safe": [0, lim],
             "bad": strain > lim, "rule": f"Falla por encima de {lim:,.0f} (tipo {m['type']})".replace(",", " ")},
            {"id": "TWF", "label": "Desgaste de herramienta", "unit": "min", "value": x["Tool wear [min]"], "min": 0, "max": 260,
             "safe": [0, 200], "bad": x["Tool wear [min]"] >= m["twf_limit"], "rule": "Zona de falla aleatoria entre 200 y 240 min"},
        ]

    def _card(self, m, spark=True):
        x = m["reading"] or {}
        card = {
            "id": m["id"], "name": m["name"], "type": m["type"], "status": m["status"], "cause": m["cause"],
            "cause_text": CAUSES.get(m["cause"]), "profile": m["profile"], "profile_text": PROFILES[m["profile"]],
            "risk": m["risk"], "alert": m["alert"], "fc": m["fc"], "fc_alert": m["fc_alert"], "ae_error": m["ae_error"], "ae_alert": m["ae_alert"],
            "rpm": x.get("Rotational speed [rpm]"), "torque": x.get("Torque [Nm]"), "wear": x.get("Tool wear [min]"),
            "down_left": m["down_left"], "setpoints": {"rpm": m["rpm_set"], "power": m["power_set"], "cool": m["cool_set"]},
        }
        if spark:
            card["spark"] = [round(v, 3) for v in list(m["hist"]["fc"])[-SPARK:]]
        return card

    def _export(self, sel):
        sel = sel if isinstance(sel, int) and 0 <= sel < N_MACHINES else 0
        s = self.stats
        m = self.machines[sel]
        detail = self._card(m, spark=False)
        bundle = forecaster()
        detail.update({
            "forecast": ({"p": m["fc"], "alert": m["fc_alert"], "threshold": bundle["threshold"], "horizon": fcst.HORIZON,
                          "why": fcst.explain(bundle, m["fc_x"]) if m["fc_x"] is not None else []} if bundle else None),
            "reading": m["reading"], "path": m["path"], "leaf": m["leaf"], "leaf_n": m["leaf_n"], "leaf_fail": m["leaf_fail"],
            "p_fail": m["risk"], "rules": self._rules(m), "twf_limit": m["twf_limit"],
            "history": {k: [round(float(v), 3) for v in vals] for k, vals in m["hist"].items()},
            "ae": describe_ae(self.sim.ae, self.sim._pre.transform(pd.DataFrame([m["reading"]])[FEATURES])) if self.sim.ae and m["reading"] else None,
        })
        counts = {"run": 0, "alert": 0, "down": 0}
        for k in self.machines:
            counts["down" if k["status"] == "down" else "alert" if (k["alert"] or k["fc_alert"]) else "run"] += 1
        return {
            "t": self.t, "seed": self.seed, "machines": [self._card(k) for k in self.machines], "selected": detail, "counts": counts,
            "forecast": self._forecast_info(),
            "stats": {**{k: v for k, v in s.items() if k not in ("leads", "ae_leads", "fc_leads")},
                      "mean_fc_lead": float(np.mean(s["fc_leads"])) if s["fc_leads"] else None,
                      "mean_lead": float(np.mean(s["leads"])) if s["leads"] else None,
                      "mean_ae_lead": float(np.mean(s["ae_leads"])) if s["ae_leads"] else None},
            "log": list(self.log),
        }

    @staticmethod
    def _forecast_info():
        b = forecaster()
        if not b:
            return None
        ev = (b["info"].get("evaluation") or {})
        fe, nt = ev.get("forecast_events") or {}, (ev.get("without_trend") or {}).get("events") or {}
        return {"horizon": fcst.HORIZON, "window": fcst.WINDOW, "threshold": b["threshold"],
                "test": {"recall": fe.get("recall_events"), "median_lead": fe.get("median_lead"), "mean_lead": fe.get("mean_lead"),
                         "false_per_1000": fe.get("false_runs_per_1000_ticks"), "flat_false_per_1000": nt.get("false_runs_per_1000_ticks"),
                         "flat_recall": nt.get("recall_events"), "failures": fe.get("failures"), "by_cause": fe.get("by_cause")}}

    def snapshot(self, sel=0):
        with self.lock:
            return self._export(sel)


def _ahead(m, changes, t0, steps=5):
    """Proyecta `steps` pasos de una máquina SIN ruido bajo unos cambios del operador y devuelve las lecturas (para el pronosticador)."""
    st = {"rpm": m["rpm_set"], "power": m["power_set"], "cool": m["cool_set"], "wear": m["wear"], "profile": m["profile"], "drift": m["drift"]}
    if changes.get("action") == "tool":
        st["wear"] = 0.0
    if changes.get("action") == "stabilize":
        st.update(profile="saludable", drift=0.0, rpm=1550.0, power=6000.0, cool=10.0)
    for key in ("rpm", "power", "cool"):
        if key in changes:
            st[key] = float(changes[key]); st["profile"], st["drift"] = "saludable", 0.0
    out = {k: [] for k in ("power", "dt", "wear", "rpm", "torque")}
    for k in range(1, steps + 1):
        if st["profile"] == "sobrecarga":
            st["power"] = min(CONTROL_RANGES["power"][1] - 1, st["power"] + st["drift"])
        elif st["profile"] == "refrigeracion":
            st["cool"] = max(CONTROL_RANGES["cool"][0], st["cool"] - st["drift"])
        elif st["profile"] == "baja_potencia":
            st["power"] = max(CONTROL_RANGES["power"][0], st["power"] - st["drift"])
        st["wear"] = min(253.0, st["wear"] + (0.6 + 0.4 * st["power"] / 6400))
        air = m["air_base"] + 0.8 * np.sin((t0 + k) / 40 + m["phase"])
        rpm = st["rpm"]
        torque = float(np.clip(st["power"] / (rpm * 2 * np.pi / 60), 3, 77))
        out["power"].append(power_w(torque, rpm)); out["dt"].append(st["cool"]); out["wear"].append(st["wear"])
        out["rpm"].append(rpm); out["torque"].append(torque)
    return out


def plant_dispatch(sim, name, data):
    """Punto único de entrada para la API (servidor web y servidor local)."""
    if not isinstance(data, dict):
        raise ValueError("La solicitud debe ser un objeto JSON.")
    sel = data.get("sel", 0)
    plant = sim.plant
    if name == "state":
        return plant.snapshot(sel)
    if name == "tick":
        return plant.tick(sel)
    if name == "control":
        return plant.control(data, sel)
    if name == "assistant":
        from src.assistant import reply
        return reply(plant, data)
    if name == "reset":
        seed = data.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31):
            raise ValueError("La semilla debe ser un entero entre 0 y 2 147 483 647.")
        plant.reset(seed)
        return plant.snapshot(sel)
    raise ValueError("Acción de planta no disponible.")
