/**
 * Document Search Assistant — add a ✕ close button to each inline element.
 *
 * Chainlit renders inline elements (PDF, Image, Text) as cards inside a
 * message. We observe those cards and inject a top-right close button that
 * collapses the card when clicked. Data is not deleted — refresh brings it
 * back — just hidden in the current view.
 */
(function () {
  "use strict";

  const BTN_CLASS = "hr-close-btn";
  const HIDDEN_CLASS = "hr-hidden";

  function makeCloseButton() {
    const btn = document.createElement("button");
    btn.className = BTN_CLASS;
    btn.setAttribute("aria-label", "Ẩn tài liệu này");
    btn.setAttribute("title", "Ẩn tài liệu này");
    btn.type = "button";
    btn.innerHTML = "&#10005;"; // ✕
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      const card = btn.closest("[data-inline-element], .inline-element, [class*='inlineElement'], [class*='element-card']")
        || btn.parentElement;
      if (card) {
        card.classList.add(HIDDEN_CLASS);
      }
    });
    return btn;
  }

  function attachCloseButtons(root) {
    // Inline elements in Chainlit appear inside message bodies. Pick anything
    // that looks like an element card (PDF / Image / Text preview).
    const selectors = [
      "[data-inline-element]",
      "[class*='inlineElement']",
      "[class*='InlineElement']",
      ".element-card",
      "iframe[src*='pdf']",
      "embed[type='application/pdf']",
    ];
    const sel = selectors.join(", ");
    const candidates = root.querySelectorAll(sel);
    candidates.forEach(function (el) {
      // Walk up to the nearest "card-like" container so the button sits on the
      // frame, not inside the iframe (which we can't touch due to sandboxing).
      let card = el;
      for (let i = 0; i < 4 && card && card !== document.body; i++) {
        const rect = card.getBoundingClientRect();
        if (rect.height > 200 && rect.width > 200) break;
        card = card.parentElement;
      }
      if (!card || card === document.body) return;
      if (card.querySelector(":scope > ." + BTN_CLASS)) return; // already added
      const style = getComputedStyle(card);
      if (style.position === "static") {
        card.style.position = "relative";
      }
      card.appendChild(makeCloseButton());
    });
  }

  // Initial pass + watch for newly streamed messages.
  function init() {
    attachCloseButtons(document.body);
    const observer = new MutationObserver(function (mutations) {
      for (const m of mutations) {
        if (m.addedNodes.length) {
          attachCloseButtons(document.body);
          break;
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    console.log("[DS Assistant] inline close buttons initialised");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
