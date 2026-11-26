"use strict";

const el = id => document.getElementById(id);
const statusNames = {
  ready: "Listo para iniciar",
  running: "Reproduciendo",
  paused: "En pausa",
  completed: "Reproducción completada",
  error: "Reproducción detenida por un error"
};
const outcomes = {
  TN: "Acierto sin falla",
  TP: "Falla detectada",
  FP: "Falsa alarma",
  FN: "Falla omitida"
};

let busy = false;
let lastState = null;
let polling = false;
let actionGeneration = 0;

function showError(message) {
  el("error").textContent = message || "";
  el("error").hidden = !message;
}

function applyControls() {
  const s = lastState;
  if (!s) {
    for (const id of ["start", "pause", "step", "reset", "load"]) el(id).disabled = true;
    return;
  }
  el("start").disabled = busy || ["running", "completed", "error"].includes(s.status);
  el("start").textContent = s.status === "paused" ? "Continuar" : "Iniciar simulación";
  el("pause").disabled = busy || s.status !== "running";
  el("step").disabled = busy || ["running", "completed", "error"].includes(s.status);
  el("reset").disabled = busy;
  el("load").disabled = busy || s.status === "running";
  el("interval").disabled = busy || s.status === "running";
}

function outcomeClass(code) {
  if (code === "TP" || code === "TN") return "is-ok";
  if (code === "FP") return "is-alert";
  if (code === "FN") return "is-miss";
  return "is-neutral";
}

function createBadge(text, tone) {
  const span = document.createElement("span");
  span.className = `status-pill ${tone}`;
  span.textContent = text;
  return span;
}

function render(s) {
  lastState = s;
  el("status").textContent = `${statusNames[s.status]} · ${s.processed} de ${s.total} registros`;
  el("progress").value = s.processed;
  el("progress").max = s.total;

  const pct = el("progress-pct");
  if (pct) {
    const ratio = s.total ? (s.processed / s.total) * 100 : 0;
    pct.textContent = `${ratio.toLocaleString("es-PE", { maximumFractionDigits: 1 })} %`;
  }

  el("alerts").textContent = s.alerts;
  el("latency").textContent = s.predict_mean_ms === null
    ? "— / — ms"
    : `${s.predict_mean_ms.toFixed(2)} / ${s.predict_p95_ms.toFixed(2)} ms`;

  // Actualizar mini-matriz viva del cockpit
  const liveMap = {
    "live-tn": s.counts.TN,
    "live-tp": s.counts.TP,
    "live-fp": s.counts.FP,
    "live-fn": s.counts.FN
  };
  for (const [id, val] of Object.entries(liveMap)) {
    const node = el(id);
    if (node) node.textContent = val;
  }

  const row = s.last;
  el("identity").textContent = row
    ? `UDI ${row.UDI} · Producto tipo ${row.Type}`
    : "Avanza un registro para inspeccionar sus mediciones.";

  const sensorBindings = [
    ["air", "Air temperature [K]", "K"],
    ["process", "Process temperature [K]", "K"],
    ["speed", "Rotational speed [rpm]", "rpm"],
    ["torque", "Torque [Nm]", "Nm"],
    ["wear", "Tool wear [min]", "min"]
  ];
  for (const [id, name, unit] of sensorBindings) {
    el(id).textContent = `${row ? row[name].toLocaleString("es-PE", { maximumFractionDigits: 2 }) : "—"} ${unit}`;
  }

  el("prediction").textContent = row
    ? (row.alert ? "⚠ Alerta: con falla" : "✓ Sin falla detectada")
    : "Sin predicción";
  el("prediction").className = `prediction ${row ? (row.alert ? "alert" : "normal") : "neutral"}`;
  el("reference").textContent = row
    ? `Etiqueta real: ${row["Machine failure"] ? "con falla" : "sin falla"} · ${outcomes[row.outcome]}`
    : "Etiqueta real: —";

  const body = el("history");
  body.replaceChildren();
  if (!s.recent.length) {
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.textContent = "Todavía no hay registros procesados.";
    const tr = document.createElement("tr");
    tr.append(cell);
    body.append(tr);
  }

  for (const item of s.recent) {
    const tr = document.createElement("tr");
    const cells = [
      item.UDI,
      item.Type,
      item.prediction ? "Con falla" : "Sin falla",
      item["Machine failure"] ? "Con falla" : "Sin falla",
      outcomes[item.outcome],
      item.predict_ms.toFixed(2)
    ];
    for (const [i, value] of cells.entries()) {
      const td = document.createElement("td");
      if (i === 2) {
        td.dataset.alert = String(item.alert);
        td.append(createBadge(value, item.alert ? "is-alert" : "is-neutral"));
      } else if (i === 4) {
        td.append(createBadge(value, outcomeClass(item.outcome)));
      } else {
        td.textContent = value;
      }
      tr.append(td);
    }
    body.append(tr);
  }

  el("counts").textContent =
    `Aciertos sin falla: ${s.counts.TN} · Fallas detectadas: ${s.counts.TP} · Falsas alarmas: ${s.counts.FP} · Fallas omitidas: ${s.counts.FN}`;
  if (s.error) showError(s.error);
  applyControls();
  window.dispatchEvent(new CustomEvent("simulation-state", { detail: s }));
}

async function request(path, data) {
  const response = await fetch(
    path,
    data === undefined
      ? {}
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "No se pudo completar la solicitud.");
  return result;
}

async function action(path, data = {}) {
  if (busy) return;
  busy = true;
  actionGeneration++;
  showError("");
  applyControls();
  try {
    const state = await request(path, data);
    render(state);
    return true;
  } catch (error) {
    showError(error.message);
    return false;
  } finally {
    busy = false;
    applyControls();
  }
}

el("start").addEventListener("click", () => action("/api/start", { interval: Number(el("interval").value) }));
el("pause").addEventListener("click", () => action("/api/pause"));
el("step").addEventListener("click", () => action("/api/step"));
el("reset").addEventListener("click", () => {
  el("load-message").textContent = "";
  action("/api/reset");
});

el("load").addEventListener("click", async () => {
  const file = el("csv").files[0];
  el("load-message").textContent = "";
  if (!file) {
    showError("Selecciona un archivo CSV de prueba.");
    return;
  }
  if (file.size > 1_000_000) {
    showError("El archivo supera el límite de 1 MB.");
    return;
  }
  try {
    if (await action("/api/load", { csv: await file.text() })) {
      el("load-message").textContent = "CSV válido. Reserva verificada y sesión reiniciada.";
    }
  } catch (error) {
    showError(`No se pudo leer el archivo: ${error.message}`);
  }
});

async function poll() {
  if (polling || busy) return;
  polling = true;
  const generation = actionGeneration;
  try {
    const state = await request("/api/state");
    if (!busy && generation === actionGeneration) render(state);
  } catch (error) {
    if (!busy && generation === actionGeneration) {
      showError(
        error instanceof TypeError
          ? "No hay conexión con el servidor. Espera un momento y comprueba tu conexión; si usas la versión local, revisa su terminal."
          : error.message
      );
      lastState = null;
      applyControls();
    }
  } finally {
    polling = false;
  }
}

applyControls();
poll();
setInterval(poll, 300);
