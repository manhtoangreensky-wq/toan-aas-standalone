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
  const LANDING_HERO_KICKOFF_FALLBACK_MS = 160;
  // The preview demonstrates the real Web workflow in a short, bounded
  // sequence. It is intentionally replayable instead of running forever.
  const LANDING_PREVIEW_STEP_START_DELAY_MS = 460;
  const LANDING_PREVIEW_STEP_INTERVAL_MS = 360;
  let landingCleanup = null;
  let landingGeneration = 0;

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
    const cleanup = landingCleanup;
    landingCleanup = null;
    // In-flight RAF/timer/observer deliveries can race cancellation during a
    // route replacement.  Invalidate their generation before cleanup runs so
    // a stale callback can never mutate the old or newly rendered landing.
    landingGeneration += 1;
    if (typeof cleanup === "function") cleanup();
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
    const previewSteps = preview
      ? Array.from(preview.querySelectorAll(".portal-landing-preview-steps > span"))
      : [];
    const heroStages = hero
      ? Array.from(root.querySelectorAll(
        ".portal-landing-hero-copy, .portal-landing-hero-actions, .portal-landing-proof, .portal-landing-preview"
      ))
      : [];
    const revealDetails = revealTargets.map((target) => ({
      target,
      title: target.querySelector(
        ".portal-landing-section-heading, .portal-landing-workflow > div, .portal-landing-trust-copy, .portal-landing-final > div"
      ),
      cards: Array.from(target.querySelectorAll(
        ".portal-landing-studio, .portal-landing-workflow li, .portal-landing-trust-grid > article"
      ))
    }));
    const landingCtas = Array.from(root.querySelectorAll(".portal-button"));
    const replayControl = root.querySelector("[data-landing-motion-replay]");
    const generation = landingGeneration;
    const isCurrentMount = () => landingGeneration === generation;
    if (header) header.classList.add("landing-motion-header");
    if (hero) hero.classList.add("landing-motion-hero", "landing-cinematic-hero");
    if (preview) {
      preview.classList.add("landing-cinematic-preview");
      previewSteps.forEach((step) => step.classList.add("landing-cinematic-step"));
    }

    const clearLandingDecorations = () => {
      root.removeAttribute("data-landing-motion-phase");
      root.removeAttribute("data-landing-motion");
      if (header) {
        header.classList.remove("landing-motion-header");
        header.removeAttribute("data-landing-motion-header");
      }
      if (hero) hero.classList.remove("landing-motion-hero", "landing-cinematic-hero", "is-ready");
      if (preview) preview.classList.remove("landing-cinematic-preview");
      previewSteps.forEach((step) => step.classList.remove("landing-cinematic-step", "landing-motion-step-active"));
      root.removeAttribute("data-landing-motion-run");
      heroStages.forEach((stage) => stage.classList.remove("landing-motion-hero-stage"));
      revealDetails.forEach(({ target, title, cards }) => {
        target.classList.remove(
          "landing-motion-reveal",
          "landing-motion-workflow",
          "landing-motion-final",
          "is-pending",
          "is-visible"
        );
        if (title) title.classList.remove("landing-motion-reveal-title");
        cards.forEach((card) => card.classList.remove("landing-motion-card"));
      });
      landingCtas.forEach((cta) => cta.classList.remove("landing-motion-cta"));
    };
    // The aperture remains a quiet static frame for motion-sensitive visitors.
    // Only animation setup is skipped; no content relies on this helper to be
    // visible or operable. Cleanup still has to run on the next route mount.
    landingCleanup = clearLandingDecorations;
    if (prefersReducedMotion()) {
      root.setAttribute("data-landing-motion-phase", "settled");
      return;
    }

    let scrollFrame = 0;
    let heroFrame = 0;
    let heroKickoffTimer = 0;
    let heroActivated = false;
    let settledTimer = 0;
    let previewStepTimers = [];
    let introRun = 0;
    let observer = null;

    const clearIntroSchedule = () => {
      if (heroFrame) window.cancelAnimationFrame(heroFrame);
      if (heroKickoffTimer) window.clearTimeout(heroKickoffTimer);
      if (settledTimer) window.clearTimeout(settledTimer);
      previewStepTimers.forEach((timer) => window.clearTimeout(timer));
      heroFrame = 0;
      heroKickoffTimer = 0;
      settledTimer = 0;
      previewStepTimers = [];
    };
    const setActivePreviewStep = (activeIndex) => {
      previewSteps.forEach((step, index) => {
        if (index === activeIndex) step.classList.add("landing-motion-step-active");
        else step.classList.remove("landing-motion-step-active");
      });
    };
    const schedulePreviewSteps = (run) => {
      previewSteps.forEach((_step, index) => {
        if (index === 0) return;
        const timer = window.setTimeout(() => {
          if (!isCurrentMount() || run !== introRun) return;
          setActivePreviewStep(index);
        }, LANDING_PREVIEW_STEP_START_DELAY_MS + ((index - 1) * LANDING_PREVIEW_STEP_INTERVAL_MS));
        previewStepTimers.push(timer);
      });
    };
    const settleIntro = (run) => {
      settledTimer = window.setTimeout(() => {
        if (!isCurrentMount() || run !== introRun) return;
        settledTimer = 0;
        root.setAttribute("data-landing-motion-phase", "settled");
      }, LANDING_SEQUENCE_SETTLE_DELAY_MS);
    };
    const replayIntro = () => {
      if (!isCurrentMount()) return;
      clearIntroSchedule();
      const run = ++introRun;
      heroActivated = false;
      root.setAttribute("data-landing-motion-phase", "intro");
      root.setAttribute("data-landing-motion-run", String(run));
      if (hero) {
        hero.classList.remove("is-ready");
        // Force a style boundary so a replay always restarts the CSS timeline.
        void hero.offsetWidth;
      }
      setActivePreviewStep(0);
      if (prefersReducedMotion()) return;

      const activateHero = () => {
        if (!isCurrentMount() || run !== introRun || heroActivated) return;
        heroActivated = true;
        if (heroFrame) window.cancelAnimationFrame(heroFrame);
        if (heroKickoffTimer) window.clearTimeout(heroKickoffTimer);
        heroFrame = 0;
        heroKickoffTimer = 0;
        if (hero) hero.classList.add("is-ready");
        schedulePreviewSteps(run);
        // The countdown begins only after the browser has painted the initial
        // state and the visible hero sequence has actually started.
        settleIntro(run);
      };
      if (hero) {
        heroFrame = window.requestAnimationFrame(() => {
          if (!isCurrentMount() || run !== introRun) return;
          // A second animation frame gives the browser a real pre-animation
          // paint. Without it, fast devices can jump straight to the final
          // state and make a valid motion sequence look like no motion at all.
          heroFrame = window.requestAnimationFrame(activateHero);
        });
        // Background tabs and an initial long task may defer animation frames.
        // A bounded timer keeps the intro observable without creating a loop.
        heroKickoffTimer = window.setTimeout(activateHero, LANDING_HERO_KICKOFF_FALLBACK_MS);
      } else {
        schedulePreviewSteps(run);
        settleIntro(run);
      }
    };

    const syncHeader = () => {
      scrollFrame = 0;
      if (!isCurrentMount()) return;
      if (!header) return;
      header.setAttribute(
        "data-landing-motion-header",
        window.scrollY > 20 ? "compact" : "default"
      );
    };
    const onScroll = () => {
      if (!isCurrentMount()) return;
      if (scrollFrame) return;
      scrollFrame = window.requestAnimationFrame(syncHeader);
    };

    if (header) {
      syncHeader();
      window.addEventListener("scroll", onScroll, { passive: true });
    }

    if (hero) heroStages.forEach((stage) => stage.classList.add("landing-motion-hero-stage"));

    revealDetails.forEach(({ target, title, cards }) => {
      target.classList.add("landing-motion-reveal");
      if (target.matches(".portal-landing-workflow")) target.classList.add("landing-motion-workflow");
      if (target.matches(".portal-landing-final")) target.classList.add("landing-motion-final");
      if (title) title.classList.add("landing-motion-reveal-title");
      cards.forEach((card) => card.classList.add("landing-motion-card"));
    });
    landingCtas.forEach((cta) => cta.classList.add("landing-motion-cta"));
    if (replayControl) replayControl.addEventListener("click", replayIntro);

    const revealTarget = (target) => {
      if (!isCurrentMount()) return;
      target.classList.remove("is-pending");
      target.classList.add("is-visible");
      if (observer) observer.unobserve(target);
    };
    const onRevealFocus = (event) => revealTarget(event.currentTarget);
    revealTargets.forEach((target) => target.addEventListener("focusin", onRevealFocus));

    if (typeof window.IntersectionObserver === "function") {
      revealTargets.forEach((target) => target.classList.add("is-pending"));
      observer = new window.IntersectionObserver((entries) => {
        if (!isCurrentMount()) return;
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          revealTarget(entry.target);
        });
      }, { rootMargin: "0px 0px -8%", threshold: 0.12 });
      revealTargets.forEach((target) => observer.observe(target));
    } else {
      revealTargets.forEach((target) => target.classList.add("is-visible"));
    }

    // Start the first bounded sequence after all lifecycle listeners are in
    // place. The same function is used by the visible replay control.
    replayIntro();

    landingCleanup = () => {
      clearIntroSchedule();
      if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
      if (header) window.removeEventListener("scroll", onScroll);
      revealTargets.forEach((target) => target.removeEventListener("focusin", onRevealFocus));
      if (replayControl) replayControl.removeEventListener("click", replayIntro);
      if (observer) observer.disconnect();
      clearLandingDecorations();
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
