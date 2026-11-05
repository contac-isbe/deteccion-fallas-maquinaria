/* Se ejecuta antes del CSS para aplicar la preferencia sin destellos. */
(() => {
  "use strict";
  const key = "maquinaria-theme";
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const valid = value => value === "dark" || value === "light";
  let selected = null;
  try { selected = localStorage.getItem(key); } catch (_) { /* La página sigue funcionando sin almacenamiento. */ }
  let explicit = valid(selected);
  const preferred = () => system.matches ? "dark" : "light";

  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    const button = document.getElementById("theme-toggle");
    if (!button) return;
    const dark = theme === "dark";
    button.setAttribute("aria-checked", String(dark));
    button.title = dark ? "Activar modo claro" : "Activar modo oscuro";
    button.querySelector(".theme-label").textContent = dark ? "Oscuro" : "Claro";
  }

  apply(explicit ? selected : preferred());
  document.addEventListener("DOMContentLoaded", () => {
    apply(document.documentElement.dataset.theme);
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      explicit = true;
      apply(theme);
      try { localStorage.setItem(key, theme); } catch (_) { /* Mantener la elección durante esta sesión. */ }
    });
  });
  system.addEventListener("change", () => { if (!explicit) apply(preferred()); });
  window.addEventListener("storage", event => {
    if (event.key !== key && event.key !== null) return;
    explicit = valid(event.newValue);
    apply(explicit ? event.newValue : preferred());
  });
})();
