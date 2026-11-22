/* Se ejecuta antes del CSS para aplicar tema y estado de portada sin destellos. */
(() => {
  "use strict";
  const themeKey = "maquinaria-theme";
  const splashKey = "maquinaria-splash-seen";
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const valid = value => value === "dark" || value === "light";

  let selected = null;
  try {
    selected = localStorage.getItem(themeKey);
    if (sessionStorage.getItem(splashKey) === "1") {
      document.documentElement.dataset.splash = "done";
    }
  } catch (_) {
    /* La página sigue funcionando sin almacenamiento web. */
  }

  let explicit = valid(selected);
  const preferred = () => (system.matches ? "dark" : "light");

  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    const button = document.getElementById("theme-toggle");
    if (button) {
      const dark = theme === "dark";
      button.setAttribute("aria-checked", String(dark));
      button.title = dark ? "Activar modo claro" : "Activar modo oscuro";
      const label = button.querySelector(".theme-label");
      if (label) label.textContent = dark ? "Oscuro" : "Claro";
    }
    window.dispatchEvent(new CustomEvent("theme-change", { detail: theme }));
  }

  apply(explicit ? selected : preferred());

  document.addEventListener("DOMContentLoaded", () => {
    apply(document.documentElement.dataset.theme);
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        explicit = true;
        apply(next);
        try {
          localStorage.setItem(themeKey, next);
        } catch (_) {
          /* Conservar la elección durante esta sesión. */
        }
      });
    }
  });

  system.addEventListener("change", () => {
    if (!explicit) apply(preferred());
  });

  window.addEventListener("storage", event => {
    if (event.key !== themeKey && event.key !== null) return;
    explicit = valid(event.newValue);
    apply(explicit ? event.newValue : preferred());
  });
})();
