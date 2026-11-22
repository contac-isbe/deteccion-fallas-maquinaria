"use strict";

const monitorUnits = {
  "Rotational speed [rpm]": "rpm",
  "Torque [Nm]": "Nm",
  "Air temperature [K]": "K",
  "Process temperature [K]": "K",
  "Tool wear [min]": "min"
};

// Rangos físicos reales del dataset AI4I 2020 para normalizar barras de instrumentos
const sensorBounds = {
  "Air temperature [K]": { min: 295.3, max: 304.5, gaugeId: "gauge-air" },
  "Process temperature [K]": { min: 305.7, max: 313.8, gaugeId: "gauge-process" },
  "Rotational speed [rpm]": { min: 1168, max: 2886, gaugeId: "gauge-speed" },
  "Torque [Nm]": { min: 3.8, max: 76.6, gaugeId: "gauge-torque" },
  "Tool wear [min]": { min: 0, max: 253, gaugeId: "gauge-wear" }
};

const outcomeLabels = {
  TN: "Acierto sin falla",
  TP: "Falla detectada",
  FP: "Falsa alarma",
  FN: "Falla omitida"
};

const machineStateLabels = {
  ready: "EN ESPERA",
  running: "MECANIZANDO",
  paused: "EN PAUSA",
  completed: "COMPLETADO",
  error: "DETENIDO"
};

let chartFeature = "Rotational speed [rpm]";
let monitorState = null;
let lastDrawKey = "";
let activeChartPoints = [];
let activeChartRows = [];
let activeChartGeo = null;

const svgNS = "http://www.w3.org/2000/svg";

