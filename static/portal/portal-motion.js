/* Presentation-only lifecycle helpers for the public portal shell.
   This file intentionally owns no route, request, storage or account state. */
(() => {
  "use strict";

  const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
  const ENTER_CLEAR_DELAY_MS = 500;
  // The public Landing needs a long enough one-shot sequence that visitors
  // can actually perceive it after Portal hydration. This is presentation
  // timing only; it never gates content, navigation, or an account action.
  const LANDING_SEQUENCE_SETTLE_DELAY_MS = 1900;
  const LANDING_HERO_KICKOFF_FALLBACK_MS = 90;
  let landingCleanup = null;

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
    root.setAttribute("data-landing-motion-phase", "intro");
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

    const clearLandingAttributes = () => {
      root.removeAttribute("data-landing-motion-phase");
      root.removeAttribute("data-landing-motion");
    };
    // The aperture remains a quiet static frame for motion-sensitive visitors.
    // Only animation setup is skipped; no content relies on this helper to be
    // visible or operable. Cleanup still has to run on the next route mount.
    landingCleanup = clearLandingAttributes;
    if (prefersReducedMotion()) {
      root.setAttribute("data-landing-motion-phase", "settled");
      return;
    }

    let scrollFrame = 0;
    let heroFrame = 0;
    let heroKickoffTimer = 0;
    let heroActivated = false;
    let settledTimer = 0;
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
      // Each real entry to /welcome receives an intro. The previous global
      // one-time gate made SPA navigation appear static after the first visit.
      hero.classList.remove("is-ready");
      const activateHero = () => {
        if (heroActivated) return;
        heroActivated = true;
        if (heroFrame) window.cancelAnimationFrame(heroFrame);
        if (heroKickoffTimer) window.clearTimeout(heroKickoffTimer);
        heroFrame = 0;
        heroKickoffTimer = 0;
        hero.classList.add("is-ready");
      };
      heroFrame = window.requestAnimationFrame(activateHero);
      // Background tabs and an initial long task may defer animation frames.
      // A bounded timer keeps the intro observable without creating a loop.
      heroKickoffTimer = window.setTimeout(activateHero, LANDING_HERO_KICKOFF_FALLBACK_MS);
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

    settledTimer = window.setTimeout(() => {
      settledTimer = 0;
      root.setAttribute("data-landing-motion-phase", "settled");
    }, LANDING_SEQUENCE_SETTLE_DELAY_MS);

    landingCleanup = () => {
      if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
      if (heroFrame) window.cancelAnimationFrame(heroFrame);
      if (heroKickoffTimer) window.clearTimeout(heroKickoffTimer);
      if (settledTimer) window.clearTimeout(settledTimer);
      if (header) window.removeEventListener("scroll", onScroll);
      revealTargets.forEach((target) => target.removeEventListener("focusin", onRevealFocus));
      if (observer) observer.disconnect();
      clearLandingAttributes();
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
