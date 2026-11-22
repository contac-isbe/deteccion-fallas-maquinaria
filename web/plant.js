"use strict";
/* Vista «Planta en vivo»: 12 máquinas simuladas, gemelo digital y marcador de la IA frente a la realidad.
   Depende de lab.js (M, shown, showEntry, buildSteps, renderAE, finishDecision, request, fmt, pct, $...). */
const PLANT_SEED = 12;     // misma historia cada vez que se reinicia (útil para ensayar la exposición)
const P = {state: null, sel: 0, running: false, timer: 0, busy: false, drag: false, sceneKey: "", ready: false};
const CAUSE_SHORT = {OSF: "Sobretensión", PWF: "Potencia", HDF: "Calor", TWF: "Desgaste de herramienta"};
const KNOWN_RULES = [
  {feat: "Power [W]", real: 9000, label: "Potencia máxima", unit: "W"},
  {feat: "Power [W]", real: 3500, label: "Potencia mínima", unit: "W"},
  {feat: "Temp diff [K]", real: 8.6, label: "Diferencia de temperatura", unit: "K"},
  {feat: "Rotational speed [rpm]", real: 1380, label: "Velocidad mínima", unit: "rpm"},
  {feat: "Wear x torque [minNm]", real: 11000, label: "Sobretensión (tipo L)", unit: "min·Nm"},
];

const esc = t => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const interval = () => Math.round(Number($("interval").value) * 1000);

/* ---------- Ciclo de la simulación ---------- */
async function plantTick() {
  if (P.busy) return;
  P.busy = true;
  try { renderPlant(await request("/api/plant/tick", {sel: P.sel})); showError(""); }
  catch (e) { showError(e.message); stopPlant(); }
  finally { P.busy = false; }
}
function loop() {
  if (!P.running || view !== "plant") return;
  plantTick().finally(() => { if (P.running) P.timer = setTimeout(loop, interval()); });
}
function startPlant() { if (P.running) return; P.running = true; plantControls(); loop(); }
function stopPlant() { P.running = false; clearTimeout(P.timer); plantControls(); if (P.state) statusLine(P.state); }
function plantControls() {
  if (view !== "plant") return;
  $("start").disabled = P.running; $("start").textContent = P.state && P.state.t > 0 && !P.running ? "Continuar" : "Iniciar simulación";
  $("pause").disabled = !P.running; $("step").disabled = P.running; $("reset").disabled = false;
  $("interval").disabled = false; $("plant-new").disabled = false;
}
function statusLine(s) {
  $("status").textContent = P.running ? "Planta en marcha" : s.t === 0 ? "Planta lista" : "Planta en pausa";
  $("run-dot").dataset.state = P.running ? "running" : s.t === 0 ? "ready" : "paused";
  $("status-plant").textContent = `Paso ${s.t} · ${s.counts.run} en marcha · ${s.counts.alert} con alerta · ${s.counts.down} detenidas`;
}