function cssVar(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function svgElement(tag, attrs = {}, text) {
  const node = document.createElementNS(svgNS, tag);
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function numberLabel(value) {
  return Number(value).toLocaleString("es-PE", { maximumFractionDigits: 1 });
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function coordinates(rows, feature, width, height, padLeft, padRight, padY) {
  const values = rows.map(row => row[feature]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const margin = Math.max((max - min) * 0.14, Math.abs(max) * 0.015, 0.1);
  min -= margin;
  max += margin;
  const spanX = Math.max(width - padLeft - padRight, 1);
  const spanY = Math.max(height - 2 * padY, 1);
  return {
    min,
    max,
    points: values.map((v, i) => ({
      x: rows.length === 1 ? padLeft + spanX / 2 : padLeft + (i * spanX) / (rows.length - 1),
      y: height - padY - ((v - min) * spanY) / (max - min),
      value: v
    }))
  };
}

function hideTooltip() {
  const tip = document.getElementById("trace-tooltip");
  if (tip) tip.hidden = true;
  const guide = document.getElementById("trace-guide");
  if (guide) guide.setAttribute("opacity", "0");
  const focusDot = document.getElementById("trace-focus-dot");
  if (focusDot) focusDot.setAttribute("opacity", "0");
}

function drawCharts(state) {
  const rows = state.series || [];
  const chart = document.getElementById("trace");
  chart.replaceChildren();
  hideTooltip();

  const width = Math.max(chart.clientWidth || 760, 300);
  const height = 220;
  const padLeft = 64;
  const padRight = 20;
  const padY = 24;
  chart.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const lineColor = cssVar("--chart-line", "#0b6e7c");
  const fillColor = cssVar("--chart-fill", "#0b6e7c");
  const gridColor = cssVar("--chart-grid", "#dce4ec");
  const alertColor = cssVar("--chart-alert", "#cf5216");
  const surfaceColor = cssVar("--surface-solid", "#ffffff");
  const sparkColor = cssVar("--spark-line", "#128394");

  document.getElementById("chart-empty").hidden = rows.length > 0;
  const featureUnit = monitorUnits[chartFeature];
  document.getElementById("chart-current").textContent = rows.length
    ? `${numberLabel(rows.at(-1)[chartFeature])} ${featureUnit}`
    : `— ${featureUnit}`;

  const scale = rows.length ? coordinates(rows, chartFeature, width, height, padLeft, padRight, padY) : null;

  for (let i = 0; i < 4; i++) {
    const y = padY + (i * (height - 2 * padY)) / 3;
    chart.append(
      svgElement("line", {
        x1: padLeft,
        x2: width - padRight,
        y1: y,
        y2: y,
        stroke: gridColor,
        "stroke-dasharray": "4 5"
      })
    );
    if (scale) {
      chart.append(
        svgElement(
          "text",
          { x: padLeft - 10, y: y + 4, "text-anchor": "end", class: "chart-axis" },
          numberLabel(scale.max - (i * (scale.max - scale.min)) / 3)
        )
      );
    }
  }

  activeChartRows = rows;
  activeChartPoints = scale ? scale.points : [];
  activeChartGeo = { width, height, padLeft, padRight, padY, lineColor, alertColor, surfaceColor, featureUnit };

  if (rows.length) {
    const { points } = scale;
    const line = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
    const defs = svgElement("defs");
    const gradient = svgElement("linearGradient", { id: "trace-fill", x1: "0", y1: "0", x2: "0", y2: "1" });
    gradient.append(
      svgElement("stop", { offset: "0%", "stop-color": fillColor, "stop-opacity": "0.24" }),
      svgElement("stop", { offset: "100%", "stop-color": fillColor, "stop-opacity": "0.01" })
    );
    defs.append(gradient);
    chart.append(defs);

    chart.append(
      svgElement("path", {
        d: `${line} L${points.at(-1).x} ${height - padY} L${points[0].x} ${height - padY} Z`,
        fill: "url(#trace-fill)"
      })
    );
    chart.append(
      svgElement("path", {
        d: line,
        fill: "none",
        stroke: lineColor,
        "stroke-width": "2.3",
        "stroke-linejoin": "round",
        "stroke-linecap": "round"
      })
    );

    chart.append(
      svgElement("line", {
        id: "trace-guide",
        x1: 0,
        x2: 0,
        y1: padY,
        y2: height - padY,
        stroke: lineColor,
        "stroke-width": "1",
        "stroke-dasharray": "3 3",
        opacity: "0"
      })
    );

    points.forEach((p, i) => {
      if (rows[i].alert || i === points.length - 1) {
        if (rows[i].alert) {
          chart.append(
            svgElement("circle", {
              cx: p.x,
              cy: p.y,
              r: "8.5",
              fill: alertColor,
              opacity: "0.2"
            })
          );
        }
        const dot = svgElement("circle", {
          cx: p.x,
          cy: p.y,
          r: rows[i].alert ? 4.8 : 3.8,
          fill: rows[i].alert ? alertColor : lineColor,
          stroke: surfaceColor,
          "stroke-width": "2"
        });
        dot.append(
          svgElement(
            "title",
            {},
            `UDI ${rows[i].UDI}: ${numberLabel(p.value)} ${featureUnit}${rows[i].alert ? " · Predicción de falla" : ""}`
          )
        );
        chart.append(dot);
      }
    });

    chart.append(
      svgElement("circle", {
        id: "trace-focus-dot",
        cx: 0,
        cy: 0,
        r: "5.8",
        fill: lineColor,
        stroke: surfaceColor,
        "stroke-width": "2.4",
        opacity: "0"
      })
    );

    chart.append(svgElement("text", { x: padLeft, y: height - 4, class: "chart-axis" }, `#${state.processed - rows.length + 1}`));
    if (rows.length > 1) {
      chart.append(svgElement("text", { x: width - padRight, y: height - 4, "text-anchor": "end", class: "chart-axis" }, `#${state.processed}`));
    }
    chart.setAttribute(
      "aria-label",
      `${chartFeature}: ${rows.length} registros procesados en orden de reproducción, del UDI ${rows[0].UDI} al UDI ${rows.at(-1).UDI}. Último valor ${numberLabel(rows.at(-1)[chartFeature])} ${featureUnit}.`
    );
  } else {
    chart.setAttribute("aria-label", "Sin registros procesados. El gráfico aparecerá al avanzar la simulación.");
  }

  document.getElementById("chart-range").textContent = rows.length
    ? `${rows.length} registros · Escala ${featureUnit}`
    : "Sin registros";

  for (const spark of document.querySelectorAll("[data-spark]")) {
    spark.replaceChildren();
    if (!rows.length) continue;
    const sparkPoints = coordinates(rows, spark.dataset.spark, 160, 28, 2, 2, 3).points;
    spark.append(
      svgElement("path", {
        d: sparkPoints.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" "),
        fill: "none",
        stroke: sparkColor,
        "stroke-width": "1.6",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      })
    );
  }
}

function updateMachinePhysics(state) {
  const row = state.last;
  const panel = document.querySelector(".machine-panel");
  const statePill = document.getElementById("machine-state-pill");

  if (statePill) {
    statePill.textContent = row?.alert
      ? "ALERTA DE FALLA"
      : (machineStateLabels[state.status] || "EN ESPERA");
  }

  const rpmEl = document.getElementById("machine-rpm");
  const torqueEl = document.getElementById("machine-torque");
  const wearEl = document.getElementById("machine-wear");
  const deltaEl = document.getElementById("machine-delta-t");
  const heatEl = document.getElementById("workpiece-heat");
  const torqueBar = document.getElementById("machine-torque-bar");
  const wearBar = document.getElementById("machine-wear-bar");

  if (rpmEl) rpmEl.textContent = row ? `${numberLabel(row["Rotational speed [rpm]"])} rpm` : "— rpm";
  if (torqueEl) torqueEl.textContent = row ? `${numberLabel(row["Torque [Nm]"])} Nm` : "— Nm";
  if (wearEl) wearEl.textContent = row ? `${numberLabel(row["Tool wear [min]"])} min` : "— min";
  if (deltaEl) {
    deltaEl.textContent = row
      ? `${numberLabel(row["Process temperature [K]"] - row["Air temperature [K]"])} K`
      : "— K";
  }

  // Vincular velocidad de rotación del husillo a los RPM reales
  if (panel && row) {
    const rpmNorm = clamp01((row["Rotational speed [rpm]"] - 1168) / (2886 - 1168));
    const spinSec = (0.52 - rpmNorm * 0.36).toFixed(3);
    panel.style.setProperty("--spin-dur", `${spinSec}s`);
  }

  // Barras de carga de Torque y Desgaste dentro de la consola CNC (altura máx 32px en y=152..184)
  if (torqueBar) {
    const tNorm = row ? clamp01((row["Torque [Nm]"] - 3.8) / (76.6 - 3.8)) : 0;
    const h = Math.max(2, tNorm * 32);
    torqueBar.setAttribute("height", h.toFixed(1));
    torqueBar.setAttribute("y", (184 - h).toFixed(1));
    torqueBar.setAttribute("fill", tNorm > 0.72 || row?.alert ? "#f08c42" : "#22b8cf");
  }

  if (wearBar) {
    const wNorm = row ? clamp01(row["Tool wear [min]"] / 253) : 0;
    const h = Math.max(2, wNorm * 32);
    wearBar.setAttribute("height", h.toFixed(1));
    wearBar.setAttribute("y", (184 - h).toFixed(1));
    wearBar.setAttribute("fill", wNorm > 0.78 ? "#ff6b2b" : "#f08c42");
  }

  // Resplandor térmico de la pieza según temperatura de proceso real y alerta
  if (heatEl) {
    const tempNorm = row ? clamp01((row["Process temperature [K]"] - 305.7) / (313.8 - 305.7)) : 0;
    const opacity = row ? Math.min(0.95, 0.14 + tempNorm * 0.55 + (row.alert ? 0.3 : 0)) : 0.08;
    heatEl.setAttribute("opacity", opacity.toFixed(2));
  }

  // Actualizar barras normalizadas de los 5 instrumentos
  for (const [feature, info] of Object.entries(sensorBounds)) {
    const bar = document.getElementById(info.gaugeId);
    if (!bar) continue;
    if (!row) {
      bar.style.width = "0%";
      bar.classList.remove("is-high");
      continue;
    }
    const norm = clamp01((row[feature] - info.min) / (info.max - info.min));
    bar.style.width = `${Math.max(4, norm * 100).toFixed(1)}%`;
    bar.classList.toggle("is-high", norm > 0.78);
  }
}

function bindChartHover() {
  const chart = document.getElementById("trace");
  const tip = document.getElementById("trace-tooltip");
  if (!chart || !tip) return;

  chart.addEventListener("pointermove", event => {
    if (!activeChartPoints.length || !activeChartGeo) return;
    const rect = chart.getBoundingClientRect();
    if (!rect.width) return;
    const relX = ((event.clientX - rect.left) / rect.width) * activeChartGeo.width;
    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < activeChartPoints.length; i++) {
      const dist = Math.abs(activeChartPoints[i].x - relX);
      if (dist < bestDist) {
        bestDist = dist;
        best = i;
      }
    }
    const p = activeChartPoints[best];
    const row = activeChartRows[best];
    const guide = document.getElementById("trace-guide");
    const focusDot = document.getElementById("trace-focus-dot");
    if (guide) {
      guide.setAttribute("x1", p.x.toFixed(2));
      guide.setAttribute("x2", p.x.toFixed(2));
      guide.setAttribute("opacity", "0.7");
    }
    if (focusDot) {
      focusDot.setAttribute("cx", p.x.toFixed(2));
      focusDot.setAttribute("cy", p.y.toFixed(2));
      focusDot.setAttribute("fill", row.alert ? activeChartGeo.alertColor : activeChartGeo.lineColor);
      focusDot.setAttribute("opacity", "1");
    }

    tip.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `UDI ${row.UDI} · Tipo ${row.Type}`;
    const val = document.createElement("div");
    val.className = "tt-val";
    val.textContent = `${numberLabel(p.value)} ${activeChartGeo.featureUnit}`;
    const outcome = document.createElement("div");
    outcome.className = row.alert ? "tt-alert" : "";
    outcome.textContent = `${row.alert ? "Alerta" : "Sin falla"} · ${outcomeLabels[row.outcome] || row.outcome}`;
    tip.append(title, val, outcome);
    tip.hidden = false;

    const pxX = (p.x / activeChartGeo.width) * rect.width;
    const pxY = (p.y / activeChartGeo.height) * rect.height;
    const tipWidth = tip.offsetWidth || 180;
    const left = pxX + tipWidth + 24 > rect.width ? Math.max(8, pxX - tipWidth - 14) : pxX + 14;
    const top = Math.max(6, Math.min(rect.height - (tip.offsetHeight || 68) - 6, pxY - 22));
    tip.style.transform = `translate(${left.toFixed(0)}px, ${top.toFixed(0)}px)`;
  });

  chart.addEventListener("pointerleave", hideTooltip);
}

function bindMachineTilt() {
  const viewport = document.querySelector(".machine-viewport");
  const svg = document.querySelector(".machine-drawing");
  if (!viewport || !svg) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  viewport.addEventListener("pointermove", event => {
    if (reduced.matches) return;
    const rect = viewport.getBoundingClientRect();
    const nx = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const ny = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
    svg.style.transform = `rotateY(${(nx * 2.4).toFixed(2)}deg) rotateX(${(-ny * 1.8).toFixed(2)}deg)`;
  });

  viewport.addEventListener("pointerleave", () => {
    svg.style.transform = "";
  });
}

function setChartFeature(feature) {
  if (!monitorUnits[feature]) return;
  chartFeature = feature;
  document.querySelectorAll("[data-feature]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.feature === feature));
  });
  document.querySelectorAll("[data-sensor-feature]").forEach(card => {
    card.dataset.active = String(card.dataset.sensorFeature === feature);
  });
  if (monitorState) drawCharts(monitorState);
}

function updateMonitor(state) {
  monitorState = state;
  document.body.dataset.run = state.status;
  document.body.dataset.alert = String(Boolean(state.last?.alert));
  const key = `${state.processed}/${state.last?.UDI || ""}/${state.status}`;
  if (key === lastDrawKey) return;
  lastDrawKey = key;

  updateMachinePhysics(state);

  const row = state.last;
  document.getElementById("decision-explanation").textContent = !row
    ? "El árbol de decisión evalúa las seis variables de entrada de cada registro."
    : row.alert
      ? "El patrón de esta observación fue clasificado como una condición con falla."
      : "El modelo no detectó una condición de falla en esta observación.";

  const alerts = (state.series || []).filter(r => r.alert).reverse();
  document.getElementById("window-alerts").textContent = alerts.length;
  const feed = document.getElementById("alert-feed");
  feed.replaceChildren();
  if (!alerts.length) {
    const empty = document.createElement("div");
    empty.className = "alert-empty";
    empty.textContent = state.processed ? "Sin predicciones de falla en esta ventana." : "Sin alertas registradas";
    const p = document.createElement("p");
    p.textContent = "Las predicciones de falla recientes aparecerán aquí al avanzar la simulación.";
    empty.append(p);
    feed.append(empty);
  }
  for (const alert of alerts.slice(0, 4)) {
    const item = document.createElement("div");
    item.className = "alert-event";
    const symbol = document.createElement("span");
    symbol.className = "alert-event-icon";
    symbol.textContent = "!";
    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `UDI ${alert.UDI}`;
    const description = document.createElement("span");
    description.textContent =
      alert.outcome === "FP" ? "Falsa alarma · Etiqueta sin falla" : "Falla detectada · Etiqueta con falla";
    text.append(title, description);
    const tag = document.createElement("span");
    tag.className = "alert-event-type";
    tag.textContent = alert.Type;
    item.append(symbol, text, tag);
    feed.append(item);
  }

  drawCharts(state);

  if (row && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    for (const value of document.querySelectorAll(".sensor > strong")) {
      value.animate([{ opacity: 0.45 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
    }
  }
}

document.querySelectorAll("[data-feature]").forEach(button => {
  button.addEventListener("click", () => setChartFeature(button.dataset.feature));
});

document.querySelectorAll("[data-sensor-feature]").forEach(card => {
  card.addEventListener("click", () => setChartFeature(card.dataset.sensorFeature));
  card.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setChartFeature(card.dataset.sensorFeature);
    }
  });
});

bindChartHover();
bindMachineTilt();

window.addEventListener("simulation-state", event => updateMonitor(event.detail));
window.addEventListener("portal-panel", event => {
  if (event.detail === "ejecucion" && monitorState) requestAnimationFrame(() => drawCharts(monitorState));
});
window.addEventListener("theme-change", () => {
  if (monitorState) requestAnimationFrame(() => drawCharts(monitorState));
});

let monitorResizeFrame;
window.addEventListener("resize", () => {
  cancelAnimationFrame(monitorResizeFrame);
  monitorResizeFrame = requestAnimationFrame(() => {
    if (monitorState) drawCharts(monitorState);
  });
});

if (typeof lastState !== "undefined" && lastState) updateMonitor(lastState);
