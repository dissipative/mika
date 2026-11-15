// Mika's care guide — progressive enhancement only. The page works without it.
(function () {
  "use strict";

  // 1. Remember the language a visitor picks in the switcher.
  document.querySelectorAll("[data-lang-link]").forEach(function (link) {
    link.addEventListener("click", function () {
      try { localStorage.setItem("mika-lang", link.getAttribute("data-lang-link")); } catch (e) { /* storage blocked */ }
    });
  });

  // 2. Print / save as PDF button (hidden when scripts are off).
  var printBtn = document.querySelector("[data-print]");
  if (printBtn && typeof window.print === "function") {
    printBtn.hidden = false;
    printBtn.addEventListener("click", function () { window.print(); });
  }

  // 3. Print: open collapsed sections and show the page address, then restore.
  var closed = [];
  var urlSlot = document.querySelector("[data-print-url]");
  window.addEventListener("beforeprint", function () {
    closed = Array.prototype.filter.call(document.querySelectorAll("details"), function (d) { return !d.open; });
    closed.forEach(function (d) { d.open = true; });
    if (urlSlot) { urlSlot.textContent = location.href.split("#")[0]; }
  });
  window.addEventListener("afterprint", function () {
    closed.forEach(function (d) { d.open = false; });
    closed = [];
  });
})();
