"use strict";
/* Pestaña «Asistente IA»: lista compacta de fresadoras (planta simulada) y chat con el asistente.
   El Transformer ajustado entiende la pregunta; el pronosticador prueba qué acción baja el riesgo. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = t => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const pct = p => `${Math.round((p || 0) * 100)} %`;
  const CHIPS = ["¿Qué hago con esta fresadora?", "¿Por qué sube el riesgo?", "¿Cuánto tiempo tengo?", "¿Qué fresadora atiendo primero?"];
  const S = {sel: 0, timer: 0, running: true, busy: false, visible: false, state: null, hold: 0, tree: null};
  const FEAT = {"Air temperature [K]": "Temperatura del aire", "Process temperature [K]": "Temperatura del proceso", "Rotational speed [rpm]": "Velocidad",
    "Torque [Nm]": "Torque", "Tool wear [min]": "Desgaste de herramienta", "Power [W]": "Potencia", "Temp diff [K]": "Diferencia de temperatura",
    "Wear x torque [minNm]": "Desgaste × torque"};
  const UNIT = {rpm: v => `${Math.round(v)} rpm`, power: v => `${Math.round(v).toLocaleString("es")} W`, cool: v => `${Number(v).toFixed(1)}`};
  const num = (v, u) => `${Math.abs(v) >= 100 ? Math.round(v).toLocaleString("es") : Number(v).toFixed(1)} ${u}`;

  async function request(path, data) {
    const r = await fetch(path, data === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
    const out = await r.json();
    if (!r.ok) throw new Error(out.error || "No se pudo completar la solicitud.");
    return out;
  }

  function level(m) {
    if (m.status === "down") return "down";
    const p = m.fc ?? m.risk ?? 0;
    return p >= 0.5 ? "high" : p >= 0.2 ? "mid" : "ok";
  }

  function render(state) {
    S.state = state;
    $("as-list").innerHTML = state.machines.map(m => {
      const lv = level(m), label = lv === "down" ? "Detenida" : pct(m.fc ?? m.risk);
      return `<li><button type="button" data-id="${m.id}" class="as-m ${lv}${m.id === S.sel ? " sel" : ""}" aria-pressed="${m.id === S.sel}">
        <span class="as-dot"></span><span class="as-name">${esc(m.name)}</span><span class="as-risk">${label}</span></button></li>`;
    }).join("");
    if (state.selected) card(state.selected);
  }

  function card(m) {
    $("as-mname").textContent = `${m.name} · tipo ${m.type}`;
    const down = m.status === "down";
    $("as-status").textContent = down ? "Detenida por falla" : m.alert ? "Falla detectada" : "En marcha";
    $("as-status").className = `as-status ${down || m.alert ? "bad" : ""}`;
    $("as-restart").hidden = !down;
    document.querySelectorAll("#asistente [data-action=tool], #asistente [data-action=stabilize]").forEach(b => b.disabled = down);
    if (Date.now() > S.hold) for (const k of ["rpm", "power", "cool"]) {
      const el = $(`c-${k}`);
      if (document.activeElement !== el) { el.value = m.setpoints[k]; $(`v-${k}`).textContent = UNIT[k](m.setpoints[k]); }
    }
    const fc = m.fc ?? m.forecast?.p ?? 0, lv = fc >= 0.5 ? "high" : fc >= 0.2 ? "mid" : "ok";
    $("as-fc").textContent = pct(fc);
    $("as-arc").setAttribute("stroke-dasharray", `${Math.max(1, Math.round(fc * 100))} 100`);
    $("as-arc").setAttribute("class", `as-arc-fg ${lv}`);
    $("as-tree-v").textContent = `Árbol: ${m.alert ? "falla" : "sin falla"}`;
    $("as-tree-v").className = `as-chipv ${m.alert ? "bad" : "good"}`;
    $("as-ae-v").textContent = `Autoencoder: ${m.ae_alert ? "atípico" : "normal"}`;
    $("as-ae-v").className = `as-chipv ${m.ae_alert ? "warn" : "good"}`;
    $("as-gauges").innerHTML = (m.rules || []).map(r => {
      const span = r.max - r.min || 1, x = v => Math.min(100, Math.max(0, (v - r.min) / span * 100));
      return `<li class="${r.bad ? "bad" : ""}" title="${esc(r.rule)}"><div><span>${esc(r.label)}</span><b>${num(r.value, r.unit)}</b></div>
        <span class="as-track"><span class="as-safe" style="left:${x(r.safe[0])}%;width:${x(r.safe[1]) - x(r.safe[0])}%"></span><span class="as-needle" style="left:${x(r.value)}%"></span></span></li>`;
    }).join("");
    if (S.tree && m.path) {
      const n = S.tree.nodes, f = S.tree.features, steps = [];
      for (let i = 0; i < m.path.length - 1; i++) {
        const node = n[m.path[i]], yes = m.path[i + 1] === node.l, name = FEAT[f[node.f]] || f[node.f];
        steps.push(`<li>¿${esc(name)} ≤ ${num(node.t, "").trim()}? <b>${yes ? "Sí" : "No"}</b></li>`);
      }
      steps.push(`<li class="${m.alert ? "bad" : "good"}"><b>${m.alert ? "Predice falla" : "Predice sin falla"}</b> · en esta hoja cayeron ${m.leaf_n} casos de entrenamiento, ${m.leaf_fail} con falla</li>`);
      $("as-path").innerHTML = steps.join("");
    }
  }

  async function control(data) {
    try { S.hold = Date.now() + 1500; render(await request("/api/plant/control", {id: S.sel, sel: S.sel, ...data})); }
    catch (e) { message("err", esc(e.message)); }
  }

  async function tick() {
    if (S.busy || !S.visible || !S.running) return;
    S.busy = true;
    try { render(await request("/api/plant/tick", {sel: S.sel})); } catch (_) { /* reintenta en el siguiente ciclo */ }
    finally { S.busy = false; }
  }

  function message(kind, html) {
    const el = document.createElement("div");
    el.className = `as-msg ${kind}`; el.innerHTML = html;
    const log = $("as-log");
    log.append(el);
    while (log.children.length > 12) log.firstChild.remove();
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function answer(r) {
    let h = `<p>${esc(r.text)}</p>`;
    if (r.ranking) h += `<ol class="as-rank">${r.ranking.slice(0, 5).map(x => `<li>${esc(x.name)} <b>${pct(x.p)}</b></li>`).join("")}</ol>`;
    if (r.actions && r.actions.length) {
      h += `<ul class="as-actions">${r.actions.slice(0, 3).map((a, i) =>
        `<li><span>${esc(a.label)}${a.p == null ? "" : ` <em>${pct(r.p_idle)} → <b>${pct(a.p)}</b></em>`}</span>
         <button type="button" class="as-apply" data-i="${i}">Aplicar</button></li>`).join("")}</ul>`;
    }
    const el = message("a", h);
    el.querySelectorAll(".as-apply").forEach(b => b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        const id = r.machine ?? S.sel;
        render(await request("/api/plant/control", {id, sel: id, ...r.actions[Number(b.dataset.i)].apply}));
        b.textContent = "Aplicado ✓";
      } catch (e) { b.disabled = false; message("err", esc(e.message)); }
    }));
    if (r.machine != null && r.named && r.machine !== S.sel) { S.sel = r.machine; request(`/api/plant?sel=${S.sel}`).then(render).catch(() => {}); }
  }

  async function ask(q) {
    q = (q || "").trim();
    if (!q) return;
    const name = S.state ? S.state.machines[S.sel].name : "";
    message("q", `${esc(q)}${name ? `<small>${esc(name)}</small>` : ""}`);
    $("as-q").value = ""; $("as-send").disabled = true;
    try { answer(await request("/api/plant/assistant", {question: q, sel: S.sel})); }
    catch (e) { message("err", esc(e.message)); }
    finally { $("as-send").disabled = false; }
  }

  $("as-chips").innerHTML = CHIPS.map(q => `<button type="button" class="as-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("");
  $("as-chips").addEventListener("click", e => { const b = e.target.closest("[data-q]"); if (b) ask(b.dataset.q); });
  $("as-form").addEventListener("submit", e => { e.preventDefault(); ask($("as-q").value); });
  $("as-list").addEventListener("click", e => {
    const b = e.target.closest("[data-id]");
    if (b) { S.sel = Number(b.dataset.id); request(`/api/plant?sel=${S.sel}`).then(render).catch(() => {}); }
  });
  $("as-run").addEventListener("click", () => {
    S.running = !S.running;
    $("as-run").textContent = S.running ? "Pausar" : "Reanudar";
    $("as-run").setAttribute("aria-pressed", String(S.running));
  });

  for (const k of ["rpm", "power", "cool"]) {
    const el = $(`c-${k}`);
    el.addEventListener("input", () => { S.hold = Date.now() + 1500; $(`v-${k}`).textContent = UNIT[k](el.value); });
    el.addEventListener("change", () => control({[k]: Number(el.value)}));
  }
  document.querySelectorAll("#asistente [data-action]").forEach(b => b.addEventListener("click", () => control({action: b.dataset.action})));
  request("/api/model").then(t => { S.tree = t; if (S.state && S.state.selected) card(S.state.selected); }).catch(() => {});

  async function show(panel) {
    S.visible = panel === "asistente";
    clearInterval(S.timer);
    if (!S.visible) return;
    if (!S.state) { try { render(await request(`/api/plant?sel=${S.sel}`)); } catch (e) { message("err", esc(e.message)); } }
    S.timer = setInterval(tick, 1500);
  }
  window.addEventListener("portal-panel", e => show(e.detail));
  show(location.hash.slice(1));
})();
