"use strict";
/* Monitor: muestra el árbol de decisión REAL del modelo congelado y el camino que sigue cada registro.
   Todo lo que se dibuja sale de /api/model (estructura) y de /api/state (registros procesados). */
const $ = id => document.getElementById(id);
const NUM = [
  {key: "Air temperature [K]", id: "air", label: "Temperatura del aire", unit: "K", dec: 1},
  {key: "Process temperature [K]", id: "process", label: "Temperatura del proceso", unit: "K", dec: 1},
  {key: "Rotational speed [rpm]", id: "speed", label: "Velocidad de rotación", unit: "rpm", dec: 0},
  {key: "Torque [Nm]", id: "torque", label: "Torque", unit: "Nm", dec: 1},
  {key: "Tool wear [min]", id: "wear", label: "Desgaste de la herramienta", unit: "min", dec: 0},
];
// Variables que el pipeline calcula a partir de las anteriores (física del proceso).
const DERIVED = [
  {key: "Power [W]", id: "power", label: "Potencia", unit: "W", dec: 0, derived: true, calc: v => v["Torque [Nm]"] * v["Rotational speed [rpm]"] * 2 * Math.PI / 60},
  {key: "Temp diff [K]", id: "dt", label: "Diferencia de temperatura (proceso − aire)", unit: "K", dec: 2, derived: true, calc: v => v["Process temperature [K]"] - v["Air temperature [K]"]},
  {key: "Wear x torque [minNm]", id: "strain", label: "Desgaste × torque", unit: "min·Nm", dec: 0, derived: true, calc: v => v["Tool wear [min]"] * v["Torque [Nm]"]},
];
const ALL = [...NUM, ...DERIVED];
let view = "plant";
const STEP = {"Air temperature [K]": .1, "Process temperature [K]": .1, "Rotational speed [rpm]": 1, "Torque [Nm]": .1, "Tool wear [min]": 1};
const statusNames = {ready: "Listo para iniciar", running: "Reproduciendo", paused: "En pausa", completed: "Reproducción completada", error: "Reproducción detenida por un error"};
const outcomes = {TN: "Acierto sin falla", TP: "Falla detectada", FP: "Falsa alarma", FN: "Falla omitida"};
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const STEP_MS = 120;

const fmt = (v, d = 1) => Number(v).toLocaleString("es-PE", {minimumFractionDigits: d, maximumFractionDigits: d});
const fmtT = v => Number(v).toLocaleString("es-PE", {maximumFractionDigits: 2});
const pct = v => (100 * v).toLocaleString("es-PE", {maximumFractionDigits: 0}) + " %";

let M = null;              // estructura del árbol
let pos = [];              // posición normalizada de cada nodo
let hits = [], maxHits = 0;
let lastState = null, busy = false, polling = false, generation = 0;
let mode = "play";
let shown = null;          // {trace, values, real, outcome, label, start}
let labValues = null, labToken = 0, labTimer = 0;
let projectMetrics = null;
let hover = -1;

/* ---------- Estructura y diseño del árbol ---------- */
function layoutTree() {
  const n = M.nodes; let leaves = 0, maxD = 0;
  const x = new Array(n.length), d = new Array(n.length);
  (function walk(i, depth) {
    d[i] = depth; maxD = Math.max(maxD, depth);
    if (n[i].l === -1) { x[i] = leaves++; return; }
    walk(n[i].l, depth + 1); walk(n[i].r, depth + 1);
    x[i] = (x[n[i].l] + x[n[i].r]) / 2;
  })(0, 0);
  pos = n.map((_, i) => ({x: leaves > 1 ? x[i] / (leaves - 1) : .5, y: maxD ? d[i] / maxD : 0, d: d[i]}));
  M.maxDepth = maxD;
}
const isLeaf = i => M.nodes[i].l === -1;
const leafFails = i => M.nodes[i].fail / Math.max(1, M.nodes[i].n) > .5;
const typeLetter = f => M.features[f].slice(-1);

function question(i) {
  const nd = M.nodes[i], name = M.features[nd.f];
  if (name.startsWith("Type_")) return {text: `¿Tipo de producto = ${typeLetter(nd.f)}?`, yesRight: true, kind: "type"};
  const meta = ALL.find(f => f.key === name);
  return {text: `¿${meta.label} ≤ ${fmtT(nd.t)} ${meta.unit}?`, yesRight: false, kind: "num", meta};
}
function valueFor(f, values) {
  const name = M.features[f];
  if (name.startsWith("Type_")) return values.Type === typeLetter(f) ? 1 : 0;
  const meta = DERIVED.find(d => d.key === name);
  return meta ? meta.calc(values) : values[name];
}

/* ---------- Dibujo ---------- */
const canvas = $("tree"), ctx = canvas.getContext("2d");
let W = 0, H = 0, dpr = 1, dirty = true;
const PAD = {x: 46, top: 28, bottom: 40};
const C = {path: "#6ee7ff", fail: "#ff6b7d", ok: "#35d0b4", node: "#a894e8", edge: "#7d6fb8", text: "#e9e4f7"};
const px = i => PAD.x + pos[i].x * (W - 2 * PAD.x);
const py = i => PAD.top + pos[i].y * (H - PAD.top - PAD.bottom);

function resize() {
  const wrap = $("tree-wrap"), w = wrap.clientWidth;
  if (!w) return;
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  W = w; H = Math.round(Math.max(380, Math.min(540, w * .5)));
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  dirty = true;
}
const heat = i => maxHits ? Math.log1p(hits[i] || 0) / Math.log1p(maxHits) : 0;

function currentProgress(now) {
  if (!shown) return 0;
  const len = shown.trace.path.length;
  if (reduceMotion.matches || shown.instant) return len - 1;
  return Math.min(len - 1, (now - shown.start) / STEP_MS);
}

