"use strict";

const panels = [...document.querySelectorAll('[role="tabpanel"]')];
const tabs = [...document.querySelectorAll('[role="tab"]')];
const titles = {
  documentacion: [
    "El proyecto",
    "Metodología, métricas verificadas y alcance del sistema de clasificación.",
    "EL PROYECTO"
  ],
  codigo: [
    "Explora el código",
    "Consulta los archivos fuente del repositorio y las instrucciones de ejecución.",
    "CÓDIGO"
  ],
  ejecucion: [
    "Monitor de maquinaria",
    "Telemetría en vivo, operación CNC simulada y diagnóstico del árbol de decisión.",
    "MONITOR"
  ]
};

function moveNavSlider() {
  const slider = document.getElementById("nav-slider");
  const activeTab = document.querySelector('.deck-nav [role="tab"][aria-selected="true"]');
  if (!slider || !activeTab) return;
  const x = activeTab.offsetLeft - 4;
  slider.style.width = `${activeTab.offsetWidth}px`;
  slider.style.transform = `translateX(${x}px)`;
}

function selectPanel(name, focus = false) {
  if (!titles[name]) name = "ejecucion";
  for (const p of panels) p.hidden = p.id !== name;
  for (const t of tabs) {
    const active = t.dataset.panel === name;
    t.setAttribute("aria-selected", String(active));
    t.tabIndex = active ? 0 : -1;
    if (active && focus) t.focus();
  }
  document.getElementById("page-title").textContent = titles[name][0];
  document.getElementById("page-description").textContent = titles[name][1];
  const crumb = document.getElementById("topbar-section");
  if (crumb) crumb.textContent = titles[name][2];
  document.title = `${titles[name][0]} · Detección de fallas`;
  history.replaceState(null, "", `#${name}`);
  window.requestAnimationFrame(moveNavSlider);
  window.dispatchEvent(new CustomEvent("portal-panel", { detail: name }));
}

