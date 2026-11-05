"use strict";
const usageDialog = document.getElementById("usage-dialog");
document.querySelectorAll("[data-open-manual]").forEach(button => {
  button.addEventListener("click", () => usageDialog.showModal());
});
usageDialog.addEventListener("click", event => {
  if (event.target === usageDialog) {
    const rect = usageDialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) usageDialog.close();
  }
});