function draw(now) {
  const n = M.nodes, prog = currentProgress(now), big = n.length < 80 ? 1.9 : 1, label = n.length < 80;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  // Guías de nivel: cada nivel es una pregunta
  ctx.strokeStyle = "rgba(168,148,232,.07)"; ctx.lineWidth = 1;
  for (let d = 0; d <= M.maxDepth; d += 1) {
    const y = PAD.top + (d / M.maxDepth) * (H - PAD.top - PAD.bottom);
    ctx.beginPath(); ctx.moveTo(PAD.x, y); ctx.lineTo(W - PAD.x, y); ctx.stroke();
  }
  // Aristas
  for (let i = 0; i < n.length; i++) {
    if (isLeaf(i)) continue;
    for (const c of [n[i].l, n[i].r]) {
      const h = heat(c);
      ctx.strokeStyle = `rgba(150,132,214,${.16 + .55 * h})`;
      ctx.lineWidth = (.8 + 1.6 * h) * (big > 1 ? 1.5 : 1);
      const x1 = px(i), y1 = py(i), x2 = px(c), y2 = py(c), my = (y1 + y2) / 2;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.bezierCurveTo(x1, my, x2, my, x2, y2); ctx.stroke();
    }
  }
  // Nodos
  for (let i = 0; i < n.length; i++) {
    const h = heat(i), x = px(i), y = py(i);
    if (isLeaf(i)) {
      const r = (2.2 + Math.min(3.2, Math.log10(n[i].n + 1) * 1.1)) * big;
      ctx.fillStyle = leafFails(i) ? C.fail : C.ok;
      ctx.globalAlpha = .45 + .55 * h;
      ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
    } else {
      const r = (i === 0 ? 6 : 2.4 + Math.min(2.6, Math.log10(n[i].n + 1) * .75)) * big;
      ctx.fillStyle = C.node; ctx.globalAlpha = .4 + .6 * h;
      ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  // Preguntas de todos los nodos (solo cuando el árbol es pequeño y cabe)
  if (label) {
    ctx.font = "500 10.5px Inter, system-ui, sans-serif"; ctx.textBaseline = "middle"; ctx.textAlign = "center";
    for (let i = 0; i < n.length; i++) {
      if (isLeaf(i)) continue;
      const q = question(i).text.replace(/^¿|\?$/g, "").replace("Diferencia de temperatura (proceso − aire)", "Dif. temperatura").replace("Velocidad de rotación", "Velocidad"), x = px(i), y = py(i) + 17;
      ctx.lineWidth = 3.5; ctx.strokeStyle = "rgba(15,11,25,.9)"; ctx.strokeText(q, x, y);
      ctx.fillStyle = "rgba(214,205,240,.82)"; ctx.fillText(q, x, y);
    }
    ctx.font = "600 10px Inter, system-ui, sans-serif";
    for (let i = 0; i < n.length; i++) {
      if (!isLeaf(i)) continue;
      const x = px(i), y = py(i) + 15, t = `${n[i].fail}/${n[i].n}`;
      ctx.lineWidth = 3; ctx.strokeStyle = "rgba(15,11,25,.9)"; ctx.strokeText(t, x, y);
      ctx.fillStyle = leafFails(i) ? "#ff9aa6" : "#8fe3d2"; ctx.fillText(t, x, y);
    }
  }
  // Camino del registro actual
  if (shown) {
    const path = shown.trace.path, reached = Math.floor(prog);
    ctx.save();
    ctx.lineCap = "round"; ctx.shadowColor = C.path; ctx.shadowBlur = 12;
    ctx.strokeStyle = C.path; ctx.lineWidth = 2.6;
    const seg = (a, b, t) => {
      const x1 = px(a), y1 = py(a), x2 = px(b), y2 = py(b), my = (y1 + y2) / 2;
      const pt = u => { const v = 1 - u; return [v*v*v*x1 + 3*v*v*u*x1 + 3*v*u*u*x2 + u*u*u*x2, v*v*v*y1 + 3*v*v*u*my + 3*v*u*u*my + u*u*u*y2]; };
      ctx.beginPath(); const s = pt(0); ctx.moveTo(s[0], s[1]);
      for (let k = 1; k <= 16; k++) { const q = pt(t * k / 16); ctx.lineTo(q[0], q[1]); }
      ctx.stroke(); return pt(t);
    };
    let head = [px(path[0]), py(path[0])];
    for (let k = 0; k < path.length - 1; k++) {
      if (k < reached) head = seg(path[k], path[k + 1], 1);
      else if (k === reached) head = seg(path[k], path[k + 1], Math.max(0, prog - k));
    }
    ctx.shadowBlur = 0;
    // nodos visitados
    for (let k = 0; k <= Math.min(reached, path.length - 1); k++) {
      const i = path[k], leaf = isLeaf(i);
      ctx.fillStyle = leaf ? (shown.trace.p_fail > .5 ? C.fail : C.ok) : "#fff";
      ctx.beginPath(); ctx.arc(px(i), py(i), (leaf ? 6 : 4) * (big > 1 ? 1.35 : 1), 0, 6.2832); ctx.fill();
      ctx.strokeStyle = C.path; ctx.lineWidth = 2; ctx.stroke();
    }
    // etiquetas de las primeras preguntas (en árboles grandes)
    ctx.font = "600 11px Inter, system-ui, sans-serif"; ctx.textBaseline = "middle";
    for (let k = 0; k < (label ? 0 : Math.min(reached + 1, path.length - 1, 4)); k++) {
      const i = path[k], q = question(i), goLeft = path[k + 1] === M.nodes[i].l;
      const label = q.text.replace(/^¿|\?$/g, "");
      const tw = ctx.measureText(label).width, x = px(i), y = py(i);
      let lx = goLeft ? x - tw - 18 : x + 12; lx = Math.max(8, Math.min(W - tw - 10, lx));
      ctx.fillStyle = "rgba(14,11,24,.86)";
      ctx.beginPath(); ctx.roundRect(lx - 5, y - 10, tw + 10, 20, 6); ctx.fill();
      ctx.strokeStyle = "rgba(110,231,255,.45)"; ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = C.text; ctx.textAlign = "left"; ctx.fillText(label, lx, y + .5);
    }
    // cabeza luminosa
    if (reached < path.length - 1) {
      ctx.fillStyle = "#fff"; ctx.shadowColor = C.path; ctx.shadowBlur = 16;
      ctx.beginPath(); ctx.arc(head[0], head[1], 4.5, 0, 6.2832); ctx.fill();
    }
    ctx.restore();
    // pulso de la hoja
    if (prog >= path.length - 1 && !reduceMotion.matches) {
      const leaf = path[path.length - 1], col = shown.trace.p_fail > .5 ? C.fail : C.ok;
      const t = ((now - shown.start) / 1500) % 1;
      ctx.strokeStyle = col; ctx.globalAlpha = (1 - t) * .8; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(px(leaf), py(leaf), 9 + t * 24, 0, 6.2832); ctx.stroke(); ctx.globalAlpha = 1;
    }
  }
  // Nodo bajo el cursor
  if (hover >= 0) {
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(px(hover), py(hover), 8, 0, 6.2832); ctx.stroke();
  }
}

let lastReached = -2;
function frame(now) {
  requestAnimationFrame(frame);
  if (!M || !W || $("ejecucion").hidden || document.hidden) return;
  draw(now);
  const prog = currentProgress(now), reached = Math.floor(prog);
  if (shown && reached !== lastReached) { lastReached = reached; syncReveal(reached); }
}

/* ---------- Panel de preguntas ---------- */
function buildSteps(entry) {
  const list = $("steps"); list.replaceChildren();
  const path = entry.trace.path;
  for (let k = 0; k < path.length - 1; k++) {
    const i = path[k], nd = M.nodes[i], q = question(i), goLeft = path[k + 1] === nd.l;
    const yes = q.yesRight ? !goLeft : goLeft;
    const li = document.createElement("li"); li.className = "step";
    const val = valueFor(nd.f, entry.values);
    let right, track = "";
    if (q.kind === "num") {
      right = `${fmt(val, q.meta.dec)} ${q.meta.unit}`;
      const [lo, hi] = M.ranges[q.meta.key] || [nd.t * 0.5, nd.t * 1.5], t = Math.min(100, Math.max(0, (nd.t - lo) / (hi - lo) * 100)), v = Math.min(100, Math.max(0, (val - lo) / (hi - lo) * 100));
      track = `<span class="q-track" aria-hidden="true"><i class="q-zone" style="left:0;width:${t}%"></i><i class="q-thr" style="left:${t}%"></i><i class="q-val" style="left:${v}%"></i></span>`;
    } else right = `Tipo ${entry.values.Type}`;
    li.innerHTML = `<span class="q-n">${k + 1}</span><div class="q-body"><div class="q-line"><span class="q-text"></span><span class="q-ans" data-yes="${yes}"></span></div>${track}</div>`;
    li.querySelector(".q-text").textContent = q.text;
    li.querySelector(".q-ans").textContent = `${right} → ${yes ? "Sí" : "No"}`;
    list.append(li);
  }
  const leaf = document.createElement("li"); leaf.className = "step step-leaf";
  const fail = entry.trace.p_fail > .5;
  leaf.innerHTML = `<span class="q-n">✓</span><div class="q-body"><div class="q-line"><span class="q-text"></span><span class="q-ans" data-yes="${fail}"></span></div></div>`;
  leaf.querySelector(".q-text").textContent = "Llega a una hoja: ya no hay más preguntas";
  leaf.querySelector(".q-ans").textContent = fail ? "Predice falla" : "Predice sin falla";
  list.append(leaf);
  $("r-sub").textContent = `${path.length - 1} preguntas, de la raíz a la hoja.`;
}
function syncReveal(reached) {
  const items = [...$("steps").children];
  items.forEach((li, k) => li.classList.toggle("on", k <= reached));
  const lastIdx = shown ? shown.trace.path.length - 1 : 0;
  if (shown && reached >= lastIdx) {
    items.at(-1)?.classList.add("on");
    finishDecision();
  } else if (shown) {
    setChip("thinking", "Preguntando…", `Nivel ${Math.min(reached + 1, lastIdx)} de ${lastIdx}`);
  }
  const on = $("steps").querySelectorAll(".step.on"); const last = on[on.length - 1];
  if (last) { const box = $("steps"); box.scrollTop = Math.max(0, last.offsetTop - box.clientHeight + last.offsetHeight + 10); }
}

/* ---------- Veredicto ---------- */
function setChip(state, title, sub) {
  const chip = $("verdict-chip"); chip.dataset.state = state;
  $("vc-icon").textContent = {idle: "◌", thinking: "◔", alert: "⚠", ok: "✓", lab: "✎"}[state] || "◌";
  $("vc-title").textContent = title; $("vc-sub").textContent = sub;
}
let finishedFor = null;
function finishDecision() {
  if (!shown || finishedFor === shown) return;
  finishedFor = shown;
  const t = shown.trace, fail = t.p_fail > .5, lab = shown.label === "lab";
  setChip(lab ? "lab" : fail ? "alert" : "ok", fail ? "Alerta: con falla" : "Sin falla detectada",
    lab ? "Respuesta del modelo a tu prueba" : `UDI ${shown.udi} · Tipo ${shown.values.Type}`);
  const d = $("decision"); d.dataset.state = fail ? "alert" : "ok";
  $("prediction").textContent = fail ? "⚠ Alerta: con falla" : "✓ Sin falla detectada";
  $("ev-fill").style.width = Math.max(2, t.p_fail * 100) + "%";
  $("evidence").dataset.state = fail ? "alert" : "ok";
  const nonFail = t.leaf_n - t.leaf_fail;
  $("ev-text").textContent = t.leaf_fail === 0
    ? `En esta hoja cayeron ${t.leaf_n} casos de entrenamiento y ninguno terminó en falla.`
    : `En esta hoja cayeron ${t.leaf_n} casos de entrenamiento: ${t.leaf_fail} terminaron en falla y ${nonFail} no (${pct(t.p_fail)}). No es una probabilidad calibrada.`;
  $("reference").textContent = lab ? "Es una prueba tuya: no hay etiqueta real con la que comparar." :
    `Etiqueta real: ${shown.real ? "con falla" : "sin falla"} · ${outcomes[shown.outcome]}. ${shown.outcome === "FN" ? "El modelo se equivocó: este caso se le escapó." : shown.outcome === "FP" ? "El modelo se equivocó: dio una alarma innecesaria." : ""}`;
  $("truth").dataset.outcome = lab ? "lab" : shown.outcome;
  if (lab) $("axis-depth").textContent = `↓ ${t.path.length - 1} preguntas hasta la hoja ${t.leaf}`;
  highlightSensors();
}
function clearDecision() {
  finishedFor = null;
  $("decision").dataset.state = "idle"; $("prediction").textContent = "Sin predicción";
  $("ev-fill").style.width = "0%"; $("evidence").dataset.state = "idle";
  $("ev-text").textContent = "Cuando el registro llega a una hoja, aquí verás cuántos casos de entrenamiento parecidos terminaron en falla.";
  $("reference").textContent = "La etiqueta real se muestra después de decidir; el modelo nunca la ve.";
  $("truth").dataset.outcome = "";
}

/* ---------- Sensores ---------- */
function buildSensors() {
  const box = $("sensor-rows"); box.replaceChildren();
  const impSum = M.features.reduce((acc, name, i) => acc + (name.startsWith("Type_") ? M.importances[i] : 0), 0);
  $("type-buttons").parentElement.querySelector("span").innerHTML = `Tipo de producto <em>peso ${pct(impSum)}</em>`;
  ALL.forEach(f => {
    const k = M.features.indexOf(f.key); if (k < 0) return;
    const [lo, hi] = M.ranges[f.key];
    const ticks = [...new Set(M.nodes.filter(n => n.f === k).map(n => n.t))];
    const row = document.createElement("div"); row.className = "srow" + (f.derived ? " derived" : ""); row.dataset.k = k;
    row.innerHTML = `<div class="srow-top"><label for="in-${f.id}">${f.label}${f.derived ? " <span class=\"calc\" title=\"Calculada por el pipeline a partir de las mediciones\">calculada</span>" : ""}</label><em title="Importancia de la variable en el árbol (reducción de impureza)">peso ${pct(M.importances[k])}</em><output id="out-${f.id}">—</output></div>
      <div class="srow-track"><div class="ticks" aria-hidden="true">${ticks.map(t => `<i data-t="${t}" style="left:${Math.min(100, Math.max(0, (t - lo) / (hi - lo) * 100)).toFixed(2)}%"></i>`).join("")}</div>
      <input id="in-${f.id}" type="range" min="${lo}" max="${hi}" step="${(hi - lo) / 400}" value="${(lo + hi) / 2}" disabled></div>
      <div class="srow-scale" aria-hidden="true"><span>${fmt(lo, 0)}</span><span>${fmt(hi, 0)} ${f.unit}</span></div>`;
    box.append(row);
    if (!f.derived) { row.querySelector("input").step = {air: .1, process: .1, speed: 1, torque: .1, wear: 1}[f.id]; row.querySelector("input").addEventListener("input", () => { if (mode === "lab") labChanged(); }); }
  });
}
function setSensorValues(values) {
  ALL.forEach(f => {
    const v = f.derived ? f.calc(values) : values[f.key], input = $("in-" + f.id); if (!input) return;
    input.value = v; $("out-" + f.id).textContent = `${fmt(v, f.dec)} ${f.unit}`;
  });
  document.querySelectorAll("#type-buttons button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.type === values.Type)));
}
function highlightSensors() {
  document.querySelectorAll(".ticks i").forEach(t => t.classList.remove("used"));
  document.querySelectorAll(".srow").forEach(r => r.classList.remove("hot"));
  if (!shown) return;
  const path = shown.trace.path;
  for (let k = 0; k < path.length - 1; k++) {
    const nd = M.nodes[path[k]]; if (M.features[nd.f].startsWith("Type_")) continue;
    const row = document.querySelector(`.srow[data-k="${nd.f}"]`);
    row.classList.add("hot");
    row.querySelector(`.ticks i[data-t="${nd.t}"]`)?.classList.add("used");
  }
}

/* ---------- Estado y modos ---------- */
function showEntry(entry) {
  shown = entry; entry.start = performance.now(); lastReached = -2;
  clearDecision(); buildSteps(entry); setSensorValues(entry.values); renderAE(entry, false);
  $("axis-depth").textContent = `↓ ${entry.trace.path.length - 1} preguntas hasta la hoja ${entry.trace.leaf}`;
  setChip("thinking", "Preguntando…", `Nivel 1 de ${entry.trace.path.length - 1}`);
  if (reduceMotion.matches) entry.instant = true;
}
function entryFromRecord(r) {
  const values = {Type: r.Type}; NUM.forEach(f => values[f.key] = r[f.key]);
  return {trace: {path: r.path, leaf: r.leaf, leaf_n: r.leaf_n, leaf_fail: r.leaf_fail, p_fail: r.p_fail},
    values, udi: r.UDI, real: r["Machine failure"], outcome: r.outcome, label: "play", ae: r.ae};
}
function idle() {
  shown = null; finishedFor = null; clearDecision();
  $("steps").innerHTML = '<li class="steps-empty">Aquí aparecerán las preguntas que el modelo hace a cada registro.</li>';
  $("r-sub").textContent = "Las preguntas del camino, en orden.";
  $("identity").textContent = "Sin registro todavía.";
  setChip("idle", "Esperando un registro", "Pulsa «Iniciar simulación» o «Siguiente».");
  $("axis-depth").textContent = "↓ cada nivel es una pregunta sobre una medición";
  highlightSensors(); renderAE(null);
}

function setMode(next) {
  mode = next;
  $("mode-play").setAttribute("aria-pressed", String(next === "play"));
  $("mode-lab").setAttribute("aria-pressed", String(next === "lab"));
  $("lab").dataset.mode = next;
  $("lab-actions").hidden = next !== "lab";
  document.querySelectorAll(".srow:not(.derived) input, #type-buttons button").forEach(el => el.disabled = next !== "lab");
  $("stage-title").textContent = next === "lab" ? "Mueve las mediciones y mira cómo cambia el camino" : "Cada registro recorre este árbol hasta una hoja";
  $("sensor-hint").textContent = next === "lab"
    ? "Las barras están limitadas al rango del dataset. Pueden formar combinaciones poco realistas: sirven para entender al modelo, no para probar máquinas reales."
    : "Las marcas verticales de cada barra son los cortes que el árbol aprendió para esa medición; las brillantes son las que usó para este registro.";
  $("identity").textContent = next === "lab" ? "Prueba manual · no entra al registro" : (lastState?.last ? `UDI ${lastState.last.UDI} · Tipo de producto ${lastState.last.Type}` : "Sin registro todavía.");
  if (next === "lab") {
    const last = lastState?.last;
    labValues = last ? entryFromRecord(last).values : {Type: "L", "Air temperature [K]": 300, "Process temperature [K]": 310, "Rotational speed [rpm]": 1500, "Torque [Nm]": 40, "Tool wear [min]": 100};
    setSensorValues(labValues); runLab(true);
  } else if (lastState?.last) {
    showEntry(entryFromRecord(lastState.last)); lastShownKey = key(lastState);
  } else idle();
}
function labChanged() {
  NUM.forEach(f => labValues[f.key] = Number($("in-" + f.id).value));
  setSensorValues(labValues);
  clearTimeout(labTimer); labTimer = setTimeout(() => runLab(false), 50);
}
async function runLab(first) {
  const token = ++labToken;
  try {
    const r = await request("/api/whatif", labValues);
    if (token !== labToken || mode !== "lab") return;
    const same = shown && shown.label === "lab" && shown.trace.path.join() === r.path.join();
    const entry = {trace: r, values: {...labValues}, label: "lab", instant: !first, ae: r.ae};
    if (same) { shown.values = entry.values; shown.trace = r; shown.ae = r.ae; finishedFor = null; finishDecision(); renderAE(shown, true); return; }
    shown = entry; entry.start = performance.now(); lastReached = -2; finishedFor = null;
    buildSteps(entry); $("steps").querySelectorAll(".step").forEach(li => li.classList.add("on"));
    finishDecision(); renderAE(entry, !first);
  } catch (e) { showError(e.message); }
}


/* ---------- Autoencoder ---------- */
function activationColor(v, max, signed) {
  const t = Math.min(1, Math.abs(v) / (max || 1));
  if (signed && v < 0) return `color-mix(in srgb, #b57cf0 ${Math.round(20 + 75 * t)}%, var(--card))`;
  return `color-mix(in srgb, #12b5d6 ${Math.round(12 + 85 * t)}%, var(--card))`;
}
function renderAE(entry, instant) {
  const A = M && M.autoencoder; if (!A) return;
  const net = $("ae-net"), feats = $("ae-feats"), verdict = $("ae-verdict"), agree = $("ae-agree");
  const d = entry && entry.ae;
  if (!d) {
    net.replaceChildren(); feats.replaceChildren(); net.dataset.instant = "true";
    verdict.textContent = "Sin registro"; verdict.dataset.state = "idle"; agree.textContent = ""; agree.dataset.k = "";
    $("ae-fill").style.width = "0%"; $("ae-bar").classList.remove("over");
    $("ae-thr").style.left = "50%";
    $("ae-text").textContent = "El error es el promedio de las diferencias al cuadrado entre la entrada y su reconstrucción.";
    drawNet(null, A); return;
  }
  net.dataset.instant = String(!!instant);
  drawNet(d, A);
  // barras entrada / reconstrucción
  feats.replaceChildren();
  const pos = z => (50 + Math.max(-4, Math.min(4, z)) / 4 * 50).toFixed(1);
  A.input_names.forEach((name, i) => {
    const a = d.input[i], b = d.output[i], hi = d.feature_error[i] > 4 * d.threshold;
    const row = document.createElement("div"); row.className = "ae-f"; row.dataset.hi = String(hi);
    row.innerHTML = `<span></span><div class="tr"><i class="zero"></i><i class="gap" style="left:${Math.min(pos(a), pos(b))}%;width:${Math.abs(pos(a) - pos(b))}%"></i><i class="in" style="left:${pos(a)}%"></i><i class="out" style="left:${pos(b)}%"></i></div><em></em>`;
    row.children[0].textContent = name; row.children[2].textContent = fmt(d.feature_error[i], 2);
    row.title = `${name}: entrada ${fmt(a, 2)} · reconstruida ${fmt(b, 2)} (en desviaciones estándar)`;
    feats.append(row);
  });
  const hint = document.createElement("div"); hint.className = "ae-f"; hint.style.fontSize = "10.5px";
  hint.innerHTML = `<span></span><span style="color:var(--muted)"><b style="color:var(--cyan)">●</b> entrada &nbsp; <b style="color:var(--accent)">○</b> reconstrucción &nbsp; <span style="color:var(--warn)">▬</span> diferencia</span><span></span>`;
  feats.append(hint);
  // medidor de error
  const top = Math.max(d.threshold * 2.2, d.error * 1.15);
  $("ae-fill").style.width = Math.min(100, d.error / top * 100) + "%";
  $("ae-thr").style.left = (d.threshold / top * 100) + "%";
  $("ae-bar").classList.toggle("over", d.alert);
  $("ae-text").textContent = d.alert
    ? `Error de reconstrucción ${fmt(d.error, 3)} > umbral ${fmt(d.threshold, 3)}: el decoder no logra rehacer este registro, así que lo considera atípico.`
    : `Error de reconstrucción ${fmt(d.error, 3)} ≤ umbral ${fmt(d.threshold, 3)}: el registro se parece a lo que el autoencoder aprendió como normal.`;
  verdict.textContent = d.alert ? "⚠ Atípico" : "✓ Normal"; verdict.dataset.state = d.alert ? "atypical" : "normal";
  const treeAlert = entry.trace.p_fail > .5;
  agree.dataset.k = treeAlert === d.alert ? "agree" : "split";
  agree.textContent = treeAlert === d.alert ? (d.alert ? "El árbol y el autoencoder coinciden: alerta" : "El árbol y el autoencoder coinciden: sin alerta")
    : treeAlert ? "Discrepan: alertó el árbol, el autoencoder no" : "Discrepan: alertó solo el autoencoder";
}
function drawNet(d, A) {
  const arch = A.architecture, cols = arch.length, mid = Math.floor(cols / 2);
  const W0 = 700, H0 = 330, xs = [96, 236, 350, 464, 604], cy = 176, gap = arch.map(n => Math.min(62, 270 / Math.max(1, n - 1)));
  const titles = ["Entrada", "Encoder", "Espacio latente", "Decoder", "Reconstrucción"];
  const subs = [`${arch[0]} variables`, "comprime", `${arch[mid]} números`, "expande", `${arch[0]} valores`];
  const layers = d ? [d.input, ...d.encoder, ...d.decoder, d.output] : null;
  const pts = arch.map((n, c) => Array.from({length: n}, (_, i) => [xs[c], cy + (i - (n - 1) / 2) * gap[c]]));
  let svg = `<svg viewBox="0 0 ${W0} ${H0}" aria-hidden="true">`;
  svg += `<rect class="zone zone-lat" x="${xs[2] - 34}" y="38" width="68" height="276" rx="12"/>`;
  for (let c = 0; c < cols - 1; c++)
    for (const a of pts[c]) for (const b of pts[c + 1]) svg += `<line class="link" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
  const maxes = layers ? layers.map(l => Math.max(1e-6, ...l.map(Math.abs))) : null;
  pts.forEach((col, c) => {
    svg += `<g class="ae-col" style="--c:${c}">`;
    svg += `<text class="col-t" x="${xs[c]}" y="14">${titles[c]}</text><text class="col-s" x="${xs[c]}" y="27">${subs[c]}</text>`;
    col.forEach(([x, y], i) => {
      const v = layers ? layers[c][i] : 0, fill = layers ? activationColor(v, maxes[c], c === 0 || c === cols - 1) : "var(--soft)";
      svg += `<circle class="nd" cx="${x}" cy="${y}" r="${c === mid ? 12 : 9}" fill="${fill}"><title>${layers ? fmt(v, 2) : ""}</title></circle>`;
      if (c === 0) svg += `<text class="nm" x="${x - 16}" y="${y + 3.5}" text-anchor="end">${A.input_names[i]}</text>`;
      if (c === cols - 1) svg += `<text class="nm" x="${x + 16}" y="${y + 3.5}">${A.input_names[i]}</text>`;
    });
    svg += "</g>";
  });
  $("ae-net").innerHTML = svg + "</svg>";
}

/* ---------- Carriles realidad / IA ---------- */
function drawLanes(series) {
  const N = 60, cw = 14, h = 96, el = $("lanes");
  const yR = 14, yP = 66, bh = 22;
  let s = `<svg viewBox="0 0 ${N * cw + 74} ${h}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">`;
  s += `<text x="0" y="${yR + 15}" class="ln-label">Realidad</text><text x="0" y="${yP + 15}" class="ln-label">Modelo</text>`;
  const x0 = 74, start = N - series.length;
  series.forEach((r, i) => {
    const x = x0 + (start + i) * cw + 1, w = cw - 2, o = r.outcome;
    const newest = i === series.length - 1;
    if (newest) s += `<rect x="${x - 2}" y="2" width="${w + 4}" height="${h - 4}" rx="4" class="ln-now"/>`;
    const dot = y => `<rect x="${x + 2}" y="${y + bh / 2 - 1.5}" width="${w - 4}" height="3" rx="1.5" class="ln-dot"/>`;
    if (o === "TP") s += `<rect x="${x}" y="${yR}" width="${w}" height="${bh}" rx="3" class="ln-fail"/><rect x="${x}" y="${yP}" width="${w}" height="${bh}" rx="3" class="ln-fail"/><line x1="${x + w / 2}" x2="${x + w / 2}" y1="${yR + bh}" y2="${yP}" class="ln-link-ok"/>`;
    else if (o === "FN") s += `<rect x="${x}" y="${yR}" width="${w}" height="${bh}" rx="3" class="ln-fail"/><rect x="${x + 1}" y="${yP + 1}" width="${w - 2}" height="${bh - 2}" rx="3" class="ln-miss"/><line x1="${x + w / 2}" x2="${x + w / 2}" y1="${yR + bh}" y2="${yP}" class="ln-link-bad"/>`;
    else if (o === "FP") s += dot(yR) + `<rect x="${x}" y="${yP}" width="${w}" height="${bh}" rx="3" class="ln-false"/><line x1="${x + w / 2}" x2="${x + w / 2}" y1="${yR + bh / 2}" y2="${yP}" class="ln-link-warn"/>`;
    else s += dot(yR) + dot(yP);
    s += `<title>UDI ${r.UDI}: ${outcomes[o]}</title>`;
  });
  el.innerHTML = s + "</svg>";
}

/* ---------- Render principal ---------- */
let lastShownKey = null;
const key = s => s.last ? `${s.processed}:${s.last.UDI}` : "none";
function showError(message) { $("error").textContent = message || ""; $("error").hidden = !message; }
function applyControls() {
  if (view !== "test") return;
  const s = lastState, ids = ["start", "pause", "step", "reset", "load"];
  if (!s) { ids.forEach(id => { const e = $(id); if (e) e.disabled = true; }); return; }
  $("start").disabled = busy || ["running", "completed", "error"].includes(s.status);
  $("start").textContent = s.status === "paused" ? "Continuar" : "Iniciar simulación";
  $("pause").disabled = busy || s.status !== "running";
  $("step").disabled = busy || ["running", "completed", "error"].includes(s.status);
  $("reset").disabled = busy;
  if ($("load")) $("load").disabled = busy || s.status === "running";
  $("interval").disabled = busy || s.status === "running";
}
function render(s) {
  const prev = lastState; lastState = s;
  if (view === "test") {
    $("status").textContent = statusNames[s.status];
    $("run-dot").dataset.state = s.status;
  }
  $("count").textContent = s.processed.toLocaleString("es-PE"); $("total").textContent = s.total.toLocaleString("es-PE");
  $("bar").style.width = (100 * s.processed / s.total) + "%";
  $("alerts").textContent = s.alerts;
  $("latency").textContent = s.predict_mean_ms === null ? "— ms" : `${fmt(s.predict_mean_ms, 2)} ms (p95 ${fmt(s.predict_p95_ms, 2)})`;
  // matriz y aporte
  const c = s.counts;
  for (const k of ["TN", "FP", "FN", "TP"]) $("cm-" + k.toLowerCase()).textContent = c[k].toLocaleString("es-PE");
  $("caught").textContent = c.TP; $("real").textContent = c.TP + c.FN;
  $("counts").textContent = `Aciertos sin falla: ${c.TN} · Fallas detectadas: ${c.TP} · Falsas alarmas: ${c.FP} · Fallas omitidas: ${c.FN}`;
  const m = $("match");
  if (s.status === "completed" && projectMetrics) {
    const ok = c.TP === projectMetrics.true_positive && c.FN === projectMetrics.false_negative && c.FP === projectMetrics.false_positive && c.TN === projectMetrics.true_negative;
    m.hidden = false; m.dataset.ok = String(ok);
    m.textContent = ok ? `✓ Los ${s.total.toLocaleString("es-PE")} registros reproducidos coinciden con la evaluación del informe: ${c.TP} detectadas, ${c.FN} omitidas, ${c.FP} falsas alarmas.` : "La reproducción terminó; revisa las comprobaciones: los conteos no coinciden con la evaluación registrada.";
  } else m.hidden = true;
  const ac = s.ae_counts, box = $("ae-score");
  if (ac) {
    box.hidden = false;
    $("ae-score-text").textContent = s.processed ? `Alertó en ${ac.TP + ac.FP} registros: ${ac.TP} eran fallas reales y ${ac.FP} no. Coincidió con el árbol en ${ac.both}, alertó solo él en ${ac.only_ae} y rescató ${ac.rescued} ${ac.rescued === 1 ? "falla que el árbol había omitido" : "fallas que el árbol había omitido"}.` : "Aún no hay registros procesados.";
  } else box.hidden = true;
  // hojas más visitadas
  hits = s.node_hits || []; maxHits = hits.reduce((a, b) => Math.max(a, b), 0);
  // historial
  const body = $("history"); body.replaceChildren();
  if (!s.recent.length) { const tr = document.createElement("tr"), td = document.createElement("td"); td.colSpan = 7; td.textContent = "Todavía no hay registros procesados."; tr.append(td); body.append(tr); }
  for (const r of s.recent) {
    const tr = document.createElement("tr"); tr.dataset.outcome = r.outcome;
    [r.UDI, r.Type, r.prediction ? "Con falla" : "Sin falla", r["Machine failure"] ? "Con falla" : "Sin falla", outcomes[r.outcome], `${r.leaf_fail}/${r.leaf_n}`, r.predict_ms.toFixed(2)]
      .forEach((v, i) => { const td = document.createElement("td"); td.textContent = v; if (i === 2) td.dataset.alert = String(r.alert); if (i === 4) td.dataset.outcome = r.outcome; tr.append(td); });
    body.append(tr);
  }
  drawLanes(s.series);
  if (s.error) showError(s.error);
  applyControls();
  // escena
  if (mode === "play" && view === "test") {
    if (!s.last) { if (prev?.last || shown) idle(); lastShownKey = null; }
    else if (key(s) !== lastShownKey) {
      lastShownKey = key(s); showEntry(entryFromRecord(s.last));
      $("identity").textContent = `UDI ${s.last.UDI} · Tipo de producto ${s.last.Type}`;
    }
  }
  window.dispatchEvent(new CustomEvent("simulation-state", {detail: s}));
}

/* ---------- Red ---------- */
async function request(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "No se pudo completar la solicitud.");
  return result;
}
async function action(path, data = {}) {
  if (busy) return false;
  busy = true; generation++; showError(""); applyControls();
  try { render(await request(path, data)); return true; }
  catch (e) { showError(e.message); return false; }
  finally { busy = false; applyControls(); }
}
async function poll() {
  if (polling || busy) return;
  polling = true; const g = generation;
  try { const s = await request("/api/state"); if (!busy && g === generation) render(s); }
  catch (e) { if (!busy && g === generation) { showError(e instanceof TypeError ? "No hay conexión con el servidor. Espera un momento y comprueba tu conexión; si usas la versión local, revisa su terminal." : e.message); lastState = null; applyControls(); } }
  finally { polling = false; }
}

/* ---------- Interacción ---------- */
function nodeAt(mx, my) {
  let best = -1, bd = 11 * 11;
  for (let i = 0; i < M.nodes.length; i++) { const dx = px(i) - mx, dy = py(i) - my, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = i; } }
  return best;
}
function onMove(e) {
  if (!M) return;
  const r = canvas.getBoundingClientRect(), i = nodeAt(e.clientX - r.left, e.clientY - r.top), tip = $("tree-tip");
  hover = i; canvas.style.cursor = i >= 0 ? "help" : "default";
  if (i < 0) { tip.hidden = true; return; }
  const nd = M.nodes[i];
  const head = isLeaf(i) ? (leafFails(i) ? "Hoja: predice falla" : "Hoja: predice sin falla") : question(i).text;
  tip.replaceChildren();
  const b = document.createElement("b"); b.textContent = head;
  const s = document.createElement("span"); s.textContent = `${nd.n.toLocaleString("es-PE")} casos de entrenamiento · ${nd.fail.toLocaleString("es-PE")} con falla` + (hits[i] ? ` · ${hits[i]} registros de esta sesión` : "");
  tip.append(b, s); tip.hidden = false;
  const tw = tip.offsetWidth; let x = e.clientX - r.left + 14; if (x + tw > r.width - 6) x = e.clientX - r.left - tw - 14;
  tip.style.left = Math.max(6, x) + "px"; tip.style.top = Math.max(6, e.clientY - r.top - 12) + "px";
}
canvas.addEventListener("pointermove", onMove);
canvas.addEventListener("pointerleave", () => { hover = -1; $("tree-tip").hidden = true; });

$("start").addEventListener("click", () => view === "test" && action("/api/start", {interval: Number($("interval").value)}));
$("pause").addEventListener("click", () => view === "test" && action("/api/pause"));
$("step").addEventListener("click", () => view === "test" && action("/api/step"));
$("reset").addEventListener("click", () => { if (view !== "test") return; const m = $("load-message"); if (m) m.textContent = ""; lastShownKey = null; action("/api/reset"); });
$("mode-play").addEventListener("click", () => mode !== "play" && setMode("play"));
$("mode-lab").addEventListener("click", () => mode !== "lab" && setMode("lab"));
$("lab-sync").addEventListener("click", () => { if (lastState?.last) { labValues = entryFromRecord(lastState.last).values; setSensorValues(labValues); runLab(true); } });
document.querySelectorAll("#type-buttons button").forEach(b => b.addEventListener("click", () => { if (mode !== "lab") return; labValues.Type = b.dataset.type; setSensorValues(labValues); runLab(false); }));
$("load")?.addEventListener("click", async () => {
  const file = $("csv").files[0], msg = $("load-message"); msg.textContent = "";
  if (!file) { showError("Selecciona un archivo CSV de prueba."); return; }
  if (file.size > 1_000_000) { showError("El archivo supera el límite de 1 MB."); return; }
  try { lastShownKey = null; if (await action("/api/load", {csv: await file.text()})) msg.textContent = "CSV válido. Reserva verificada y sesión reiniciada."; }
  catch (e) { showError(`No se pudo leer el archivo: ${e.message}`); }
});
function setView(next) {
  if (next === view) return;
  view = next; $("lab").dataset.view = next;
  $("view-plant").setAttribute("aria-pressed", String(next === "plant")); $("view-test").setAttribute("aria-pressed", String(next === "test"));
  showError("");
  if (next === "test") {
    $("stage-kicker").textContent = "EL MODELO POR DENTRO · ÁRBOL DE DECISIÓN";
    $("r-sub").textContent = "Las preguntas del camino, en orden.";
    setMode(mode); if (lastState) render(lastState); applyControls();
    $("start").textContent = lastState?.status === "paused" ? "Continuar" : "Iniciar simulación";
  }
  window.dispatchEvent(new CustomEvent("view-change", {detail: next}));
  requestAnimationFrame(resize);
}
$("view-plant").addEventListener("click", () => setView("plant"));
$("view-test").addEventListener("click", () => setView("test"));
new ResizeObserver(resize).observe($("tree-wrap"));
window.addEventListener("portal-panel", () => requestAnimationFrame(resize));
reduceMotion.addEventListener?.("change", () => { if (shown) shown.instant = reduceMotion.matches; });

/* ---------- Arranque ---------- */
(async () => {
  applyControls();
  try {
    M = await request("/api/model");
    layoutTree(); buildSensors(); setMode("play"); idle();
    $("tree-meta").textContent = `${M.nodes.length} nodos · ${M.leaves} hojas · ${M.depth} niveles · aprendido con ${M.train_rows.toLocaleString("es-PE")} observaciones (${M.train_failures} con falla).`;
    if (M.autoencoder) {
      $("ae-card").hidden = false; renderAE(null);
      const ev = M.autoencoder.evaluation, a = ev.autoencoder_alone, t = ev.tree_alone, o = ev.tree_or_autoencoder;
      $("ae-eval").textContent = `Evaluación con las ${a.true_negative + a.false_positive + a.false_negative + a.true_positive} observaciones de prueba: solo, el autoencoder detecta ${a.true_positive} de ${a.true_positive + a.false_negative} fallas con ${a.false_positive} falsas alarmas (sensibilidad ${pct(a.recall)}, AUC ${fmt(ev.auc_roc, 2)}); el árbol detecta ${t.true_positive} de ${t.true_positive + t.false_negative}. Es un detector más débil porque en estos datos las fallas dependen de combinaciones de mediciones más que de ser registros raros. Combinarlo con el árbol rescata ${ev.tree_missed_caught_by_autoencoder} de ${ev.tree_missed_failures} fallas omitidas, pero agrega ${o.false_positive - t.false_positive} falsas alarmas: por eso es una segunda opinión y no reemplaza al árbol. Umbral y arquitectura se eligieron solo con datos de desarrollo.`;
    }
    resize();
    requestAnimationFrame(frame);
    window.dispatchEvent(new Event("lab-ready"));
  } catch (e) { showError("No se pudo cargar el modelo: " + e.message); }
  projectMetrics = M && M.reference ? M.reference : null;
  poll(); setInterval(poll, 300);
})();
