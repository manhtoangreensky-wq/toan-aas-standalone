/* Presentation-only lifecycle helpers for the public portal shell.
   This file intentionally owns no route, request, storage or account state. */
(() => {
  "use strict";

  const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
  const ENTER_CLEAR_DELAY_MS = 500;
  // Scroll observers are an optional visual enhancement.  A missing observer
  // delivery must never leave a complete, interactive workspace transparent.
  const WORKSPACE_REVEAL_FALLBACK_MS = 900;
  // The public Landing needs a long enough one-shot sequence that visitors
  // can actually perceive it after Portal hydration. This is presentation
  // timing only; it never gates content, navigation, or an account action.
  // Keep the opening sequence observable after a normal page paint.  The
  // previous 1.9s window was technically correct, but most visitors only
  // noticed the final static frame after fonts and hydration had settled.
  const LANDING_SEQUENCE_SETTLE_DELAY_MS = 7600;
  const LANDING_HERO_KICKOFF_FALLBACK_MS = 160;
  // The preview demonstrates the real Web workflow in a short, bounded
  // sequence. It is intentionally replayable instead of running forever.
  const LANDING_PREVIEW_STEP_START_DELAY_MS = 620;
  const LANDING_PREVIEW_STEP_INTERVAL_MS = 900;
  const LANDING_PREVIEW_CYCLE_PAUSE_MS = 700;
  const LANDING_PREVIEW_CYCLE_COUNT = 2;
  const LANDING_SCROLL_POINTER_QUERY = "(hover: hover) and (pointer: fine)";
  let landingCleanup = null;
  let landingGeneration = 0;
  let workspaceCleanup = null;
  let workspaceGeneration = 0;

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, Number(value) || 0));
  }

  function setStyleProperty(element, property, value) {
    if (!element || !element.style || typeof element.style.setProperty !== "function") return;
    element.style.setProperty(property, String(value));
  }

  function removeStyleProperty(element, property) {
    if (!element || !element.style || typeof element.style.removeProperty !== "function") return;
    element.style.removeProperty(property);
  }

  function setReplayAvailability(replayControl, enabled) {
    if (!replayControl) return;
    replayControl.hidden = !enabled;
    replayControl.disabled = !enabled;
    if (enabled) {
      replayControl.removeAttribute("data-landing-motion-replay-disabled");
      replayControl.removeAttribute("aria-hidden");
      return;
    }
    replayControl.setAttribute("data-landing-motion-replay-disabled", "true");
    replayControl.setAttribute("aria-hidden", "true");
  }

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

  // Signed workspace motion is a thin lifecycle enhancement. It has no
  // access to route data, account state, storage, actions, requests or feature
  // readiness. Portal calls it only after the semantic workspace is rendered.
  function unmountWorkspace() {
    const cleanup = workspaceCleanup;
    workspaceCleanup = null;
    workspaceGeneration += 1;
    if (typeof cleanup === "function") cleanup();
  }

  function mountWorkspace(root) {
    unmountWorkspace();
    if (!root || typeof window !== "object" || prefersReducedMotion()) return;

    // Dashboard motion is deliberately limited to Web-owned decision layers.
    // Its summary and canonical read lane remain immediately readable because
    // this presentation helper never treats account or integration state as
    // an animation prerequisite.
    const dashboardDecisionSelector = [
      "[data-dashboard-start-guide]",
      ".portal-dashboard-app .portal-command-center-lane--work",
      ".portal-dashboard-app .portal-command-center-lane--account",
      ".portal-dashboard-app .portal-studio-section",
      ".portal-dashboard-app .portal-dashboard-assurance"
    ].join(", ");
    const targetSelector = [
      ".portal-feature-directory-controls",
      ".portal-catalog-context",
      ".portal-feature-catalog > .portal-section-heading",
      ".portal-feature-guided-start",
      ".portal-feature-family-explorer",
      ".portal-capability-hub",
      ".portal-catalog-search",
      ".portal-feature-jumps",
      ".portal-feature-studio-continuation",
      ".portal-feature-group",
      ".portal-media-studio-shell .portal-media-studio-intro",
      ".portal-media-studio-shell .portal-media-studio-flow",
      ".portal-media-studio-shell .portal-media-studio-handoff",
      ".portal-workspace-menu-intro",
      ".portal-workspace-menu-group",
      ".portal-workspace-menu-boundary",
      ".portal-workspace-drafts > .portal-card"
    ].join(", ");
    const itemSelector = [
      ".portal-start-guide-step",
      ".portal-feature-family-explorer-card",
      ".portal-capability-hub-card",
      ".portal-feature-jump",
      ".portal-catalog-item",
      ".portal-media-studio-step",
      ".portal-workspace-menu-card",
      ".portal-workspace-draft",
      ".portal-workspace-draft-attach"
    ].join(", ");
    const dashboardItemSelector = [
      ".portal-start-guide-step",
      ".portal-dashboard-focus-card",
      ".portal-dashboard-draft",
      ".portal-command-center-lane-actions .portal-button",
      ".portal-studio-card",
      ".portal-dashboard-assurance > summary"
    ].join(", ");
    const dashboardTargets = Array.from(root.querySelectorAll(dashboardDecisionSelector));
    const dashboardTargetSet = new Set(dashboardTargets);
    const rawTargets = Array.from(new Set([
      ...Array.from(root.querySelectorAll(targetSelector)),
      ...dashboardTargets
    ]));
    // The AI Studio directory is one bounded reveal surface. Its search,
    // family explorer and jump navigation remain interactive children, but
    // must not become independent observers or receive a second fade/stagger.
    // Keep the same selectors for standalone family pages where no directory
    // boundary exists.
    const targets = rawTargets.filter((target) => {
      const boundary = target.closest && target.closest(".portal-feature-directory-controls");
      return !boundary || target === boundary;
    });
    if (!targets.length) return;
    const targetDetails = targets.map((target) => {
      const dashboardDecision = dashboardTargetSet.has(target);
      return {
        target,
        targetClass: dashboardDecision ? "portal-dashboard-motion-target" : "portal-workspace-motion-target",
        itemClass: dashboardDecision ? "portal-dashboard-motion-item" : "portal-workspace-motion-item",
        itemIndexProperty: dashboardDecision
          ? "--portal-dashboard-motion-index"
          : "--portal-workspace-motion-index",
        itemSelector: dashboardDecision ? dashboardItemSelector : itemSelector
      };
    });

    const generation = workspaceGeneration;
    const isCurrentMount = () => workspaceGeneration === generation;
    const focusHandlers = [];
    let observer = null;
    let revealFallbackTimer = 0;
    let removeReducedMotionListener = () => {};
    const revealTarget = (target) => {
      if (!isCurrentMount() || !target) return;
      target.classList.remove("is-pending");
      target.classList.add("is-visible");
      if (observer) observer.unobserve(target);
    };

    targetDetails.forEach(({ target, targetClass, itemClass, itemIndexProperty, itemSelector: selector }) => {
      target.classList.add(targetClass, "is-pending");
      Array.from(target.querySelectorAll(selector)).slice(0, 6).forEach((item, index) => {
        item.classList.add(itemClass);
        setStyleProperty(item, itemIndexProperty, index);
      });
      const onFocus = (event) => revealTarget(event.currentTarget);
      target.addEventListener("focusin", onFocus);
      focusHandlers.push({ target, onFocus });
    });

    if (typeof window.IntersectionObserver === "function") {
      observer = new window.IntersectionObserver((entries) => {
        if (!isCurrentMount()) return;
        entries.forEach((entry) => {
          if (entry.isIntersecting) revealTarget(entry.target);
        });
      // Reveal as soon as a primary group enters the readable viewport. A
      // higher ratio can leave the first visible part of a tall group blank,
      // which reads as unfinished content rather than a deliberate entrance.
      }, { rootMargin: "0px 0px -8%", threshold: 0 });
      targets.forEach((target) => observer.observe(target));
    } else {
      targets.forEach(revealTarget);
    }

    // Browser layout/observer delivery can be interrupted by an extension,
    // background tab transition or an implementation defect.  Preserve the
    // semantic page by completing the optional reveal after a short bounded
    // window rather than relying on scrolling or focus to recover it.  The
    // narrow DOM harness used for static portal checks does not supply timer
    // APIs, so it gets the same immediate no-observer safety outcome.
    const timerHost = typeof window.setTimeout === "function" && typeof window.clearTimeout === "function"
      ? window
      : null;
    if (timerHost) {
      revealFallbackTimer = timerHost.setTimeout(() => {
        if (!isCurrentMount()) return;
        targets.forEach(revealTarget);
      }, WORKSPACE_REVEAL_FALLBACK_MS);
    } else {
      targets.forEach(revealTarget);
    }

    // An OS preference can change while this signed page remains open. Stop
    // this optional presentation layer immediately and restore its semantic
    // content instead of leaving a pending/staggered group in the DOM until a
    // route change or reload. We intentionally do not restart the animation
    // when the preference changes back: static content is the calmest state
    // and a future Portal mount can opt in again.
    if (typeof window.matchMedia === "function") {
      const reducedMotionMedia = window.matchMedia(REDUCED_MOTION_QUERY);
      const onReducedMotionChange = (event) => {
        if (event && event.matches) unmountWorkspace();
      };
      if (reducedMotionMedia && typeof reducedMotionMedia.addEventListener === "function") {
        reducedMotionMedia.addEventListener("change", onReducedMotionChange);
        removeReducedMotionListener = () => reducedMotionMedia.removeEventListener("change", onReducedMotionChange);
      } else if (reducedMotionMedia && typeof reducedMotionMedia.addListener === "function") {
        reducedMotionMedia.addListener(onReducedMotionChange);
        removeReducedMotionListener = () => reducedMotionMedia.removeListener(onReducedMotionChange);
      }
    }

    workspaceCleanup = () => {
      if (observer) observer.disconnect();
      if (revealFallbackTimer && timerHost) timerHost.clearTimeout(revealFallbackTimer);
      removeReducedMotionListener();
      focusHandlers.forEach(({ target, onFocus }) => target.removeEventListener("focusin", onFocus));
      targetDetails.forEach(({ target, targetClass, itemClass, itemIndexProperty }) => {
        target.classList.remove(targetClass, "is-pending", "is-visible");
        Array.from(target.querySelectorAll(`.${itemClass}`)).forEach((item) => {
          item.classList.remove(itemClass);
          removeStyleProperty(item, itemIndexProperty);
        });
      });
    };
  }

  function mountLanding(root) {
    unmountLanding();
    if (!root || typeof window !== "object") return;

    root.setAttribute("data-landing-motion", "cinematic-mini");
    root.setAttribute("data-landing-scroll-motion", "active");
    root.setAttribute("data-landing-scroll-progress", "0");
    root.setAttribute("data-landing-motion-phase", "intro");
    if (root.classList && typeof root.classList.add === "function") root.classList.add("landing-motion-scroll");
    const header = root.querySelector(".portal-landing-header");
    const hero = root.querySelector(".portal-landing-hero");
    const preview = root.querySelector(".portal-landing-preview");
    const scrollLayers = Array.from(root.querySelectorAll("[data-landing-layer]"));
    const pointerTargets = Array.from(root.querySelectorAll(
      "[data-landing-pointer], .portal-landing-spotlight-preview, .portal-landing-workflow li, .portal-landing-trust-grid > article, .portal-landing-final .portal-button"
    ));
    // Preserve the established landing selector while adding the new
    // reference-first sections as independent semantic scenes. This only
    // enhances their presentation after render; it never gates a route or
    // product action.
    const revealTargets = Array.from(new Set([
      ...Array.from(root.querySelectorAll(
        ".portal-landing-section, .portal-landing-workflow, .portal-landing-trust, .portal-landing-final"
      )),
      ...Array.from(root.querySelectorAll(
        ".portal-landing-feature-strip, .portal-landing-spotlights"
      ))
    ]));
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
        ".portal-landing-section-heading, .portal-landing-workflow > div, .portal-landing-trust-copy, .portal-landing-final > div, .portal-landing-spotlight-copy"
      ),
      cards: Array.from(target.querySelectorAll(
        ".portal-landing-studio, .portal-landing-workflow li, .portal-landing-trust-grid > article, .portal-landing-feature-strip article, .portal-landing-spotlight"
      ))
    }));
    const landingCtas = Array.from(root.querySelectorAll(".portal-button"));
    const replayControl = root.querySelector("[data-landing-motion-replay]");
    setReplayAvailability(replayControl, !prefersReducedMotion());
    const generation = landingGeneration;
    const isCurrentMount = () => landingGeneration === generation;
    let pointerHandlers = [];
    if (header) header.classList.add("landing-motion-header");
    if (hero) hero.classList.add("landing-motion-hero", "landing-cinematic-hero");
    if (preview) {
      preview.classList.add("landing-cinematic-preview", "landing-motion-parallax");
      previewSteps.forEach((step) => step.classList.add("landing-cinematic-step"));
    }
    scrollLayers.forEach((layer) => {
      if (!layer || !layer.classList || typeof layer.classList.add !== "function") return;
      const layerName = layer.getAttribute && layer.getAttribute("data-landing-layer");
      layer.classList.add("landing-scroll-scene");
      if (layerName && /^[a-z]+$/.test(String(layerName))) layer.classList.add(`landing-motion-${layerName}`);
    });

    const clearLandingDecorations = () => {
      root.removeAttribute("data-landing-motion-phase");
      root.removeAttribute("data-landing-motion");
      root.removeAttribute("data-landing-scroll-motion");
      root.removeAttribute("data-landing-scroll-progress");
      root.removeAttribute("data-landing-motion-section");
      if (root.classList && typeof root.classList.remove === "function") root.classList.remove("landing-motion-scroll");
      ["--landing-scroll-progress", "--landing-hero-progress", "--landing-pointer-x", "--landing-pointer-y"].forEach((property) => removeStyleProperty(root, property));
      if (header) {
        header.classList.remove("landing-motion-header");
        header.removeAttribute("data-landing-motion-header");
      }
      if (hero) hero.classList.remove("landing-motion-hero", "landing-cinematic-hero", "is-ready");
      if (preview) preview.classList.remove("landing-cinematic-preview", "landing-motion-parallax", "landing-motion-pointer", "is-pointer-active");
      previewSteps.forEach((step) => step.classList.remove("landing-cinematic-step", "landing-motion-step-active", "is-active"));
      if (previewSteps[0]) previewSteps[0].classList.add("is-active");
      root.removeAttribute("data-landing-motion-run");
      heroStages.forEach((stage) => stage.classList.remove("landing-motion-hero-stage"));
      revealDetails.forEach(({ target, title, cards }) => {
        target.classList.remove(
          "landing-motion-reveal",
          "landing-motion-features",
          "landing-motion-spotlights",
          "landing-motion-workflow",
          "landing-motion-final",
          "is-pending",
          "is-visible"
        );
        if (title) title.classList.remove("landing-motion-reveal-title");
        cards.forEach((card) => card.classList.remove(
          "landing-motion-card",
          "landing-motion-studio",
          "landing-motion-feature",
          "landing-motion-spotlight"
        ));
      });
      scrollLayers.forEach((layer) => {
        if (layer && layer.classList && typeof layer.classList.remove === "function") {
          layer.classList.remove(
            "landing-scroll-scene",
            "landing-motion-hero",
            "landing-motion-features",
            "landing-motion-spotlights",
            "landing-motion-studios",
            "landing-motion-workflow",
            "landing-motion-trust",
            "landing-motion-final"
          );
        }
        ["--landing-section-progress", "--landing-section-offset"].forEach((property) => removeStyleProperty(layer, property));
      });
      pointerHandlers.forEach(({ target, move, leave }) => {
        if (!target || typeof target.removeEventListener !== "function") return;
        target.removeEventListener("pointermove", move);
        target.removeEventListener("pointerleave", leave);
        target.removeEventListener("pointercancel", leave);
        if (target.classList && typeof target.classList.remove === "function") target.classList.remove("landing-motion-pointer", "is-pointer-active");
        ["--landing-pointer-x", "--landing-pointer-y"].forEach((property) => removeStyleProperty(target, property));
      });
      pointerHandlers = [];
      landingCtas.forEach((cta) => cta.classList.remove("landing-motion-cta"));
      setReplayAvailability(replayControl, true);
    };
    // The aperture remains a quiet static frame for motion-sensitive visitors.
    // Only animation setup is skipped; no content relies on this helper to be
    // visible or operable. Cleanup still has to run on the next route mount.
    landingCleanup = clearLandingDecorations;
    if (prefersReducedMotion()) {
      root.setAttribute("data-landing-scroll-motion", "static");
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

    const syncScrollMotion = () => {
      if (!isCurrentMount()) return;
      const viewportHeight = Math.max(1, Number(window.innerHeight) || 800);
      const scrollY = Math.max(0, Number(window.scrollY) || 0);
      const documentElement = typeof document === "object" && document ? document.documentElement : null;
      const documentHeight = Math.max(viewportHeight, Number(documentElement && documentElement.scrollHeight) || viewportHeight);
      const pageProgress = clamp(scrollY / Math.max(1, documentHeight - viewportHeight), 0, 1);
      setStyleProperty(root, "--landing-scroll-progress", pageProgress.toFixed(4));
      root.setAttribute("data-landing-scroll-progress", String(Math.round(pageProgress * 100)));

      const heroRect = hero && typeof hero.getBoundingClientRect === "function" ? hero.getBoundingClientRect() : null;
      const heroProgress = heroRect
        ? clamp((viewportHeight * 0.38 - Number(heroRect.top || 0)) / Math.max(1, Number(heroRect.height || viewportHeight) * 0.86), 0, 1)
        : pageProgress;
      setStyleProperty(root, "--landing-hero-progress", heroProgress.toFixed(4));
      setStyleProperty(hero, "--landing-hero-progress", heroProgress.toFixed(4));

      let activeLayer = "hero";
      let activeDistance = Number.POSITIVE_INFINITY;
      scrollLayers.forEach((layer) => {
        if (!layer || typeof layer.getBoundingClientRect !== "function") return;
        const rect = layer.getBoundingClientRect();
        const height = Math.max(1, Number(rect.height) || viewportHeight);
        const center = Number(rect.top || 0) + (height / 2);
        const travel = Math.max(1, (height + viewportHeight) * 0.55);
        const progress = clamp(1 - (Math.abs(center - (viewportHeight * 0.52)) / travel), 0, 1);
        const distance = clamp((center - (viewportHeight * 0.52)) / travel, -1, 1);
        setStyleProperty(layer, "--landing-section-progress", progress.toFixed(4));
        setStyleProperty(layer, "--landing-section-offset", `${Math.round(distance * 18)}px`);
        if (layer.getAttribute) {
          const name = String(layer.getAttribute("data-landing-layer") || "");
          const currentDistance = Math.abs(center - (viewportHeight * 0.52));
          if (name && currentDistance < activeDistance) {
            activeDistance = currentDistance;
            activeLayer = name;
          }
        }
      });
      root.setAttribute("data-landing-motion-section", activeLayer);
    };

    const resetPointer = (target) => {
      if (!target) return;
      removeStyleProperty(target, "--landing-pointer-x");
      removeStyleProperty(target, "--landing-pointer-y");
      if (target.classList && typeof target.classList.remove === "function") target.classList.remove("is-pointer-active");
    };

    const setupPointerMotion = () => {
      const pointerFine = typeof window.matchMedia !== "function"
        || window.matchMedia(LANDING_SCROLL_POINTER_QUERY).matches;
      if (!pointerFine) return;
      pointerTargets.forEach((target) => {
        if (!target || typeof target.addEventListener !== "function") return;
        if (target.classList && typeof target.classList.add === "function") target.classList.add("landing-motion-pointer");
        const move = (event) => {
          if (!isCurrentMount() || !event || typeof target.getBoundingClientRect !== "function") return;
          const rect = target.getBoundingClientRect();
          const width = Math.max(1, Number(rect.width) || 1);
          const height = Math.max(1, Number(rect.height) || 1);
          const x = clamp(((Number(event.clientX) - Number(rect.left || 0)) / width) * 2 - 1, -1, 1);
          const y = clamp(((Number(event.clientY) - Number(rect.top || 0)) / height) * 2 - 1, -1, 1);
          setStyleProperty(target, "--landing-pointer-x", x.toFixed(3));
          setStyleProperty(target, "--landing-pointer-y", y.toFixed(3));
          if (target.classList && typeof target.classList.add === "function") target.classList.add("is-pointer-active");
        };
        const leave = () => resetPointer(target);
        target.addEventListener("pointermove", move, { passive: true });
        target.addEventListener("pointerleave", leave, { passive: true });
        target.addEventListener("pointercancel", leave, { passive: true });
        pointerHandlers.push({ target, move, leave });
      });
    };

    const clearIntroSchedule = () => {
      if (heroFrame) window.cancelAnimationFrame(heroFrame);
      if (heroKickoffTimer) window.clearTimeout(heroKickoffTimer);
      if (settledTimer) window.clearTimeout(settledTimer);
      previewStepTimers.forEach((timer) => window.clearTimeout(timer));
      heroFrame = 0;
      heroKickoffTimer = 0;
      settledTimer = 0;
      previewStepTimers = [];
      root.removeAttribute("data-landing-motion-playback");
    };
    const setActivePreviewStep = (activeIndex) => {
      previewSteps.forEach((step, index) => {
        if (index === activeIndex) {
          step.classList.add("landing-motion-step-active", "is-active");
        } else {
          step.classList.remove("landing-motion-step-active", "is-active");
        }
      });
    };
    const schedulePreviewSteps = (run) => {
      if (previewSteps.length < 2) return;
      root.setAttribute("data-landing-motion-playback", "active");
      const cycleSpan = ((previewSteps.length - 1) * LANDING_PREVIEW_STEP_INTERVAL_MS)
        + LANDING_PREVIEW_CYCLE_PAUSE_MS;
      for (let cycle = 0; cycle < LANDING_PREVIEW_CYCLE_COUNT; cycle += 1) {
        previewSteps.forEach((_step, index) => {
          if (index === 0) return;
          const delay = LANDING_PREVIEW_STEP_START_DELAY_MS
            + (cycle * cycleSpan)
            + ((index - 1) * LANDING_PREVIEW_STEP_INTERVAL_MS);
          const timer = window.setTimeout(() => {
            if (!isCurrentMount() || run !== introRun) return;
            setActivePreviewStep(index);
          }, delay);
          previewStepTimers.push(timer);
        });
        // Return briefly to the first stage between bounded playback cycles;
        // this makes the workflow direction legible without an infinite loop.
        if (cycle < LANDING_PREVIEW_CYCLE_COUNT - 1) {
          const resetTimer = window.setTimeout(() => {
            if (!isCurrentMount() || run !== introRun) return;
            setActivePreviewStep(0);
          }, LANDING_PREVIEW_STEP_START_DELAY_MS
            + (cycle * cycleSpan)
            + ((previewSteps.length - 1) * LANDING_PREVIEW_STEP_INTERVAL_MS)
            + 320);
          previewStepTimers.push(resetTimer);
        }
      }
    };
    const settleIntro = (run) => {
      settledTimer = window.setTimeout(() => {
        if (!isCurrentMount() || run !== introRun) return;
        settledTimer = 0;
        root.removeAttribute("data-landing-motion-playback");
        root.setAttribute("data-landing-motion-phase", "settled");
        // A settled preview returns to its neutral first step. The public
        // landing communicates a guarded plan, never a completed delivery.
        setActivePreviewStep(0);
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
      if (header) {
        header.setAttribute(
          "data-landing-motion-header",
          window.scrollY > 20 ? "compact" : "default"
        );
      }
      syncScrollMotion();
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

    if (!header) syncScrollMotion();

    if (hero) heroStages.forEach((stage) => stage.classList.add("landing-motion-hero-stage"));

    revealDetails.forEach(({ target, title, cards }) => {
      target.classList.add("landing-motion-reveal");
      if (target.matches(".portal-landing-feature-strip")) target.classList.add("landing-motion-features");
      if (target.matches(".portal-landing-spotlights")) target.classList.add("landing-motion-spotlights");
      if (target.matches(".portal-landing-workflow")) target.classList.add("landing-motion-workflow");
      if (target.matches(".portal-landing-final")) target.classList.add("landing-motion-final");
      if (title) title.classList.add("landing-motion-reveal-title");
      cards.forEach((card) => {
        card.classList.add("landing-motion-card");
        if (target.matches && target.matches(".portal-landing-section")) card.classList.add("landing-motion-studio");
        if (target.matches && target.matches(".portal-landing-feature-strip")) card.classList.add("landing-motion-feature");
        if (target.matches && target.matches(".portal-landing-spotlights")) card.classList.add("landing-motion-spotlight");
      });
    });
    landingCtas.forEach((cta) => cta.classList.add("landing-motion-cta"));
    if (replayControl) replayControl.addEventListener("click", replayIntro);
    setupPointerMotion();

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
    unmountLanding,
    mountWorkspace,
    unmountWorkspace
  });
})();
