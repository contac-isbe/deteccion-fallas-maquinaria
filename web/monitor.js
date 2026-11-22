"use strict";

const monitorUnits = {
  "Rotational speed [rpm]": "rpm",
  "Torque [Nm]": "Nm",
  "Air temperature [K]": "K",
  "Process temperature [K]": "K",
  "Tool wear [min]": "min"
};

const sensorShortNames = {
  "Rotational speed [rpm]": "Rotación",
  "Torque [Nm]": "Torque",
  "Air temperature [K]": "Aire",
  "Process temperature [K]": "Proceso",
  "Tool wear [min]": "Desgaste"
};

const sensorBounds = {
  "Air temperature [K]": { min: 295.3, max: 304.5, mean: 300.0, std: 2.0, gaugeId: "gauge-air", badgeId: "sbadge-air" },
  "Process temperature [K]": { min: 305.7, max: 313.8, mean: 310.0, std: 1.48, gaugeId: "gauge-process", badgeId: "sbadge-process" },
  "Rotational speed [rpm]": { min: 1168, max: 2886, mean: 1538.8, std: 179.3, gaugeId: "gauge-speed", badgeId: "sbadge-speed" },
  "Torque [Nm]": { min: 3.8, max: 76.6, mean: 40.0, std: 9.97, gaugeId: "gauge-torque", badgeId: "sbadge-torque" },
  "Tool wear [min]": { min: 0, max: 253, mean: 108.0, std: 63.65, gaugeId: "gauge-wear", badgeId: "sbadge-wear" }
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
let chartScope = "window"; // "window" (últimos 60) | "session" (toda la sesión acumulada)
let monitorState = null;
let lastDrawKey = "";
let activeChartPoints = [];
let activeChartRows = [];
let activeChartGeo = null;

// Historial acumulado en memoria durante la sesión (se conserva al cambiar de sensor y se limpia al reiniciar)
const sessionHistory = new Map();
let lastProcessedCount = 0;
let lastBoomUdi = null;
let boomTimer = null;

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

/* ==========================================================================
   Atribución física por sensor para observaciones marcadas con alerta (AI4I 2020)
   El modelo clasifica la observación completa (6 variables); esta función identifica
   qué sensor(es) presentan valores críticos/extremos en esa alerta para no repetir
   el mismo marcador de error en sensores que estaban dentro de rango normal.
   ========================================================================== */

function alertSensorsFor(row) {
  if (!row || !row.alert) return [];
  const flagged = new Set();
  const air = row["Air temperature [K]"];
  const proc = row["Process temperature [K]"];
  const rpm = row["Rotational speed [rpm]"];
  const torque = row["Torque [Nm]"];
  const wear = row["Tool wear [min]"];
  const deltaT = proc - air;
  const power = torque * (rpm * (2 * Math.PI / 60));

  // Reglas físicas del dataset AI4I 2020 (TWF, HDF, PWF, OSF)
  if (wear >= 195) flagged.add("Tool wear [min]");
  if (deltaT <= 8.8 && rpm <= 1400) {
    flagged.add("Air temperature [K]");
    flagged.add("Process temperature [K]");
    flagged.add("Rotational speed [rpm]");
  }
  if (air >= 302.3) flagged.add("Air temperature [K]");
  if (proc >= 311.8) flagged.add("Process temperature [K]");
  if (torque >= 54 || torque <= 13 || torque * wear >= 10500 || power > 8800 || power < 3600) {
    flagged.add("Torque [Nm]");
  }
  if (rpm <= 1360 || rpm >= 2100 || power > 8800 || power < 3600) {
    flagged.add("Rotational speed [rpm]");
  }

  // Respaldo determinístico: si ninguna regla límite se disparó (ej. falsa alarma),
  // atribuir al sensor con mayor desviación estandarizada (z-score) respecto a la media.
  if (!flagged.size) {
    let topFeature = "Torque [Nm]";
    let topZ = -1;
    for (const [feature, b] of Object.entries(sensorBounds)) {
      const z = Math.abs((row[feature] - b.mean) / b.std);
      if (z > topZ) {
        topZ = z;
        topFeature = feature;
      }
    }
    flagged.add(topFeature);
  }
  return [...flagged];
}

function isAlertOnFeature(row, feature) {
  if (!row || !row.alert) return false;
  return alertSensorsFor(row).includes(feature);
}

// Acumular todos los registros recibidos durante la sesión para no perder alertas al cambiar de gráfica
function syncSessionHistory(state) {
  if (!state.processed || state.processed < lastProcessedCount) {
    sessionHistory.clear();
    lastBoomUdi = null;
  }
  lastProcessedCount = state.processed;
  for (const row of state.series || []) {
    if (!sessionHistory.has(row.UDI)) {
      sessionHistory.set(row.UDI, row);
    }
  }
  if (state.last && !sessionHistory.has(state.last.UDI)) {
    sessionHistory.set(state.last.UDI, state.last);
  }
}

function updateSensorAlertBadges() {
  const counts = {};
  for (const feature of Object.keys(sensorBounds)) counts[feature] = 0;

  for (const row of sessionHistory.values()) {
    if (!row.alert) continue;
    for (const feature of alertSensorsFor(row)) {
      counts[feature] = (counts[feature] || 0) + 1;
    }
  }

  for (const [feature, info] of Object.entries(sensorBounds)) {
    const badge = document.getElementById(info.badgeId);
    if (!badge) continue;
    const n = counts[feature] || 0;
    badge.textContent = String(n);
    badge.hidden = n === 0;
    badge.title = `${n} alerta(s) vinculada(s) a ${sensorShortNames[feature]} en esta sesión`;
  }
}

function triggerAlertBoom(row) {
  if (!row || !row.alert || row.UDI === lastBoomUdi) return;
  lastBoomUdi = row.UDI;

  window.dispatchEvent(new CustomEvent("alert-boom", { detail: row }));

  const bloom = document.getElementById("alert-bloom");
  if (bloom && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    bloom.classList.remove("is-glowing");
    void bloom.offsetWidth;
    bloom.classList.add("is-glowing");
  }

  document.body.classList.add("is-alert-boom");
  window.clearTimeout(boomTimer);
  boomTimer = window.setTimeout(() => {
    document.body.classList.remove("is-alert-boom");
    if (bloom) bloom.classList.remove("is-glowing");
  }, 2250);
}

// Curva cúbica suavizada Catmull-Rom -> Bézier
function smoothSplinePath(points, tension = 0.22) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  let d = `M${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) * tension;
    const cp1y = p1.y + (p2.y - p0.y) * tension;
    const cp2x = p2.x - (p3.x - p1.x) * tension;
    const cp2y = p2.y - (p3.y - p1.y) * tension;
    d += ` C${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }
  return d;
}