/* ---------- Dibujo de la planta ---------- */
function sparkline(values) {
  if (!values.length) return "";
  const w = 100, h = 22, step = w / Math.max(1, 39);
  const pts = values.map((v, i) => `${((i + 40 - values.length) * step).toFixed(1)},${(h - 2 - v * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2="${w}" y1="${h / 2}" y2="${h / 2}" class="spark-mid"/><polyline points="${pts}"/></svg>`;
}
function renderTiles(s) {
  const grid = $("plant-grid");
  if (grid.children.length !== s.machines.length) {
    grid.replaceChildren(...s.machines.map(m => { const b = document.createElement("button"); b.type = "button"; b.className = "tile"; b.dataset.id = m.id; return b; }));
  }
  s.machines.forEach(m => {
    const b = grid.children[m.id], down = m.status === "down", warn = m.fc_alert || m.alert, state = down ? "down" : warn ? "alert" : "run";
    b.dataset.state = state; b.setAttribute("aria-pressed", String(m.id === P.sel));
    b.setAttribute("aria-label", `${m.name}, ${down ? "detenida por " + (m.cause_text || "falla") : warn ? "con pronóstico de falla" : "en marcha"}, riesgo de falla próxima ${Math.round(m.fc * 100)} por ciento`);
    const badge = down ? `⛔ Detenida · ${esc(CAUSE_SHORT[m.cause] || "falla")}` : m.fc_alert ? "⚠ Falla probable pronto" : m.alert ? "⛔ Condición de falla" : "● En marcha";
    b.innerHTML = `<span class="tile-top"><b>${esc(m.name)}</b><span class="tile-type" title="Calidad del producto que fabrica: L baja, M media, H alta">Calidad ${m.type}</span></span>
      <span class="tile-badge">${badge}</span>
      <span class="tile-risk"><span class="bar"><i style="width:${Math.max(2, m.fc * 100)}%"></i></span><span>Falla en ≤ ${(P.state.forecast || {horizon: 12}).horizon} pasos: ${Math.round(m.fc * 100)} %</span></span>
      ${sparkline(m.spark)}
      <span class="tile-meta">${m.rpm == null ? "—" : fmt(m.rpm, 0) + " rpm · " + fmt(m.torque, 0) + " Nm · desgaste " + fmt(m.wear, 0)}</span>
      <span class="tile-ae" ${m.ae_alert && !down ? "" : "hidden"}>◐ Estado inusual (autoencoder)</span>
      ${down ? `<span class="tile-down">Vuelve en ${m.down_left} pasos</span>` : ""}`;
  });
}

function renderScore(s) {
  const st = s.stats, f = st.failures, fc = s.forecast, te = fc && fc.test;
  const horizon = fc ? fc.horizon : 12;
  const lead = st.mean_fc_lead != null ? `${fmt(st.mean_fc_lead, 1)} pasos` : "—";
  const ref = te && te.recall != null ? `<p class="lab-fine">En 40 simulaciones nuevas (${te.failures.toLocaleString("es-PE")} fallas) que el modelo nunca vio, anticipó el <b>${Math.round(te.recall * 100)} %</b> con una mediana de ${fmt(te.median_lead, 0)} pasos de adelanto. Si se le quita la tendencia y solo mira el valor actual, las falsas alarmas se multiplican por ${fmt(te.flat_false_per_1000 / te.false_per_1000, 0)}.</p>` : "";
  $("ps-body").innerHTML = `<div class="ps-grid">
      <div><b>${f}</b><span>fallas ocurridas</span></div><div data-k="ok"><b>${st.fc_warned}</b><span>anticipadas por la IA</span></div>
      <div data-k="bad"><b>${st.fc_missed}</b><span>no anticipadas</span></div><div data-k="warn"><b>${st.fc_false}</b><span>falsas alarmas</span></div></div>
    <p>${st.fc_warned ? `Adelanto medio: <b>${lead}</b> antes de la falla (el máximo posible es ${horizon}).` : `Cuando una máquina esté por fallar, aquí verás si la IA lo anticipó.`}${st.averted ? ` El operador evitó <b>${st.averted}</b> ${st.averted === 1 ? "falla" : "fallas"} al corregir a tiempo.` : ""}</p>
    <p class="lab-fine">El árbol, que solo mira la lectura actual, marcó ${st.detected} de ${f} fallas, siempre en el mismo instante en que ocurrían: sirve para confirmar, no para anticipar. El autoencoder vio un estado inusual antes de ${st.ae_detected} de ${f}.</p>${ref}
    <p class="lab-fine">El desgaste de herramienta falla al azar entre 200 y 240 min: es lo más difícil de anticipar, y la IA solo puede avisar que la herramienta ya está en la zona de riesgo.</p>`;
}
function renderRulesLearned() {
  const rows = KNOWN_RULES.map(r => {
    const k = M.features.indexOf(r.feat), thr = M.nodes.filter(n => n.f === k).map(n => n.t);
    if (!thr.length) return "";
    const near = thr.reduce((a, b) => Math.abs(b - r.real) < Math.abs(a - r.real) ? b : a), err = Math.abs(near - r.real) / r.real;
    return `<tr><th scope="row">${r.label}</th><td>${fmtT(r.real)} ${r.unit}</td><td data-ok="${err < .03}">${fmtT(near)}</td></tr>`;
  }).join("");
  $("pr-body").innerHTML = `<table class="pr-table"><thead><tr><th></th><th>Regla real</th><th>Corte del árbol</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="lab-fine">El modelo nunca recibió estas reglas: solo vio lecturas y si hubo falla. Los cortes salen de ${M.train_rows.toLocaleString("es-PE")} observaciones.</p>`;
}
function renderLog(s) {
  const ol = $("plant-log"); ol.replaceChildren();
  if (!s.log.length) { ol.innerHTML = '<li class="muted">Todavía no ha pasado nada. Pulsa «Iniciar simulación».</li>'; return; }
  s.log.forEach(e => { const li = document.createElement("li"); li.dataset.kind = e.kind; li.innerHTML = `<span class="lt">paso ${e.t}</span>${esc(e.text)}`; ol.append(li); });
}

/* ---------- Gemelo digital ---------- */
function twinSvg(sel) {
  const x = sel.reading, down = sel.status === "down";
  if (!x) return "";
  const rpm = x["Rotational speed [rpm]"], wear = x["Tool wear [min]"], air = x["Air temperature [K]"], proc = x["Process temperature [K]"];
  const dur = Math.max(.12, 2400 / Math.max(rpm, 100)), tube = t => Math.max(2, Math.min(74, (t - 295) / 20 * 74));
  const shorten = Math.min(7, wear / 250 * 7), hot = proc > 312 ? "var(--fail)" : "var(--warn)";
  const col = (sel.fc_alert || sel.alert) ? "var(--fail)" : down ? "var(--muted)" : "var(--ok)";
  const flow = Math.min(1, Math.max(.25, sel.setpoints.cool / 12));
  return `<svg viewBox="0 0 320 244" aria-hidden="true">
    <rect class="tw-bed" x="12" y="190" width="240" height="14" rx="4"/>
    <rect class="tw-col" x="22" y="26" width="34" height="164" rx="5"/>
    <rect class="tw-head" x="56" y="40" width="124" height="62" rx="9" style="stroke:${col}"/>
    <g class="tw-spin ${down ? "paused" : ""}" style="animation-duration:${dur.toFixed(2)}s;transform-origin:92px 71px"><circle cx="92" cy="71" r="21" class="tw-chuck"/>
      <rect x="90" y="52" width="4" height="38" class="tw-spoke"/><rect x="73" y="69" width="38" height="4" class="tw-spoke"/><circle cx="92" cy="71" r="4" class="tw-hub"/></g>
    <text class="tw-s" x="92" y="98" text-anchor="middle" style="fill:var(--muted)">husillo</text>
    <rect class="tw-spindle" x="136" y="102" width="22" height="22" rx="3"/>
    <rect class="tw-holder" x="140" y="124" width="14" height="12" rx="2"/>
    <rect class="tw-mill ${down ? "" : "cutting"}" x="144" y="136" width="6" height="${28 - shorten}" rx="1"/>
    <rect class="tw-work" x="96" y="166" width="104" height="24" rx="3"/>
    <rect class="tw-table" x="72" y="186" width="176" height="6" rx="2"/>
    <path class="tw-cool ${down ? "" : "flow"}" d="M176 102 Q192 108 168 146" style="opacity:${flow}"/>
    <text class="tw-t" x="12" y="14">Potencia ${fmt(sel.rules[0].value, 0)} W · ${fmt(rpm, 0)} rpm</text>
    <g transform="translate(262,26)"><rect class="tw-tube" x="0" y="0" width="14" height="78" rx="7"/><rect x="2" y="${76 - tube(air)}" width="10" height="${tube(air)}" rx="5" fill="var(--cyan)"/>
      <rect class="tw-tube" x="24" y="0" width="14" height="78" rx="7"/><rect x="26" y="${76 - tube(proc)}" width="10" height="${tube(proc)}" rx="5" fill="${hot}"/>
      <text class="tw-s" x="7" y="92" text-anchor="middle">Aire</text><text class="tw-s" x="31" y="92" text-anchor="middle">Proc.</text>
      <text class="tw-s" x="7" y="103" text-anchor="middle">${fmt(air, 0)}</text><text class="tw-s" x="31" y="103" text-anchor="middle">${fmt(proc, 0)}</text><text class="tw-s" x="19" y="114" text-anchor="middle">K</text></g>
    <text class="tw-t" x="12" y="216">Desgaste de la fresa: ${fmt(wear, 0)} min</text>
    <rect class="tw-wearbg" x="12" y="223" width="200" height="9" rx="4.5"/>
    <rect x="12" y="223" width="${Math.min(200, wear / 260 * 200)}" height="9" rx="4.5" fill="${wear >= 200 ? "var(--fail)" : "var(--accent)"}"/>
    <rect x="${12 + 200 / 260 * 200}" y="220" width="${200 / 260 * 40}" height="15" class="tw-zone"/>
    <text class="tw-s" x="${12 + 200 / 260 * 200 - 30}" y="242">200–240: falla al azar</text>
    ${down ? `<rect x="0" y="0" width="320" height="244" class="tw-down"/><text x="160" y="120" text-anchor="middle" class="tw-downtxt">DETENIDA</text><text x="160" y="142" text-anchor="middle" class="tw-s2">${esc(sel.cause_text || "")}</text>` : ""}
  </svg>`;
}
function renderRulesTwin(sel) {
  $("twin-rules").innerHTML = sel.rules.map(r => {
    const span = r.max - r.min, pos = v => Math.max(0, Math.min(100, (v - r.min) / span * 100));
    let bands;
    if (r.id === "TWF") bands = `background:linear-gradient(90deg,var(--ok-soft) 0 ${pos(200)}%,var(--warn-soft) ${pos(200)}% ${pos(240)}%,var(--fail-soft) ${pos(240)}% 100%)`;
    else { const a = pos(r.safe[0]), b = pos(r.safe[1]); bands = `background:linear-gradient(90deg,var(--fail-soft) 0 ${a}%,var(--ok-soft) ${a}% ${b}%,var(--fail-soft) ${b}% 100%)`; }
    return `<div class="rule" data-bad="${r.bad}"><div class="rule-top"><span>${r.label}</span><b>${fmt(r.value, r.id === "HDF" ? 2 : 0)} ${r.unit}</b></div>
      <div class="rule-track" style="${bands}"><i style="left:${pos(r.value)}%"></i></div>
      <div class="rule-foot"><span>${esc(r.rule)}</span><em>${r.bad ? "⚠ Se incumple" : "✓ Segura"}</em></div></div>`;
  }).join("");
}
function renderControls(sel) {
  const down = sel.status === "down", sp = sel.setpoints;
  if (!P.drag) {
    $("c-rpm").value = sp.rpm; $("c-power").value = sp.power; $("c-cool").value = sp.cool;
    $("o-rpm").textContent = `${fmt(sp.rpm, 0)} rpm`; $("o-power").textContent = `${fmt(sp.power, 0)} W`; $("o-cool").textContent = `${fmt(sp.cool, 1)} K`;
  }
  ["c-rpm", "c-power", "c-cool", "a-tool", "a-safe"].forEach(id => $(id).disabled = down);
  $("a-restart").hidden = !down;
}
function chartSvg(sel) {
  const h = sel.history, n = 150, W = 720, left = 112, right = 8, pw = W - left - right, ph = 44, gap = 14;
  const len = h.risk.length, x = i => left + (n - len + i) / (n - 1) * pw;
  const type = sel.reading ? sel.reading.Type : "L", lim = {L: 11000, M: 12000, H: 13000}[type];
  const thr = sel.ae ? sel.ae.threshold : 0, aeMax = Math.max(thr * 3, ...h.ae, 1e-6);
  const strain = h.wear.map((w, i) => w * h.torque[i]);
  const panels = [
    {name: "Falla próxima (pronóstico)", unit: "%", vals: h.fc, max: 1, line: sel.forecast ? sel.forecast.threshold : .5, fmt: v => Math.round(v * 100) + " %", color: "var(--fail)", area: true},
    {name: "Potencia", unit: "W", vals: h.power, max: 11500, band: [3500, 9000], fmt: v => fmt(v, 0) + " W", color: "var(--cyan)"},
    {name: "Desgaste × torque", unit: "", vals: strain, max: 15000, line: lim, fmt: v => fmt(v, 0), color: "var(--accent)"},
    {name: "Error del autoencoder", unit: "", vals: h.ae, max: aeMax, line: thr, fmt: v => fmt(v, 3), color: "var(--warn)"},
  ];
  let s = `<svg viewBox="0 0 ${W} ${panels.length * (ph + gap) + 6}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">`;
  panels.forEach((p, k) => {
    const y0 = 6 + k * (ph + gap), y = v => y0 + ph - Math.min(1, Math.max(0, v / p.max)) * ph;
    s += `<rect x="${left}" y="${y0}" width="${pw}" height="${ph}" class="ch-bg"/>`;
    if (p.band) s += `<rect x="${left}" y="${y(p.band[1])}" width="${pw}" height="${y(p.band[0]) - y(p.band[1])}" class="ch-safe"/>`;
    h.fc.forEach((a, i) => { if (sel.forecast && a >= sel.forecast.threshold) s += `<rect x="${x(i) - pw / n / 2}" y="${y0}" width="${Math.max(2, pw / n)}" height="${ph}" class="ch-alert"/>`; });
    if (p.line != null) s += `<line x1="${left}" x2="${left + pw}" y1="${y(p.line)}" y2="${y(p.line)}" class="ch-line"/>`;
    if (len > 1) {
      const pts = p.vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
      s += `<polyline points="${pts}" class="ch-pl" style="stroke:${p.color}"/>`;
    }
    h.fail.forEach((f, i) => { if (f) s += `<line x1="${x(i)}" x2="${x(i)}" y1="${y0}" y2="${y0 + ph}" class="ch-fail"/>`; });
    s += `<text x="0" y="${y0 + 13}" class="ch-t">${p.name}</text><text x="0" y="${y0 + 28}" class="ch-v">${len ? p.fmt(p.vals[len - 1]) : "—"}</text>`;
  });
  h.fail.forEach((f, i) => { if (f) s += `<text x="${x(i)}" y="${panels.length * (ph + gap) + 2}" class="ch-x" text-anchor="middle">✕</text>`; });
  return s + "</svg>";
}
function renderTwin(sel) {
  $("twin-title").textContent = `${sel.name} · Calidad ${sel.type}`;
  $("twin-sub").textContent = `Escenario de esta simulación: ${sel.profile_text}.` + (sel.profile === "saludable" ? "" : " (Se genera a propósito para que la IA tenga algo que vigilar.)");
  const t = $("twin-state"), down = sel.status === "down";
  t.dataset.state = down ? "down" : (sel.fc_alert || sel.alert) ? "alert" : "run";
  t.textContent = down ? `⛔ Detenida · ${sel.cause_text}` : (sel.fc_alert || sel.alert) ? "⚠ La IA pronostica falla" : "● En marcha";
  $("twin-svg").innerHTML = twinSvg(sel);
  renderRulesTwin(sel); renderControls(sel);
  renderForecast(sel);
  $("twin-chart").innerHTML = chartSvg(sel);
}
function renderForecast(sel) {
  const f = sel.forecast, box = $("twin-forecast");
  if (!f) { box.innerHTML = ""; return; }
  const pct = Math.round(f.p * 100), thr = Math.round(f.threshold * 100), down = sel.status === "down";
  const why = f.why.filter(w => w.drop >= .02).slice(0, 4), top = Math.max(.01, ...why.map(w => w.drop));
  const msg = down ? "La máquina está detenida." : f.alert ? `La IA pronostica que esta máquina fallará en los próximos ${f.horizon} pasos si nada cambia.` : pct >= 15 ? "Riesgo moderado: la IA la sigue de cerca." : "Sin señales de falla cercana.";
  box.dataset.state = down ? "down" : f.alert ? "alert" : "ok";
  box.innerHTML = `<div class="fc-gauge"><span class="lab-kicker">PRONÓSTICO · PRÓXIMOS ${f.horizon} PASOS</span>
      <div class="fc-num"><b>${pct} %</b><span>de probabilidad de falla</span></div>
      <div class="fc-bar"><i style="width:${Math.max(1, pct)}%"></i><u style="left:${thr}%"><em>umbral ${thr} %</em></u></div>
      <p>${msg}</p></div>
    <div class="fc-why"><span class="lab-kicker">QUÉ EMPUJA EL RIESGO</span>
      ${why.length ? why.map(w => `<div class="fc-row"><span>${esc(w.group)}</span><span class="fc-track"><i style="width:${Math.round(w.drop / top * 100)}%"></i></span><em>−${Math.round(w.drop * 100)} pts</em></div>`).join("") : '<p class="lab-fine">Ningún factor destaca: todas las variables están en rangos normales.</p>'}
      <p class="lab-fine">Cuántos puntos de riesgo bajarían si ese factor tuviera valores normales. La IA nunca recibió las reglas: lo aprendió de la tendencia de las lecturas.</p></div>`;
}

/* ---------- Escena del modelo para la máquina elegida ---------- */
function plantScene(s) {
  const sel = s.selected;
  if (!sel.reading || !sel.path.length) return;
  const bad = sel.rules.some(r => r.bad), alert = sel.p_fail > .5, down = sel.status === "down";
  const outcome = alert ? (bad ? "TP" : "FP") : (bad ? "FN" : "TN");
  const cause = sel.rules.filter(r => r.bad).map(r => r.label.toLowerCase()).join(" y ");
  const entry = {
    trace: {path: sel.path, leaf: sel.leaf, leaf_n: sel.leaf_n, leaf_fail: sel.leaf_fail, p_fail: sel.p_fail},
    values: sel.reading, label: "plant", udi: sel.name, t: s.t, ae: sel.ae, outcome, down, cause: sel.cause_text,
    truthText: down ? `Máquina detenida: ${sel.cause_text}. Se reinicia sola en ${sel.down_left} pasos o desde los controles.`
      : bad ? `Realidad de la planta: se incumple una regla física (${cause}). ${alert ? "La IA lo detectó." : "La IA NO lo detectó."}`
      : alert ? "Realidad de la planta: ninguna regla física se incumple en este instante, pero la IA alerta (falsa alarma)."
      : "Realidad de la planta: ninguna regla física se incumple.",
  };
  const key = `${sel.id}|${sel.path.join(",")}|${sel.status}`;
  if (key !== P.sceneKey) {
    P.sceneKey = key; showEntry(entry);
    $("stage-kicker").textContent = `EL DETECTOR (ÁRBOL) · ${sel.name}`;
    $("r-sub").textContent = `${sel.path.length - 1} preguntas sobre las lecturas de ${sel.name}.`;
  } else {
    entry.start = shown ? shown.start : performance.now(); entry.instant = shown ? shown.instant : false;
    const done = !shown || finishedFor === shown;
    shown = entry; finishedFor = done ? null : finishedFor;
    buildSteps(entry); if (done) $("steps").querySelectorAll(".step").forEach(li => li.classList.add("on"));
    renderAE(entry, true); if (done) finishDecision();
  }
}

function renderPlant(s) {
  P.state = s; P.ready = true;
  statusLine(s);
  $("pk-t").textContent = s.t; $("pk-run").textContent = s.counts.run; $("pk-alert").textContent = s.counts.alert; $("pk-down").textContent = s.counts.down;
  renderTiles(s); renderScore(s); renderLog(s); renderTwin(s.selected); plantScene(s); plantControls();
}

/* ---------- Interacción ---------- */
async function selectMachine(id) {
  if (id === P.sel && P.state) return;
  P.sel = id; P.drag = false;
  try { renderPlant(await request(`/api/plant?sel=${id}`)); } catch (e) { showError(e.message); }
}
async function control(data) {
  try { renderPlant(await request("/api/plant/control", {id: P.sel, sel: P.sel, ...data})); showError(""); } catch (e) { showError(e.message); }
}
async function resetPlant(seed) {
  stopPlant(); P.sceneKey = ""; P.sel = 0;
  try { renderPlant(await request("/api/plant/reset", seed == null ? {sel: 0} : {seed, sel: 0})); showError(""); } catch (e) { showError(e.message); }
}
function initPlant() {
  renderRulesLearned();
  $("plant-grid").addEventListener("click", e => { const b = e.target.closest(".tile"); if (b) selectMachine(Number(b.dataset.id)); });
  [["c-rpm", "o-rpm", v => `${fmt(v, 0)} rpm`], ["c-power", "o-power", v => `${fmt(v, 0)} W`], ["c-cool", "o-cool", v => `${fmt(v, 1)} K`]].forEach(([id, out, f]) => {
    const el = $(id);
    el.addEventListener("input", () => { P.drag = true; $(out).textContent = f(Number(el.value)); });
    el.addEventListener("change", () => { P.drag = false; control({[id.slice(2)]: Number(el.value)}); });
  });
  $("a-tool").addEventListener("click", () => control({action: "tool"}));
  $("a-safe").addEventListener("click", () => control({action: "stabilize"}));
  $("a-restart").addEventListener("click", () => control({action: "restart"}));
  $("start").addEventListener("click", () => view === "plant" && startPlant());
  $("pause").addEventListener("click", () => view === "plant" && stopPlant());
  $("step").addEventListener("click", () => view === "plant" && plantTick());
  $("reset").addEventListener("click", () => view === "plant" && resetPlant(PLANT_SEED));
  $("plant-new").addEventListener("click", () => resetPlant(null));
  enterPlant();
}
async function enterPlant() {
  $("stage-kicker").textContent = P.state ? `EL DETECTOR (ÁRBOL) · ${P.state.selected.name}` : "EL DETECTOR · ÁRBOL DE DECISIÓN";
  $("stage-title").textContent = "El árbol confirma si la lectura actual ya es una falla";
  try { P.sceneKey = ""; renderPlant(await request(`/api/plant?sel=${P.sel}`)); } catch (e) { showError(e.message); }
}
/* ---------- Asistente ---------- */
const CHIPS = ["¿Qué hago con esta fresadora?", "¿Por qué sube el riesgo?", "¿Cuánto tiempo tengo?", "¿Puedo seguir produciendo?", "¿Qué fresadora atiendo primero?"];
function chat(kind, html) {
  const log = $("as-log"), el = document.createElement("div");
  el.className = `as-msg ${kind}`; el.innerHTML = html;
  if (kind === "q" || !P.pair) { P.pair = document.createElement("div"); P.pair.className = "as-pair"; log.prepend(P.pair); }
  P.pair.append(el);
  while (log.children.length > 6) log.lastChild.remove();
  return el;
}
function actionRow(a, i, idle) {
  const to = a.p == null ? "" : Math.round(a.p * 100), from = idle == null ? "" : Math.round(idle * 100);
  const bar = a.p == null ? "" : `<span class="as-bars"><span class="as-from" style="width:${from}%"></span><span class="as-to" style="width:${Math.max(1, to)}%"></span></span><em>${from} % → <b>${to} %</b></em>`;
  return `<li><div><b>${esc(a.label)}</b>${bar}</div><button type="button" class="as-apply" data-i="${i}">Aplicar</button></li>`;
}
function renderAnswer(r) {
  $("as-mode").textContent = r.mode === "claude" ? "Claude redacta · tu modelo calcula" : "Asistente propio · sin internet";
  let h = `<p>${esc(r.text)}</p>`;
  if (r.ranking) h += `<ol class="as-rank">${r.ranking.map(x => `<li><button type="button" class="link" data-pick="${x.id}">${esc(x.name)}</button> <em>${Math.round(x.p * 100)} %</em></li>`).join("")}</ol>`;
  if (r.actions && r.actions.length) h += `<p class="as-h">Acciones probadas con el pronosticador${r.p_idle != null ? ` (si no haces nada: <b>${Math.round(r.p_idle * 100)} %</b>)` : ""}</p><ul class="as-actions">${r.actions.map((a, i) => actionRow(a, i, r.p_idle)).join("")}</ul>`;
  if (r.notes && r.notes.length) h += r.notes.map(n => `<p class="lab-fine">${esc(n)}</p>`).join("");
  if (r.check && r.understood !== "planta" && r.status !== "down" || r.status === "down") h += `<details class="as-check"><summary>Qué revisar en la fresadora real</summary><ul>${r.check.map(c => `<li>${esc(c)}</li>`).join("")}</ul><p class="lab-fine">Para prevenir: ${esc(r.prevent)}</p></details>`;
  if (r.understood == null) h += `<div class="as-sug">${r.suggest.map(q => `<button type="button" class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>`;
  const el = chat("a", h);
  el.querySelectorAll(".as-apply").forEach(b => b.addEventListener("click", async () => {
    const a = r.actions[Number(b.dataset.i)]; b.disabled = true;
    if (r.machine != null && r.machine !== P.sel) await selectMachine(r.machine);
    await control(a.apply);
    const m = P.state && P.state.machines[r.machine];
    b.textContent = "Aplicado ✓";
    chat("sys", `Aplicado en ${esc(r.name)}: ${esc(a.label)}.${m ? ` Riesgo ahora: ${Math.round(m.fc * 100)} %.` : ""}`);
  }));
  el.querySelectorAll("[data-pick]").forEach(b => b.addEventListener("click", () => selectMachine(Number(b.dataset.pick))));
  el.querySelectorAll("[data-q]").forEach(b => b.addEventListener("click", () => ask(b.dataset.q)));
  if (r.machine != null && r.named && r.machine !== P.sel) selectMachine(r.machine);
}
async function ask(q) {
  q = String(q || "").trim(); if (!q) return;
  chat("q", esc(q)); $("as-q").value = ""; $("as-send").disabled = true;
  try { renderAnswer(await request("/api/plant/assistant", {question: q, sel: P.sel})); showError(""); }
  catch (e) { chat("a", `<p>${esc(e.message)}</p>`); }
  finally { $("as-send").disabled = false; }
}
function initAssistant() {
  $("as-chips").innerHTML = CHIPS.map(q => `<button type="button" class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("");
  $("as-chips").addEventListener("click", e => { const b = e.target.closest("[data-q]"); if (b) ask(b.dataset.q); });
  $("as-form").addEventListener("submit", e => { e.preventDefault(); ask($("as-q").value); });
}

window.addEventListener("lab-ready", () => { if (!P.inited) { P.inited = true; initPlant(); initAssistant(); } });
window.addEventListener("view-change", e => {
  if (e.detail === "plant") { if (P.inited) { enterPlant(); } }
  else { stopPlant(); $("stage-title").textContent = "Cada registro recorre este árbol hasta una hoja"; }
});
