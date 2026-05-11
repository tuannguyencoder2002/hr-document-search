/**
 * HR Assistant — custom JS for Chainlit.
 *
 * Purpose: Auto-close the side panel (PDF/text viewer) when the user sends
 * a new message. Chainlit doesn't expose a backend API for this, so we
 * observe DOM mutations and close it client-side.
 */

(function () {
  "use strict";

  // Log to console so user can verify via DevTools.
  console.log("[HR Assistant] custom.js loaded");

  /**
   * Close the side panel by clicking its close button (if open).
   * Chainlit renders a button with data-testid="close-side-view" or an
   * aria-label containing "close". We try multiple selectors for robustness.
   */
  function closeSidePanel() {
    const selectors = [
      '[data-testid="close-side-view"]',
      'button[aria-label="Close"]',
      'button[aria-label="close"]',
      '.side-view-header button',
      '[class*="sideView"] button[class*="close"]',
      '[class*="SideView"] button',
    ];
    for (const sel of selectors) {
      const btn = document.querySelector(sel);
      if (btn) {
        console.log("[HR Assistant] closing side panel via:", sel);
        btn.click();
        return true;
      }
    }
    // Fallback: if there's an open side view container, hide it.
    const sideView = document.querySelector('[class*="sideView"], [class*="SideView"]');
    if (sideView && sideView.offsetParent !== null) {
      console.log("[HR Assistant] hiding side panel via display:none fallback");
      sideView.style.display = "none";
      return true;
    }
    return false;
  }

  /**
   * Observe the chat input form for submit events. When the user sends a
   * message, close the side panel so the new answer starts fresh.
   */
  function observeSubmit() {
    // Listen for Enter key or click on send button.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        const textarea = document.querySelector("textarea");
        if (textarea && textarea.value.trim()) {
          console.log("[HR Assistant] user submitting message, closing side panel");
          setTimeout(closeSidePanel, 100);
        }
      }
    });

    // Also observe clicks on the send button.
    document.addEventListener("click", function (e) {
      const target = e.target.closest(
        'button[type="submit"], [aria-label="Send"], [aria-label="Gửi"]'
      );
      if (target) {
        console.log("[HR Assistant] send button clicked, closing side panel");
        setTimeout(closeSidePanel, 100);
      }
    });
  }

  // Wait for DOM to be ready.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observeSubmit);
  } else {
    observeSubmit();
  }
})();
