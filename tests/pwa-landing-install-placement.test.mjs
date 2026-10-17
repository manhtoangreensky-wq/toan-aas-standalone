import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const portalCss = fs.readFileSync(path.join(root, "static", "portal", "portal.css"), "utf8");
const themeCss = fs.readFileSync(path.join(root, "static", "portal", "portal-theme.css"), "utf8");
const start = portalSource.indexOf("function syncSmartInstallBanner()");
const end = portalSource.indexOf("function dismissSmartInstallBanner()", start);
const installSync = start >= 0 && end > start ? portalSource.slice(start, end) : "";
const landingStyles = themeCss.slice(themeCss.lastIndexOf("/* R143: keep the optional install control in the landing CTA flow. */"));

test("landing PWA install actions stay inside the final CTA instead of floating over content", () => {
  assert.ok(installSync.includes('document.querySelector(".portal-landing .portal-landing-final")'));
  assert.ok(installSync.includes("const installContainer = landingInstallSlot || customerUtilitySlot || document.body;"));
  assert.ok(installSync.includes('placeInstallControl(banner, "portal-smart-install-banner--landing-inline")'));
  assert.ok(installSync.includes('placeInstallControl(fab, "portal-pwa-fab-trigger--landing-inline")'));
  assert.ok(installSync.includes("if (control.parentElement !== installContainer) installContainer.appendChild(control);"));
});

test("landing remains inline and the public fallback keeps its legacy positioning", () => {
  assert.match(portalCss, /\.portal-pwa-fab-trigger\s*\{[^}]*position:\s*fixed/su);
  assert.match(landingStyles, /\.portal-landing-final \.portal-pwa-fab-trigger--landing-inline\s*\{[^}]*position:\s*static;[^}]*inset:\s*auto;/su);
  assert.match(landingStyles, /\.portal-landing-final \.portal-smart-install-banner--landing-inline\s*\{[^}]*position:\s*static;[^}]*width:\s*100%/su);
  assert.match(landingStyles, /\.portal-landing-final \.portal-pwa-fab-trigger--landing-inline \.portal-pwa-fab-label\s*\{[^}]*display:\s*inline/su);
});

test("landing does not create an install FAB before the browser exposes a prompt", () => {
  const removed = [];
  const landingSlot = { appendChild() {} };
  const staleBanner = { remove: () => removed.push("banner") };
  const staleFab = { remove: () => removed.push("fab"), classList: { toggle() {} }, setAttribute() {}, innerHTML: "" };
  const document = {
    body: {},
    createElement: () => ({ classList: { toggle() {} }, setAttribute() {}, innerHTML: "" }),
    querySelector(selector) {
      if (selector === ".portal-landing .portal-landing-final") return landingSlot;
      if (selector === "[data-portal-smart-install-banner]") return staleBanner;
      if (selector === "[data-portal-pwa-fab]") return staleFab;
      return null;
    }
  };
  const window = {
    localStorage: { getItem: () => null },
    sessionStorage: { getItem: () => null }
  };
  const start = portalSource.indexOf("function syncSmartInstallBanner()");
  const end = portalSource.indexOf("function dismissSmartInstallBanner()", start);
  const runtime = vm.createContext({
    document,
    window,
    isStandaloneApp: () => false,
    isIosDevice: () => false,
    isAndroidDevice: () => false,
    pwaInstallCanBeOffered: () => true,
    pwaInstallPrompt: null,
    uiText: (_key, fallback) => fallback,
    portalIcon: () => "",
    ICONS: { download: "download" },
    safeText: value => String(value)
  });
  vm.runInContext(`${portalSource.slice(start, end)}\nsyncSmartInstallBanner();`, runtime);
  assert.deepEqual(removed, ["banner", "fab"]);
});
