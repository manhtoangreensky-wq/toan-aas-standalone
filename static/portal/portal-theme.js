/* TOAN AAS Aura theme controller.
 *
 * Presentation-only state: this module never reads or writes account data,
 * calls an API, or participates in route/permission decisions.  It runs in
 * the document head so a saved preference is applied before the shell paints.
 */
(function portalTheme(global) {
  "use strict";

  const STORAGE_KEY = "toan-aas-portal-theme";
  const THEMES = Object.freeze(["system", "light", "dark"]);
  const SVG = Object.freeze({
    sun: '<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.5"></circle><path d="M12 2.5v2M12 19.5v2M4.5 4.5l1.4 1.4M18.1 18.1l1.4 1.4M2.5 12h2M19.5 12h2M4.5 19.5l1.4-1.4M18.1 5.9l1.4-1.4"></path></svg>',
    moon: '<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M19.2 15.6A7.8 7.8 0 0 1 8.4 4.8 8.5 8.5 0 1 0 19.2 15.6Z"></path></svg>'
  });

  function valid(value) {
    return THEMES.includes(value) ? value : "system";
  }

  function readPreference() {
    try {
      return valid(global.localStorage && global.localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return "system";
    }
  }

  function systemTheme() {
    try {
      return global.matchMedia && global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } catch (_) {
      return "light";
    }
  }

  function resolve(preference) {
    const selected = valid(preference);
    return selected === "system" ? systemTheme() : selected;
  }

  let preference = readPreference();
  let resolved = resolve(preference);

  function setMetaColor(theme) {
    if (!global.document || !global.document.querySelector) return;
    const meta = global.document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#0B132B" : "#063B47");
  }

  function apply(options) {
    const settings = options && typeof options === "object" ? options : {};
    resolved = resolve(preference);
    const documentElement = global.document && global.document.documentElement;
    if (documentElement) {
      documentElement.setAttribute("data-portal-theme", resolved);
      documentElement.setAttribute("data-portal-theme-preference", preference);
      documentElement.style.colorScheme = resolved;
    }
    if (global.document && global.document.body) {
      global.document.body.setAttribute("data-portal-theme", resolved);
    }
    setMetaColor(resolved);
    if (settings.sync !== false) syncControls();
  }

  function persist(value) {
    try {
      if (value === "system") global.localStorage && global.localStorage.removeItem(STORAGE_KEY);
      else if (global.localStorage) global.localStorage.setItem(STORAGE_KEY, value);
    } catch (_) {
      // Private browsing or a blocked storage policy should not break the UI.
    }
  }

  function labels() {
    const i18n = global.TOANAASI18n;
    const t = (key, fallback) => {
      try {
        const value = i18n && typeof i18n.t === "function" ? i18n.t(key) : "";
        return typeof value === "string" && value ? value : fallback;
      } catch (_) {
        return fallback;
      }
    };
    return {
      label: t("chrome.theme_label", "Giao diện"),
      light: t("chrome.theme_light", "Sáng"),
      dark: t("chrome.theme_dark", "Tối"),
      system: t("chrome.theme_system", "Theo hệ thống"),
      toLight: t("chrome.theme_switch_to_light", "Chuyển sang giao diện sáng"),
      toDark: t("chrome.theme_switch_to_dark", "Chuyển sang giao diện tối"),
      toSystem: t("chrome.theme_switch_to_system", "Dùng giao diện theo hệ thống")
    };
  }

  function nextPreference() {
    const index = THEMES.indexOf(preference);
    return THEMES[(index + 1) % THEMES.length];
  }

  function syncControls() {
    if (!global.document || !global.document.querySelectorAll) return;
    const copy = labels();
    const modeLabel = preference === "system" ? copy.system : (preference === "dark" ? copy.dark : copy.light);
    const next = nextPreference();
    const nextLabel = next === "system" ? copy.toSystem : (next === "dark" ? copy.toDark : copy.toLight);
    global.document.querySelectorAll("[data-portal-theme-toggle]").forEach((control) => {
      const icon = control.querySelector("[data-portal-theme-icon]");
      const label = control.querySelector("[data-portal-theme-label]");
      if (icon) icon.innerHTML = resolved === "dark" ? SVG.sun : SVG.moon;
      if (label) label.textContent = `${copy.label}: ${modeLabel}`;
      control.setAttribute("aria-label", `${copy.label}: ${modeLabel}. ${nextLabel}`);
      control.setAttribute("title", `${copy.label}: ${modeLabel}. ${nextLabel}`);
      control.dataset.portalThemePreference = preference;
      control.dataset.portalThemeResolved = resolved;
    });
  }

  function setPreference(value) {
    const next = valid(value);
    const previousPreference = preference;
    const previousResolved = resolved;
    preference = next;
    persist(next);
    apply();
    if (typeof global.dispatchEvent === "function" && typeof global.CustomEvent === "function" && (previousPreference !== next || previousResolved !== resolved)) {
      global.dispatchEvent(new global.CustomEvent("toanaas:theme-change", {
        detail: Object.freeze({ preference, theme: resolved, previousPreference, previousTheme: previousResolved })
      }));
    }
    return resolved;
  }

  function toggle() {
    return setPreference(nextPreference());
  }

  function onSystemChange() {
    if (preference === "system") apply();
  }

  function bind() {
    if (!global.document || global.document.__toanAasThemeBound) return;
    global.document.__toanAasThemeBound = true;
    global.document.addEventListener("click", (event) => {
      const control = event.target && event.target.closest ? event.target.closest("[data-portal-theme-toggle]") : null;
      if (!control) return;
      event.preventDefault();
      toggle();
    });
    global.addEventListener("toanaas:locale-change", () => syncControls());
    try {
      const media = global.matchMedia && global.matchMedia("(prefers-color-scheme: dark)");
      if (media) {
        if (typeof media.addEventListener === "function") media.addEventListener("change", onSystemChange);
        else if (typeof media.addListener === "function") media.addListener(onSystemChange);
      }
    } catch (_) { /* media preference is optional */ }
    // Portal mount calls `syncControls()` after replacing shell markup.  Do
    // not observe the whole body here: rendering the SVG icon changes child
    // nodes itself and would turn a broad MutationObserver into a feedback
    // loop that blocks the main thread.
    syncControls();
  }

  apply({ sync: false });
  if (global.document) {
    if (global.document.readyState === "loading") global.document.addEventListener("DOMContentLoaded", bind, { once: true });
    else bind();
  }

  global.TOANAASPortalTheme = Object.freeze({
    version: "1.0.0",
    storageKey: STORAGE_KEY,
    themes: THEMES,
    getPreference: () => preference,
    getResolvedTheme: () => resolved,
    setPreference,
    toggle,
    syncControls
  });
}(typeof window !== "undefined" ? window : globalThis));
