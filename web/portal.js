"use strict";

const panels = [...document.querySelectorAll('[role="tabpanel"]')];
const tabs = [...document.querySelectorAll('[role="tab"]')];
const titles = {
  documentacion: [
    "El proyecto",
    "Metodología, resultados verificados y alcance del sistema de clasificación.",
    "EL PROYECTO"
  ],
  asistente: [
    "Monitor de la planta",
    "Elige una fresadora, cambia sus condiciones y mira cómo responde la IA. Si tienes dudas, pregúntale al asistente.",
    "MONITOR"
  ],
  codigo: [
    "Explora el código",
    "Consulta los archivos fuente del repositorio y las instrucciones de ejecución.",
    "CÓDIGO"
  ],
  ejecucion: [
    "Datos de prueba",
    "Reproduce los 2 000 registros reales que el modelo nunca vio y compara su decisión con la etiqueta real.",
    "DATOS DE PRUEBA"
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
  if (!titles[name]) name = "asistente";
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
    window.dispatchEvent(new CustomEvent("portal-panel", { detail: location.hash.slice(1) || "asistente" }));
  };
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    finish();
  } else {
    window.setTimeout(finish, 400);
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

if (splashEnter) splashEnter.addEventListener("click", () => dismissSplash("asistente"));
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
    dismissSplash("asistente");
  }
});

/* ==========================================================================
   Fondo Animado Técnico Reactivo (<canvas id="bg-canvas">)
   Retícula CAD interactiva con el cursor + ondas de telemetría reactivas.
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
  let phase = 0;
  let rafId = 0;
  const pointer = { x: -9999, y: -9999, active: false };

  let palette = {
    dot: "rgba(70, 96, 122, 0.17)",
    wave: "rgba(11, 110, 124, 0.14)",
    alert: "rgba(207, 82, 22, 0.2)",
    cursor: "rgba(11, 110, 124, 0.35)"
  };

  function syncPalette() {
    const style = getComputedStyle(document.documentElement);
    palette = {
      dot: style.getPropertyValue("--canvas-dot").trim() || palette.dot,
      wave: style.getPropertyValue("--canvas-wave").trim() || palette.wave,
      alert: style.getPropertyValue("--canvas-alert").trim() || palette.alert,
      cursor: style.getPropertyValue("--canvas-cursor").trim() || palette.cursor
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

  function drawFrame() {
    ctx.clearRect(0, 0, width, height);
    const isRunning = document.body.dataset.run === "running";
    const isAlert = document.body.dataset.alert === "true";

    // 1. Retícula técnica calibrada con iluminación sutil cerca del cursor
    const step = 42;
    ctx.fillStyle = palette.dot;
    for (let x = 21; x < width; x += step) {
      for (let y = 21; y < height; y += step) {
        let r = 1.05;
        if (pointer.active) {
          const dx = x - pointer.x;
          const dy = y - pointer.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 150) {
            const boost = 1 - dist / 150;
            ctx.fillStyle = isAlert ? palette.alert : palette.cursor;
            ctx.beginPath();
            ctx.arc(x, y, 1.1 + boost * 1.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = palette.dot;
            continue;
          }
        }
        ctx.fillRect(x - r * 0.5, y - r * 0.5, r, r);
      }
    }

    // 2. Tres ondas suaves de telemetría sincronizadas al estado del monitor
    const waveStroke = isAlert ? palette.alert : palette.wave;
    ctx.lineWidth = 1.25;
    ctx.strokeStyle = waveStroke;
    const baseSpeed = isRunning ? 0.024 : 0.006;
    phase += baseSpeed;

    for (let w = 0; w < 3; w++) {
      ctx.beginPath();
      const baseY = height * (0.28 + w * 0.25);
      const amp = (isRunning ? 22 : 12) + w * 5;
      const freq = 0.0032 + w * 0.0011;
      for (let x = 0; x <= width; x += 18) {
        const y = baseY + Math.sin(x * freq + phase * (1 + w * 0.35) + w * 1.8) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // 3. Micro-retícula de coordenadas en la posición del cursor
    if (pointer.active) {
      ctx.strokeStyle = isAlert ? palette.alert : palette.cursor;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(pointer.x - 10, pointer.y);
      ctx.lineTo(pointer.x + 10, pointer.y);
      ctx.moveTo(pointer.x, pointer.y - 10);
      ctx.lineTo(pointer.x, pointer.y + 10);
      ctx.stroke();
    }
  }

  function loop() {
    if (!document.hidden) drawFrame();
    if (!reduced.matches) rafId = window.requestAnimationFrame(loop);
  }

  resize();
  window.addEventListener("resize", resize);
  window.addEventListener("theme-change", () => {
    syncPalette();
    if (reduced.matches) drawFrame();
  });
  window.addEventListener("pointermove", event => {
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    pointer.active = true;
  }, { passive: true });
  window.addEventListener("pointerleave", () => {
    pointer.active = false;
  });

  if (reduced.matches) {
    drawFrame();
  } else {
    rafId = window.requestAnimationFrame(loop);
  }

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

    // Diales radiales SVG (radio 26 -> circunferencia 163.36)
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
