/**
 * HR Assistant — auto-close side panel on new message.
 * Chainlit v2 renders the side view as a drawer/panel. We observe for it
 * and close it when the user submits a new query.
 */
(function () {
  "use strict";

  console.log("[HR Assistant] custom.js loaded v2");

  function closeSidePanel() {
    // Strategy 1: find any visible close/back button in the side panel area.
    const buttons = document.querySelectorAll("button");
    for (const btn of buttons) {
      const label = (btn.getAttribute("aria-label") || "").toLowerCase();
      const text = (btn.textContent || "").trim();
      // Chainlit side view has a back arrow or close icon button.
      if (
        label.includes("close") ||
        label.includes("back") ||
        text === "←" ||
        text === "✕" ||
        text === "×"
      ) {
        // Check if it's inside a side-view-like container.
        const parent = btn.closest('[class*="side"], [class*="Side"], [class*="drawer"], [class*="Drawer"]');
        if (parent) {
          console.log("[HR Assistant] closing side panel via button:", label || text);
          btn.click();
          return true;
        }
      }
    }

    // Strategy 2: find the side panel container and click its first button (usually back/close).
    const panels = document.querySelectorAll(
      '[class*="sideView"], [class*="SideView"], [class*="side-view"], [class*="elementSideView"]'
    );
    for (const panel of panels) {
      if (panel.offsetParent !== null) {
        const firstBtn = panel.querySelector("button");
        if (firstBtn) {
          console.log("[HR Assistant] closing side panel via first button in panel");
          firstBtn.click();
          return true;
        }
      }
    }

    // Strategy 3: brute force — find any open panel with a PDF/text viewer and click backdrop or ESC.
    const backdrop = document.querySelector('[class*="backdrop"], [class*="Backdrop"]');
    if (backdrop) {
      console.log("[HR Assistant] closing via backdrop click");
      backdrop.click();
      return true;
    }

    // Strategy 4: dispatch Escape key to close any open overlay.
    const activeEl = document.activeElement || document.body;
    activeEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    console.log("[HR Assistant] dispatched Escape key");
    return false;
  }

  // Observe user message submission.
  function onUserSubmit() {
    console.log("[HR Assistant] new message submitted, closing side panel");
    // Small delay to let Chainlit process the message first.
    setTimeout(closeSidePanel, 150);
    setTimeout(closeSidePanel, 500); // retry in case panel re-renders
  }

  // Listen for Enter (without Shift) in textarea.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      const textarea = e.target.closest("textarea");
      if (textarea && textarea.value.trim()) {
        onUserSubmit();
      }
    }
  }, true);

  // Listen for send button click.
  document.addEventListener("click", function (e) {
    const btn = e.target.closest('button[type="submit"], [aria-label*="end"], [aria-label*="ửi"]');
    if (btn) {
      onUserSubmit();
    }
  }, true);

  // Also observe DOM for new user messages appearing (backup).
  const observer = new MutationObserver(function (mutations) {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1) {
          // If a new user message bubble appears, close side panel.
          if (
            node.matches && (
              node.matches('[class*="userMessage"]') ||
              node.matches('[class*="user-message"]') ||
              node.querySelector && node.querySelector('[class*="userMessage"]')
            )
          ) {
            console.log("[HR Assistant] detected new user message in DOM, closing panel");
            setTimeout(closeSidePanel, 200);
          }
        }
      }
    }
  });

  // Start observing once the chat container exists.
  function startObserving() {
    const chat = document.querySelector('[class*="messages"], [class*="Messages"], main');
    if (chat) {
      observer.observe(chat, { childList: true, subtree: true });
      console.log("[HR Assistant] MutationObserver attached to chat container");
    } else {
      setTimeout(startObserving, 1000);
    }
  }
  startObserving();
})();
