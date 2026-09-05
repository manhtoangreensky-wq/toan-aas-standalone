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
  const EXPLICIT_THEMES = Object.freeze(["light", "dark"]);
  const INITIAL_SURFACES = Object.freeze({
    "/welcome": "landing",
    "/login": "auth",
    "/register": "auth",
    "/password-recovery": "auth",
    "/admin/login": "auth"
  });
  const SVG = Object.freeze({
    sun: '<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.5"></circle><path d="M12 2.5v2M12 19.5v2M4.5 4.5l1.4 1.4M18.1 18.1l1.4 1.4M2.5 12h2M19.5 12h2M4.5 19.5l1.4-1.4M18.1 5.9l1.4-1.4"></path></svg>',
    moon: '<svg class="portal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M19.2 15.6A7.8 7.8 0 0 1 8.4 4.8 8.5 8.5 0 1 0 19.2 15.6Z"></path></svg>'
  });
  const THEME_FALLBACK_LABELS = Object.freeze({
    vi: Object.freeze({ label: "Giao diện", light: "Sáng", dark: "Tối", system: "Theo hệ thống", toLight: "Chuyển sang giao diện sáng", toDark: "Chuyển sang giao diện tối", toSystem: "Dùng giao diện theo hệ thống" }),
    en: Object.freeze({ label: "Theme", light: "Light", dark: "Dark", system: "System", toLight: "Switch to light theme", toDark: "Switch to dark theme", toSystem: "Use system theme" }),
    zh: Object.freeze({ label: "主题", light: "浅色", dark: "深色", system: "跟随系统", toLight: "切换到浅色主题", toDark: "切换到深色主题", toSystem: "使用系统主题" })
  });

  function normalizedInterfaceLocale(value) {
    const source = typeof value === "string" ? value.trim().toLowerCase() : "";
    if (source === "vi" || source.startsWith("vi-")) return "vi";
    if (source === "en" || source.startsWith("en-")) return "en";
    if (source === "zh" || source.startsWith("zh-")) return "zh";
    return "";
  }

  function interfaceLocale() {
    let queryLocale = "";
    try {
      queryLocale = new URLSearchParams(global.location && global.location.search || "").get("lang") || "";
    } catch (_) { queryLocale = ""; }
    const root = global.document && global.document.documentElement;
    const documentLocale = root && (
      root.getAttribute && (root.getAttribute("data-portal-locale") || root.getAttribute("lang"))
      || root.lang
    );
    return normalizedInterfaceLocale(queryLocale) || normalizedInterfaceLocale(documentLocale) || "vi";
  }

  function valid(value) {
    return THEMES.includes(value) ? value : null;
  }

  function readPreference() {
    try {
      return valid(global.localStorage && global.localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return null;
    }
  }

  function fallbackPreference() {
    return typeof window !== "undefined" && window.location && window.location.pathname === "/welcome" ? "light" : "system";
  }

  function systemTheme() {
    try {
      return global.matchMedia && global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } catch (_) {
      return "light";
    }
  }

  function resolve(preference) {
    const selected = valid(preference) || "system";
    return selected === "system" ? systemTheme() : selected;
  }

  const storedPreference = readPreference();
  let preference = storedPreference || fallbackPreference();
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
    const fallback = THEME_FALLBACK_LABELS[interfaceLocale()] || THEME_FALLBACK_LABELS.vi;
    const t = (key, fallback) => {
      try {
        const value = i18n && typeof i18n.t === "function" ? i18n.t(key) : "";
        return typeof value === "string" && value ? value : fallback;
      } catch (_) {
        return fallback;
      }
    };
    return {
      label: t("chrome.theme_label", fallback.label),
      light: t("chrome.theme_light", fallback.light),
      dark: t("chrome.theme_dark", fallback.dark),
      system: t("chrome.theme_system", fallback.system),
      toLight: t("chrome.theme_switch_to_light", fallback.toLight),
      toDark: t("chrome.theme_switch_to_dark", fallback.toDark),
      toSystem: t("chrome.theme_switch_to_system", fallback.toSystem)
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
    const locale = interfaceLocale();
    const modeCopy = locale === "zh" ? `${copy.label}：${modeLabel}` : `${copy.label}: ${modeLabel}`;
    const actionCopy = locale === "zh" ? `${modeCopy}。${nextLabel}` : `${modeCopy}. ${nextLabel}`;
    global.document.querySelectorAll("[data-portal-theme-toggle]").forEach((control) => {
      const icon = control.querySelector("[data-portal-theme-icon]");
      const label = control.querySelector("[data-portal-theme-label]");
      if (icon) icon.innerHTML = resolved === "dark" ? SVG.sun : SVG.moon;
      if (label) label.textContent = modeCopy;
      control.setAttribute("aria-label", actionCopy);
      control.setAttribute("title", actionCopy);
      control.dataset.portalThemePreference = preference;
      control.dataset.portalThemeResolved = resolved;
    });
    global.document.querySelectorAll("[data-portal-theme-set]").forEach((control) => {
      const mode = control.dataset && control.dataset.portalThemeSet;
      if (!EXPLICIT_THEMES.includes(mode)) return;
      const active = resolved === mode;
      const modeLabel = mode === "dark" ? copy.dark : copy.light;
      control.setAttribute("aria-pressed", String(active));
      control.classList.toggle("is-active", active);
      control.setAttribute("aria-label", `${copy.label}: ${modeLabel}`);
      control.setAttribute("title", `${copy.label}: ${modeLabel}`);
    });
  }

  function setPreference(value) {
    const next = valid(value);
    if (!next) return resolved;
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
      const explicit = event.target && event.target.closest ? event.target.closest("[data-portal-theme-set]") : null;
      if (explicit) {
        const explicitTheme = explicit.dataset && explicit.dataset.portalThemeSet;
        if (!EXPLICIT_THEMES.includes(explicitTheme)) return;
        event.preventDefault();
        setPreference(explicit.dataset.portalThemeSet);
        return;
      }
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

  function applyInitialSurface() {
    if (typeof window === "undefined" || !window.location || !global.document || !global.document.documentElement) return;
    const surface = INITIAL_SURFACES[window.location.pathname];
    if (surface) {
      global.document.documentElement.setAttribute("data-portal-initial-surface", surface);
    } else {
      global.document.documentElement.removeAttribute("data-portal-initial-surface");
    }
  }

  applyInitialSurface();
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
