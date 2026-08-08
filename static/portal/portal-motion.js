/* Presentation-only lifecycle helpers for the public portal shell.
   This file intentionally owns no route, request, storage or account state. */
(() => {
  "use strict";

  const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
  const ENTER_CLEAR_DELAY_MS = 500;
  let landingCleanup = null;
  let landingHeroHasEntered = false;

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
    const skipEnter = Boolean(main && main.dataset && main.dataset.portalMotionSkipEnter === "true");
    if (prefersReducedMotion() || typeof document.startViewTransition !== "function") {
      apply();
      if (!skipEnter) enter(main, "enter");
      return Promise.resolve();
    }
    try {
      const transition = document.startViewTransition(apply);
      if (transition && transition.ready) transition.ready.catch(() => {});
      if (transition && transition.finished) transition.finished.catch(() => {});
      if (transition && transition.updateCallbackDone
          && typeof transition.updateCallbackDone.then === "function") {
        if (skipEnter) return transition.updateCallbackDone.then(() => {}).catch(() => {});
        return transition.updateCallbackDone.then(() => {
          enter(main, "enter");
        }).catch(() => {});
      } else {
        if (!skipEnter) enter(main, "enter");
        return Promise.resolve();
      }
    } catch (_) {
      apply();
      if (!skipEnter) enter(main, "enter");
      return Promise.resolve();
    }
  }

  function unmountLanding() {
    if (typeof landingCleanup === "function") landingCleanup();
    landingCleanup = null;
  }

  function mountLanding(root) {
    unmountLanding();
    if (!root || typeof window !== "object") return;

    root.setAttribute("data-landing-motion", "cinematic-mini");
    const header = root.querySelector(".portal-landing-header");
    const hero = root.querySelector(".portal-landing-hero");
    const preview = root.querySelector(".portal-landing-preview");
    const revealTargets = Array.from(root.querySelectorAll(
      ".portal-landing-section, .portal-landing-workflow, .portal-landing-trust, .portal-landing-final"
    ));
    if (header) header.classList.add("landing-motion-header");
    if (hero) hero.classList.add("landing-motion-hero", "landing-cinematic-hero");
    if (preview) {
      preview.classList.add("landing-cinematic-preview");
      preview.querySelectorAll(".portal-landing-preview-steps > span")
        .forEach((step) => step.classList.add("landing-cinematic-step"));
    }

    // The aperture remains a quiet static frame for motion-sensitive visitors.
    // Only animation setup is skipped; no content relies on this helper to be
    // visible or operable.
    if (prefersReducedMotion()) return;

    let scrollFrame = 0;
    let heroFrame = 0;
    let observer = null;

    const syncHeader = () => {
      scrollFrame = 0;
      if (!header) return;
      header.setAttribute(
        "data-landing-motion-header",
        window.scrollY > 20 ? "compact" : "default"
      );
    };
    const onScroll = () => {
      if (scrollFrame) return;
      scrollFrame = window.requestAnimationFrame(syncHeader);
    };

    if (header) {
      syncHeader();
      window.addEventListener("scroll", onScroll, { passive: true });
    }

    if (hero) {
      root.querySelectorAll(
        ".portal-landing-hero-copy, .portal-landing-hero-actions, .portal-landing-proof, .portal-landing-preview"
      ).forEach((stage) => stage.classList.add("landing-motion-hero-stage"));
      if (landingHeroHasEntered) {
        hero.classList.add("is-ready");
      } else {
        landingHeroHasEntered = true;
        heroFrame = window.requestAnimationFrame(() => hero.classList.add("is-ready"));
      }
    }

    revealTargets.forEach((target) => {
      target.classList.add("landing-motion-reveal");
      if (target.matches(".portal-landing-workflow")) target.classList.add("landing-motion-workflow");
      if (target.matches(".portal-landing-final")) target.classList.add("landing-motion-final");
      const title = target.querySelector(
        ".portal-landing-section-heading, .portal-landing-workflow > div, .portal-landing-trust-copy, .portal-landing-final > div"
      );
      if (title) title.classList.add("landing-motion-reveal-title");
      target.querySelectorAll(
        ".portal-landing-studio, .portal-landing-workflow li, .portal-landing-trust-grid > article"
      ).forEach((card) => card.classList.add("landing-motion-card"));
    });
    root.querySelectorAll(".portal-button").forEach((cta) => cta.classList.add("landing-motion-cta"));

    const revealTarget = (target) => {
      target.classList.remove("is-pending");
      target.classList.add("is-visible");
      if (observer) observer.unobserve(target);
    };
    const onRevealFocus = (event) => revealTarget(event.currentTarget);
    revealTargets.forEach((target) => target.addEventListener("focusin", onRevealFocus));

    if (typeof window.IntersectionObserver === "function") {
      revealTargets.forEach((target) => target.classList.add("is-pending"));
      observer = new window.IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          revealTarget(entry.target);
        });
      }, { rootMargin: "0px 0px -8%", threshold: 0.12 });
      revealTargets.forEach((target) => observer.observe(target));
    } else {
      revealTargets.forEach((target) => target.classList.add("is-visible"));
    }

    landingCleanup = () => {
      if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
      if (heroFrame) window.cancelAnimationFrame(heroFrame);
      if (header) window.removeEventListener("scroll", onScroll);
      revealTargets.forEach((target) => target.removeEventListener("focusin", onRevealFocus));
      if (observer) observer.disconnect();
      root.removeAttribute("data-landing-motion");
    };
  }

  window.TOANAASPortalMotion = Object.freeze({
    enter,
    replace,
    prefersReducedMotion,
    mountLanding,
    unmountLanding
  });
})();