function coordinates(rows, feature, width, height, padLeft, padRight, padY) {
  const values = rows.map(row => row[feature]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const rawMin = min;
  const rawMax = max;
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const margin = Math.max((max - min) * 0.16, Math.abs(max) * 0.018, 0.15);
  min -= margin;
  max += margin;
  const spanX = Math.max(width - padLeft - padRight, 1);
  const spanY = Math.max(height - 2 * padY, 1);
  return {
    min,
    max,
    rawMin,
    rawMax,
    avg,
    points: values.map((v, i) => ({
      x: rows.length === 1 ? padLeft + spanX / 2 : padLeft + (i * spanX) / (rows.length - 1),
      y: height - padY - ((v - min) * spanY) / (max - min),
      value: v
    }))
  };
}

/* ==========================================================================
   Dial Semicircular Segmentado con Reborde Limpio (sin ondas superpuestas)
   ========================================================================== */

const ARC_TICKS = 37;

function initArcGauge() {
  const group = document.getElementById("arc-gauge-ticks");
  if (!group || group.childElementCount) return;
  const cx = 120;
  const cy = 112;
  const rOuter = 94;
  const rInner = 80;
  for (let i = 0; i < ARC_TICKS; i++) {
    const angle = Math.PI + (i / (ARC_TICKS - 1)) * Math.PI;
    const x1 = cx + Math.cos(angle) * rInner;
    const y1 = cy + Math.sin(angle) * rInner;
    const x2 = cx + Math.cos(angle) * rOuter;
    const y2 = cy + Math.sin(angle) * rOuter;
    group.append(
      svgElement("line", {
        x1: x1.toFixed(1),
        y1: y1.toFixed(1),
        x2: x2.toFixed(1),
        y2: y2.toFixed(1),
        class: "arc-tick",
        stroke: "var(--surface-3)",
        "stroke-width": i % 9 === 0 ? "3" : "2.1",
        "stroke-linecap": "round",
        opacity: "0.4"
      })
    );
  }
}

function updateArcGauge(row) {
  initArcGauge();
  const group = document.getElementById("arc-gauge-ticks");
  const valEl = document.getElementById("arc-gauge-val");
  const subEl = document.getElementById("arc-gauge-sub");
  const dotEl = document.getElementById("arc-gauge-dot");
  if (!group) return;

  const tNorm = row ? clamp01((row["Torque [Nm]"] - 3.8) / (76.6 - 3.8)) : 0;
  const pct = Math.round(tNorm * 100);
  const lit = Math.round(tNorm * ARC_TICKS);
  const primary = cssVar("--primary", "#38d9e8");
  const warn = cssVar("--chart-alert", "#fb923c");
  const track = cssVar("--border-strong", "#334155");

  const ticks = group.children;
  for (let i = 0; i < ticks.length; i++) {
    const isLit = i < lit;
    const highZone = i / ARC_TICKS > 0.72 || row?.alert;
    ticks[i].setAttribute("stroke", isLit ? (highZone ? warn : primary) : track);
    ticks[i].setAttribute("opacity", isLit ? "1" : "0.26");
  }

  // Posicionar indicador luminoso sobre el reborde exterior (radio 101, centro 120,112)
  if (dotEl) {
    const angle = Math.PI + tNorm * Math.PI;
    const dx = 120 + Math.cos(angle) * 101;
    const dy = 112 + Math.sin(angle) * 101;
    dotEl.setAttribute("cx", dx.toFixed(1));
    dotEl.setAttribute("cy", dy.toFixed(1));
    dotEl.setAttribute("fill", pct > 72 || row?.alert ? warn : primary);
  }

  if (valEl) valEl.textContent = row ? `${pct} %` : "0 %";
  if (subEl) {
    subEl.textContent = !row
      ? "Carga mecánica"
      : row.alert
        ? "Condición crítica detectada"
        : pct > 72
          ? "Torque elevado"
          : "Operación equilibrada";
  }
}

function hideTooltip() {
  const tip = document.getElementById("trace-tooltip");
  if (tip) tip.hidden = true;
  const guide = document.getElementById("trace-guide");
  if (guide) guide.setAttribute("opacity", "0");
  const focusDot = document.getElementById("trace-focus-dot");
  if (focusDot) focusDot.setAttribute("opacity", "0");
}

function rowsForScope(state) {
  if (chartScope === "session" && sessionHistory.size) {
    const all = [...sessionHistory.values()];
    // Si hay cientos de puntos en sesión, muestrear conservando TODAS las alertas del sensor activo + primer/último punto
    if (all.length <= 180) return all;
    const step = Math.ceil(all.length / 150);
    return all.filter((row, i) => i === 0 || i === all.length - 1 || i % step === 0 || isAlertOnFeature(row, chartFeature));
  }
  return state.series || [];
}

function drawCharts(state) {
  const rows = rowsForScope(state);
  const windowRows = state.series || [];
  const chart = document.getElementById("trace");
  chart.replaceChildren();
  hideTooltip();

  const width = Math.max(chart.clientWidth || 760, 300);
  const height = 268;
  const padLeft = 62;
  const padRight = 18;
  const padY = 24;
  chart.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const lineColor = cssVar("--chart-line", "#38d9e8");
  const gridColor = cssVar("--chart-grid", "rgba(255,255,255,0.06)");
  const alertColor = cssVar("--chart-alert", "#fb923c");
  const surfaceColor = cssVar("--surface-solid", "#12141a");
  const sparkColor = cssVar("--spark-line", "#38d9e8");

  document.getElementById("chart-empty").hidden = rows.length > 0;
  const featureUnit = monitorUnits[chartFeature];
  document.getElementById("chart-current").textContent = rows.length
    ? `${numberLabel(rows.at(-1)[chartFeature])} ${featureUnit}`
    : `— ${featureUnit}`;

  const scale = rows.length ? coordinates(rows, chartFeature, width, height, padLeft, padRight, padY) : null;

  const deltaPill = document.getElementById("chart-delta-pill");
  const minEl = document.getElementById("chart-min-val");
  const avgEl = document.getElementById("chart-avg-val");
  const maxEl = document.getElementById("chart-max-val");
  if (scale && rows.length) {
    if (minEl) minEl.textContent = `${numberLabel(scale.rawMin)} ${featureUnit}`;
    if (avgEl) avgEl.textContent = `${numberLabel(scale.avg)} ${featureUnit}`;
    if (maxEl) maxEl.textContent = `${numberLabel(scale.rawMax)} ${featureUnit}`;
    if (deltaPill) {
      const last = rows.at(-1);
      if (isAlertOnFeature(last, chartFeature)) {
        deltaPill.textContent = "⚠ Alerta en sensor";
        deltaPill.className = "delta-pill is-alert";
      } else if (rows.length > 1) {
        const prev = rows.at(-2)[chartFeature];
        const diff = prev ? ((last[chartFeature] - prev) / Math.abs(prev)) * 100 : 0;
        const sign = diff >= 0 ? "↗ +" : "↘ ";
        deltaPill.textContent = `${sign}${diff.toFixed(1)} %`;
        deltaPill.className = "delta-pill is-ok";
      } else {
        deltaPill.textContent = "✓ Normal";
        deltaPill.className = "delta-pill is-ok";
      }
    }
  } else {
    if (minEl) minEl.textContent = "—";
    if (avgEl) avgEl.textContent = "—";
    if (maxEl) maxEl.textContent = "—";
    if (deltaPill) {
      deltaPill.textContent = "En espera";
      deltaPill.className = "delta-pill";
    }
  }

  for (let i = 0; i < 4; i++) {
    const y = padY + (i * (height - 2 * padY)) / 3;
    chart.append(
      svgElement("line", {
        x1: padLeft,
        x2: width - padRight,
        y1: y,
        y2: y,
        stroke: gridColor,
        "stroke-dasharray": "3 6"
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

  let sensorAlertsInChart = 0;

  if (rows.length) {
    const { points } = scale;
    const curve = smoothSplinePath(points, rows.length > 90 ? 0.12 : 0.2);

    const defs = svgElement("defs");
    const gradient = svgElement("linearGradient", { id: "trace-fill", x1: "0", y1: "0", x2: "0", y2: "1" });
    gradient.append(
      svgElement("stop", { offset: "0%", "stop-color": lineColor, "stop-opacity": "0.26" }),
      svgElement("stop", { offset: "100%", "stop-color": lineColor, "stop-opacity": "0.01" })
    );
    defs.append(gradient);

    const stripePat = svgElement("pattern", { id: "trace-stripes", width: "6", height: "6", patternUnits: "userSpaceOnUse" });
    stripePat.append(svgElement("line", { x1: "0", y1: "0", x2: "0", y2: "6", stroke: lineColor, "stroke-opacity": "0.17", "stroke-width": "1" }));
    defs.append(stripePat);
    chart.append(defs);

    const areaD = `${curve} L${points.at(-1).x.toFixed(2)} ${height - padY} L${points[0].x.toFixed(2)} ${height - padY} Z`;
    chart.append(svgElement("path", { d: areaD, fill: "url(#trace-fill)" }));
    chart.append(svgElement("path", { d: areaD, fill: "url(#trace-stripes)" }));

    chart.append(
      svgElement("path", {
        d: curve,
        fill: "none",
        stroke: lineColor,
        "stroke-width": "2.4",
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
        "stroke-width": "1.2",
        "stroke-dasharray": "3 4",
        opacity: "0"
      })
    );

    // Marcar EXCLUSIVAMENTE las alertas atribuibles a ESTE sensor (guardadas por sensor)
    points.forEach((p, i) => {
      const isLast = i === points.length - 1;
      const sensorAlert = isAlertOnFeature(rows[i], chartFeature);
      if (sensorAlert) sensorAlertsInChart++;

      if (sensorAlert || isLast) {
        if (sensorAlert) {
          // Pin vertical fino anclando el instante exacto de la falla en este sensor
          chart.append(
            svgElement("line", {
              x1: p.x.toFixed(2),
              x2: p.x.toFixed(2),
              y1: p.y.toFixed(2),
              y2: (height - padY).toFixed(2),
              stroke: alertColor,
              "stroke-opacity": "0.42",
              "stroke-width": "1.2",
              "stroke-dasharray": "2 3"
            })
          );
        }
        chart.append(
          svgElement("circle", {
            cx: p.x,
            cy: p.y,
            r: sensorAlert ? "9.5" : "7.5",
            fill: sensorAlert ? alertColor : lineColor,
            opacity: "0.22"
          })
        );
        const dot = svgElement("circle", {
          cx: p.x,
          cy: p.y,
          r: sensorAlert ? 5 : 4,
          fill: sensorAlert ? alertColor : lineColor,
          stroke: surfaceColor,
          "stroke-width": "2.2"
        });
        dot.append(
          svgElement(
            "title",
            {},
            `UDI ${rows[i].UDI}: ${numberLabel(p.value)} ${featureUnit}${sensorAlert ? " · Alerta en " + sensorShortNames[chartFeature] : ""}`
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
        r: "6",
        fill: lineColor,
        stroke: surfaceColor,
        "stroke-width": "2.5",
        opacity: "0"
      })
    );

    const firstIdx = chartScope === "session" ? 1 : Math.max(1, state.processed - rows.length + 1);
    chart.append(svgElement("text", { x: padLeft, y: height - 5, class: "chart-axis" }, `#${firstIdx}`));
    if (rows.length > 1) {
      chart.append(svgElement("text", { x: width - padRight, y: height - 5, "text-anchor": "end", class: "chart-axis" }, `#${state.processed}`));
    }
    chart.setAttribute(
      "aria-label",
      `${chartFeature}: ${rows.length} registros mostrados, ${sensorAlertsInChart} alertas vinculadas a este sensor.`
    );
  } else {
    chart.setAttribute("aria-label", "Sin registros procesados. El gráfico aparecerá al avanzar la simulación.");
  }

  let totalSensorAlertsInSession = 0;
  for (const r of sessionHistory.values()) {
    if (isAlertOnFeature(r, chartFeature)) totalSensorAlertsInSession++;
  }

  document.getElementById("chart-range").textContent = rows.length
    ? chartScope === "session"
      ? `${sessionHistory.size} reg. · ${totalSensorAlertsInSession} alerta(s)`
      : totalSensorAlertsInSession > sensorAlertsInChart
        ? `${rows.length} reg. · ${sensorAlertsInChart} aquí (${totalSensorAlertsInSession} en sesión)`
        : `${rows.length} reg. · ${sensorAlertsInChart} alerta(s)`
    : "Sin registros";

  // Sparklines por sensor con sus propios puntos de alerta independientes
  for (const spark of document.querySelectorAll("[data-spark]")) {
    spark.replaceChildren();
    if (!windowRows.length) continue;
    const feat = spark.dataset.spark;
    const sparkPoints = coordinates(windowRows, feat, 110, 26, 2, 2, 3).points;
    spark.append(
      svgElement("path", {
        d: smoothSplinePath(sparkPoints, 0.2),
        fill: "none",
        stroke: sparkColor,
        "stroke-width": "1.7",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      })
    );
    sparkPoints.forEach((pt, idx) => {
      if (isAlertOnFeature(windowRows[idx], feat)) {
        spark.append(svgElement("circle", { cx: pt.x.toFixed(1), cy: pt.y.toFixed(1), r: "2.6", fill: alertColor }));
      }
    });
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

  if (panel && row) {
    const rpmNorm = clamp01((row["Rotational speed [rpm]"] - 1168) / (2886 - 1168));
    const spinSec = (0.52 - rpmNorm * 0.36).toFixed(3);
    panel.style.setProperty("--spin-dur", `${spinSec}s`);
  }

  if (torqueBar) {
    const tNorm = row ? clamp01((row["Torque [Nm]"] - 3.8) / (76.6 - 3.8)) : 0;
    const h = Math.max(2, tNorm * 32);
    torqueBar.setAttribute("height", h.toFixed(1));
    torqueBar.setAttribute("y", (176 - h).toFixed(1));
    torqueBar.setAttribute("fill", tNorm > 0.72 || row?.alert ? "#fb923c" : "#38d9e8");
  }

  if (wearBar) {
    const wNorm = row ? clamp01(row["Tool wear [min]"] / 253) : 0;
    const h = Math.max(2, wNorm * 32);
    wearBar.setAttribute("height", h.toFixed(1));
    wearBar.setAttribute("y", (176 - h).toFixed(1));
    wearBar.setAttribute("fill", wNorm > 0.78 ? "#ff6b2b" : "#fb923c");
  }

  if (heatEl) {
    const tempNorm = row ? clamp01((row["Process temperature [K]"] - 305.7) / (313.8 - 305.7)) : 0;
    const opacity = row ? Math.min(0.92, 0.14 + tempNorm * 0.55 + (row.alert ? 0.25 : 0)) : 0.08;
    heatEl.setAttribute("opacity", opacity.toFixed(2));
  }

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

  updateArcGauge(row);
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
    const sensorAlert = isAlertOnFeature(row, chartFeature);
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
      focusDot.setAttribute("fill", sensorAlert ? activeChartGeo.alertColor : activeChartGeo.lineColor);
      focusDot.setAttribute("opacity", "1");
    }

    tip.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `UDI ${row.UDI} · Tipo ${row.Type}`;
    const val = document.createElement("div");
    val.className = "tt-val";
    val.textContent = `${numberLabel(p.value)} ${activeChartGeo.featureUnit}`;
    const outcome = document.createElement("div");
    if (row.alert) {
      const drivers = alertSensorsFor(row).map(f => sensorShortNames[f]).join(", ");
      outcome.className = sensorAlert ? "tt-alert" : "";
      outcome.textContent = sensorAlert
        ? `Alerta aquí (${drivers}) · ${outcomeLabels[row.outcome] || row.outcome}`
        : `Alerta en ${drivers} · ${outcomeLabels[row.outcome] || row.outcome}`;
    } else {
      outcome.textContent = `Sin falla · ${outcomeLabels[row.outcome] || row.outcome}`;
    }
    tip.append(title, val, outcome);
    tip.hidden = false;

    const pxX = (p.x / activeChartGeo.width) * rect.width;
    const pxY = (p.y / activeChartGeo.height) * rect.height;
    const tipWidth = tip.offsetWidth || 190;
    const left = pxX + tipWidth + 24 > rect.width ? Math.max(8, pxX - tipWidth - 14) : pxX + 14;
    const top = Math.max(6, Math.min(rect.height - (tip.offsetHeight || 72) - 6, pxY - 22));
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
    svg.style.transform = `rotateY(${(nx * 2.5).toFixed(2)}deg) rotateX(${(-ny * 1.9).toFixed(2)}deg)`;
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

function setChartScope(scope) {
  if (scope !== "window" && scope !== "session") return;
  chartScope = scope;
  document.querySelectorAll("[data-scope]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.scope === scope));
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

  syncSessionHistory(state);
  updateSensorAlertBadges();
  updateMachinePhysics(state);

  const row = state.last;
  if (row?.alert) triggerAlertBoom(row);

  document.getElementById("decision-explanation").textContent = !row
    ? "El árbol de decisión evalúa las seis variables de cada registro."
    : row.alert
      ? `Falla predicha · Factor principal: ${alertSensorsFor(row).map(f => sensorShortNames[f]).join(" + ")}.`
      : "El modelo no detectó una condición de falla en esta observación.";

  const alerts = (state.series || []).filter(r => r.alert).reverse();
  document.getElementById("window-alerts").textContent = alerts.length;
  const feed = document.getElementById("alert-feed");
  feed.replaceChildren();
  if (!alerts.length) {
    const empty = document.createElement("div");
    empty.className = "alert-empty";
    empty.textContent = state.processed ? "Sin predicciones de falla en esta ventana." : "Sin alertas en ventana";
    const p = document.createElement("p");
    p.textContent = "Las predicciones de falla de los últimos 60 registros aparecerán aquí.";
    empty.append(p);
    feed.append(empty);
  }
  for (const alert of alerts.slice(0, 5)) {
    const item = document.createElement("div");
    item.className = "alert-event";
    const symbol = document.createElement("span");
    symbol.className = "alert-event-icon";
    symbol.textContent = "!";
    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `UDI ${alert.UDI}`;
    const drivers = alertSensorsFor(alert).map(f => sensorShortNames[f]).join(" · ");
    const description = document.createElement("span");
    description.textContent = `${drivers} · ${alert.outcome === "FP" ? "Falsa alarma" : "Falla real"}`;
    text.append(title, description);
    const tag = document.createElement("span");
    tag.className = "alert-event-type";
    tag.textContent = alert.Type;
    item.append(symbol, text, tag);
    feed.append(item);
  }

  drawCharts(state);

  if (row && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    for (const value of document.querySelectorAll(".sensor-line strong")) {
      value.animate([{ opacity: 0.45 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
    }
  }
}

document.querySelectorAll("[data-feature]").forEach(button => {
  button.addEventListener("click", () => setChartFeature(button.dataset.feature));
});

document.querySelectorAll("[data-scope]").forEach(button => {
  button.addEventListener("click", () => setChartScope(button.dataset.scope));
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

initArcGauge();
bindChartHover();
bindMachineTilt();

window.addEventListener("simulation-state", event => updateMonitor(event.detail));
window.addEventListener("portal-panel", event => {
  if (event.detail === "ejecucion" && monitorState) requestAnimationFrame(() => drawCharts(monitorState));
});
window.addEventListener("theme-change", () => {
  if (monitorState) {
    requestAnimationFrame(() => {
      drawCharts(monitorState);
      updateArcGauge(monitorState.last);
    });
  } else {
    updateArcGauge(null);
  }
});

let monitorResizeFrame;
window.addEventListener("resize", () => {
  cancelAnimationFrame(monitorResizeFrame);
  monitorResizeFrame = requestAnimationFrame(() => {
    if (monitorState) drawCharts(monitorState);
  });
});

if (typeof lastState !== "undefined" && lastState) updateMonitor(lastState);