window.addEventListener("resize", () => window.requestAnimationFrame(moveNavSlider));
if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(moveNavSlider);
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectPanel(tab.dataset.panel));
  tab.addEventListener("keydown", event => {
    if (!["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? tabs.length - 1
          : (index + (["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1) + tabs.length) % tabs.length;
    selectPanel(tabs[next].dataset.panel, true);
  });
});

document.querySelectorAll("[data-go]").forEach(button => {
  button.addEventListener("click", () => {
    selectPanel(button.dataset.go);
    document.getElementById("page-title").scrollIntoView({ block: "start" });
  });
});

selectPanel(location.hash.slice(1));

/* ==========================================================================
   Spotlight Interactivo en Tarjetas Bento (seguimiento suave del cursor)
   ========================================================================== */

document.querySelectorAll(".bento-card").forEach(card => {
  card.addEventListener("pointermove", event => {
    const rect = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${(event.clientX - rect.left).toFixed(1)}px`);
    card.style.setProperty("--my", `${(event.clientY - rect.top).toFixed(1)}px`);
  }, { passive: true });
});

/* ==========================================================================
   Control de Pantalla de Presentación (Splash Screen)
   ========================================================================== */

const splashEl = document.getElementById("splash-screen");
const splashEnter = document.getElementById("splash-enter");
const splashDocs = document.getElementById("splash-docs");
const replaySplash = document.getElementById("replay-splash");

function isSplashOpen() {
  return Boolean(
    splashEl &&
      document.documentElement.dataset.splash !== "done" &&
      !splashEl.classList.contains("is-leaving")
  );
}

function dismissSplash(targetPanel = null) {
  if (!splashEl || document.documentElement.dataset.splash === "done") return;
  try {
    sessionStorage.setItem("maquinaria-splash-seen", "1");
  } catch (_) {
    /* Sin almacenamiento web. */
  }
  if (targetPanel) selectPanel(targetPanel);
  splashEl.classList.add("is-leaving");
  const finish = () => {
    document.documentElement.dataset.splash = "done";
    splashEl.classList.remove("is-leaving");
    window.requestAnimationFrame(moveNavSlider);
    window.dispatchEvent(new CustomEvent("portal-panel", { detail: location.hash.slice(1) || "ejecucion" }));
  };
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    finish();
  } else {
    window.setTimeout(finish, 420);
  }
}

function openSplash() {
  if (!splashEl) return;
  splashEl.classList.remove("is-leaving");
  delete document.documentElement.dataset.splash;
  try {
    sessionStorage.removeItem("maquinaria-splash-seen");
  } catch (_) {
    /* Sin almacenamiento web. */
  }
  if (splashEnter) splashEnter.focus();
}

if (splashEnter) splashEnter.addEventListener("click", () => dismissSplash("ejecucion"));
if (splashDocs) splashDocs.addEventListener("click", () => dismissSplash("documentacion"));
if (replaySplash) replaySplash.addEventListener("click", openSplash);

if (isSplashOpen() && splashEnter) {
  window.requestAnimationFrame(() => splashEnter.focus());
}

document.addEventListener("keydown", event => {
  if (!isSplashOpen()) return;
  if (event.key === "Escape") {
    event.preventDefault();
    dismissSplash();
  } else if (event.key === "Enter" && document.activeElement !== splashDocs) {
    event.preventDefault();
    dismissSplash("ejecucion");
  }
});

/* ==========================================================================
   Fondo Atmosférico Fluido (<canvas id="bg-canvas">)
   Corrientes de luz suaves + cintas armónicas ondulantes + micro-partículas.
   ========================================================================== */

(() => {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let width = 0;
  let height = 0;
  let dpr = 1;
  let t = 0;
  let rafId = 0;
  const pointer = { x: 0.5, y: 0.35, tx: 0.5, ty: 0.35 };
  const particles = Array.from({ length: 34 }, (_, i) => ({
    x: ((i * 97) % 100) / 100,
    y: ((i * 53 + 17) % 100) / 100,
    r: 1 + (i % 3) * 0.65,
    vx: ((i % 2 ? 1 : -1) * (0.00008 + (i % 5) * 0.00003)),
    vy: -0.00006 - (i % 4) * 0.00003
  }));

  let pal = {
    a: "rgba(56, 217, 232, 0.14)",
    b: "rgba(251, 146, 60, 0.09)",
    alert: "rgba(251, 146, 60, 0.22)",
    part: "rgba(255, 255, 255, 0.2)"
  };

  // Glow suave basado en tiempo real (independiente de FPS)
  let bloomLevel = 0;
  let lastFrameTime = performance.now();

  window.addEventListener("alert-boom", () => {
    if (reduced.matches) return;
    bloomLevel = 1;
  });

  function syncPalette() {
    const style = getComputedStyle(document.documentElement);
    pal = {
      a: style.getPropertyValue("--canvas-a").trim() || pal.a,
      b: style.getPropertyValue("--canvas-b").trim() || pal.b,
      alert: style.getPropertyValue("--canvas-alert").trim() || pal.alert,
      part: style.getPropertyValue("--canvas-particle").trim() || pal.part
    };
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    syncPalette();
  }

  function drawFrame(now = performance.now()) {
    const dt = Math.min(0.05, Math.max(0.001, (now - lastFrameTime) / 1000));
    lastFrameTime = now;

    ctx.clearRect(0, 0, width, height);
    const isRunning = document.body.dataset.run === "running";

    // Suavizado inercial independiente de tasa de refresco
    const ease = 1 - Math.exp(-3.2 * dt);
    pointer.x += (pointer.tx - pointer.x) * ease;
    pointer.y += (pointer.ty - pointer.y) * ease;
    t += (isRunning ? 0.95 : 0.36) * dt;

    // 1. Auras atmosféricas estables
    const ax = width * (0.22 + Math.sin(t * 0.6) * 0.08 + (pointer.x - 0.5) * 0.08);
    const ay = height * (0.22 + Math.cos(t * 0.5) * 0.07 + (pointer.y - 0.5) * 0.06);
    const g1 = ctx.createRadialGradient(ax, ay, 0, ax, ay, Math.max(width, height) * 0.48);
    g1.addColorStop(0, pal.a);
    g1.addColorStop(1, "transparent");
    ctx.fillStyle = g1;
    ctx.fillRect(0, 0, width, height);

    const bx = width * (0.8 + Math.cos(t * 0.45) * 0.07);
    const by = height * (0.78 + Math.sin(t * 0.55) * 0.07);
    const g2 = ctx.createRadialGradient(bx, by, 0, bx, by, Math.max(width, height) * 0.42);
    g2.addColorStop(0, pal.b);
    g2.addColorStop(1, "transparent");
    ctx.fillStyle = g2;
    ctx.fillRect(0, 0, width, height);

    // 2. Cintas armónicas sedosas
    for (let w = 0; w < 3; w++) {
      ctx.beginPath();
      ctx.lineWidth = w === 0 ? 1.5 : 1.1;
      ctx.strokeStyle = w === 2 ? pal.b : pal.a;
      const baseY = height * (0.34 + w * 0.19);
      const amp = (isRunning ? 32 : 19) + w * 7;
      const freq = 0.0022 + w * 0.0007;
      for (let x = 0; x <= width; x += 20) {
        const wave =
          Math.sin(x * freq + t * (1 + w * 0.25) + w * 1.9) * amp +
          Math.cos(x * freq * 0.55 - t * 0.7) * (amp * 0.35);
        if (x === 0) ctx.moveTo(x, baseY + wave);
        else ctx.lineTo(x, baseY + wave);
      }
      ctx.stroke();
    }

    // 3. Micro-partículas flotantes sutiles
    ctx.fillStyle = pal.part;
    const speedMul = (isRunning ? 1.9 : 1) * (dt * 60);
    for (const p of particles) {
      p.x = (p.x + p.vx * speedMul + 1) % 1;
      p.y = (p.y + p.vy * speedMul + 1) % 1;
      ctx.beginPath();
      ctx.arc(p.x * width, p.y * height, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // 4. Resplandor atmosférico lento y sedoso (~2.2s de decaimiento exponencial suave)
    if (bloomLevel > 0.004) {
      bloomLevel *= Math.exp(-1.55 * dt);
      const radius = Math.max(width, height) * (0.58 + (1 - bloomLevel) * 0.25);
      const bg = ctx.createRadialGradient(width * 0.5, height * 0.36, 0, width * 0.5, height * 0.36, radius);
      bg.addColorStop(0, `rgba(251, 146, 60, ${(bloomLevel * 0.16).toFixed(3)})`);
      bg.addColorStop(0.6, `rgba(234, 88, 12, ${(bloomLevel * 0.07).toFixed(3)})`);
      bg.addColorStop(1, "transparent");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, width, height);
    }
  }

  function loop(now) {
    if (!document.hidden) drawFrame(now);
    else lastFrameTime = now;
    if (!reduced.matches) rafId = window.requestAnimationFrame(loop);
  }

  resize();
  window.addEventListener("resize", resize);
  window.addEventListener("theme-change", () => {
    syncPalette();
    if (reduced.matches) drawFrame();
  });
  window.addEventListener("pointermove", event => {
    if (!width || !height) return;
    pointer.tx = event.clientX / width;
    pointer.ty = event.clientY / height;
  }, { passive: true });

  if (reduced.matches) drawFrame();
  else rafId = window.requestAnimationFrame(loop);

  reduced.addEventListener("change", () => {
    window.cancelAnimationFrame(rafId);
    if (reduced.matches) drawFrame();
    else rafId = window.requestAnimationFrame(loop);
  });
})();

/* ==========================================================================
   Carga de metadatos del proyecto, diales radiales y visor de código
   ========================================================================== */

const percent = x => (100 * x).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " %";
let sourceRequest = 0;

async function showSource(path) {
  const generation = ++sourceRequest;
  document.getElementById("source-title").textContent = path;
  document.getElementById("source-content").textContent = "Cargando archivo…";
  document.getElementById("source-download").href = "/project/file?file=" + encodeURIComponent(path);
  document.querySelectorAll("[data-source]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.source === path)));
  try {
    const response = await fetch("/api/source?file=" + encodeURIComponent(path));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    if (generation !== sourceRequest) return;
    document.getElementById("source-content").textContent = data.content;
    document.getElementById("source-note").textContent = data.notebook
      ? "Vista de las celdas de explicación y código. Descarga el notebook para consultar sus salidas y gráficos."
      : "Vista de lectura. Los cambios se realizan en los archivos locales del proyecto.";
  } catch (error) {
    if (generation === sourceRequest) {
      document.getElementById("source-content").textContent = "No se pudo cargar: " + error.message;
    }
  }
}

async function loadProject() {
  try {
    const response = await fetch("/api/project");
    if (!response.ok) throw new Error("No se pudo consultar la documentación local.");
    const p = await response.json();
    const values = {
      precision: percent(p.metrics.precision),
      recall: percent(p.metrics.recall),
      f1: p.metrics.f1.toFixed(4),
      accuracy: percent(p.metrics.accuracy),
      tn: p.metrics.true_negative,
      fp: p.metrics.false_positive,
      fn: p.metrics.false_negative,
      tp: p.metrics.true_positive,
      "check-count": p.verification.checks,
      "check-result": p.verification.all_passed ? "Comprobaciones base superadas" : "Revisar comprobaciones",
      "base-revision": p.base_revision,
      "model-name": p.model
    };
    for (const [id, value] of Object.entries(values)) {
      const target = document.getElementById(id);
      if (target) target.textContent = value;
    }

    const circumference = 2 * Math.PI * 26;
    const ringMap = {
      "ring-recall": p.metrics.recall,
      "ring-precision": p.metrics.precision,
      "ring-f1": p.metrics.f1,
      "ring-accuracy": p.metrics.accuracy
    };
    for (const [id, val] of Object.entries(ringMap)) {
      const circle = document.getElementById(id);
      if (circle) {
        const clamped = Math.max(0, Math.min(1, Number(val) || 0));
        circle.style.strokeDashoffset = (circumference * (1 - clamped)).toFixed(2);
      }
    }

    document.getElementById("checks-date").textContent =
      "Ejecución registrada: " + new Date(p.verification.generated_at_utc).toLocaleString("es-PE");

    if (p.runtime?.mode === "web") {
      document.getElementById("runtime-label").textContent = "Sesión web";
      document.getElementById("session-help").textContent =
        "Tu simulación es independiente de otros navegadores. Las pestañas del mismo navegador comparten sesión. Cambiar de sección no pausa la reproducción. El avance se pierde si el servicio reinicia o tras 15 minutos sin solicitudes: exporta el CSV para conservarlo.";
      document.getElementById("publication-help").textContent =
        "Aplicación web de demostración. Los archivos y las instrucciones se encuentran en el repositorio. El servicio gratuito puede tardar en arrancar después de un periodo sin visitas.";
    }

    const tree = document.getElementById("source-tree");
    for (const path of p.source_files) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.source = path;
      button.title = path;
      button.textContent = path;
      button.addEventListener("click", () => showSource(path));
      tree.append(button);
    }
    showSource("README.md");
  } catch (error) {
    document.getElementById("project-error").hidden = false;
    document.getElementById("project-error").textContent = error.message;
  }
}

document.querySelectorAll("[data-copy]").forEach(button => {
  const original = button.textContent;
  let timer = null;
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
      button.textContent = "Copiado ✓";
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        button.textContent = original;
      }, 2200);
    } catch (_error) {
      button.textContent = "Selecciona y copia el comando";
    }
  });
});

loadProject();
