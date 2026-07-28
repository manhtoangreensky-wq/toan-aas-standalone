/* Presentation-only lifecycle helpers for the public portal shell.
   This file intentionally owns no route, request, storage or account state. */
(() => {
  "use strict";

  const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
  const ENTER_CLEAR_DELAY_MS = 500;

  function prefersReducedMotion() {
    return typeof window.matchMedia === "function"
      && window.matchMedia(REDUCED_MOTION_QUERY).matches;
  }

  function clearMotion(element) {
    if (element) element.removeAttribute("data-portal-motion");
  }

  function enter(element, kind) {
    if (!element || prefersReducedMotion()) {
      clearMotion(element);
      return;
    }
    element.setAttribute("data-portal-motion", kind === "pop" ? "pop" : "enter");
    const clear = () => clearMotion(element);
    element.addEventListener("animationend", clear, { once: true });
    window.setTimeout(clear, ENTER_CLEAR_DELAY_MS);
  }

  function replace(shell, main, render) {
    const apply = typeof render === "function" ? render : () => {};
    if (prefersReducedMotion() || typeof document.startViewTransition !== "function") {
      apply();
      enter(main, "enter");
      return;
    }
    try {
      const transition = document.startViewTransition(apply);
      if (transition && transition.ready) transition.ready.catch(() => {});
      if (transition && transition.finished) transition.finished.catch(() => {});
      if (transition && transition.updateCallbackDone
          && typeof transition.updateCallbackDone.then === "function") {
        transition.updateCallbackDone.then(() => {
          enter(main, "enter");
        }).catch(() => {});
      } else {
        enter(main, "enter");
      }
    } catch (_) {
      apply();
      enter(main, "enter");
    }
  }

  window.TOANAASPortalMotion = Object.freeze({
    enter,
    replace,
    prefersReducedMotion
  });
})();
