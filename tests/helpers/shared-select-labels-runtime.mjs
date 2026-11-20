import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

export const BASE = "46423a6df9af67ac7ccabd88686d4cb42523a078";
export const DEFAULT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const FILES = Object.freeze({portal: "static/portal/portal.js", i18n: "static/portal/portal-i18n.js"});
const hash = value => createHash("sha256").update(value).digest("hex");
export const IDS = Object.freeze([
  "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
  "33333333-3333-4333-8333-333333333333", "44444444-4444-4444-8444-444444444444",
  "55555555-5555-4555-8555-555555555555", "66666666-6666-4666-8666-666666666666"
]);
export const CUSTOMER = `Facebook TikTok media studio <img src=x onerror="literal"> "quoted" 'single' &`;
export const clone = value => JSON.parse(JSON.stringify(value));
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
export function sources({root = DEFAULT_ROOT, baseline = false} = {}) {
  const resolved = path.resolve(root);
  const raw = Object.fromEntries(Object.entries(FILES).map(([key, relative]) => [key,
    baseline ? execFileSync("git", ["show", BASE + ":" + relative], {
      cwd: resolved, encoding: "utf8", maxBuffer: 30e6, windowsHide: true
    }) : fs.readFileSync(path.join(resolved, relative), "utf8")]));
  return {root: resolved, baseline, paths: Object.fromEntries(Object.entries(FILES).map(([key, relative]) => [key, path.join(resolved, relative)])),
    raw, hashes: Object.fromEntries(Object.entries(raw).map(([key, value]) => [key, hash(value)]))};
}

// The full physical renderer and real frozen i18n run in one VM. One unique
// test-local insertion exposes renderFields; no production function is replaced.
export function runtime(source, locale = "vi") {
  assert.equal(typeof source.raw.portal, "string"); assert.equal(typeof source.raw.i18n, "string");
  const attempts = [], listeners = new Map(), attributes = {};
  const noop = () => {};
  const deny = kind => (..._args) => { attempts.push(kind); throw Error("Forbidden renderer side effect: " + kind); };
  const storage = name => ({getItem: deny(name + ".getItem"), setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  const document = {
    readyState: "loading", title: "", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
    getElementById: () => null, createElement: deny("document.createElement"),
    documentElement: {lang: locale, setAttribute: (key, value) => { attributes[key] = value; },
      getAttribute: key => attributes[key] ?? null, classList: {add: noop, remove: noop}},
    body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop}
  };
  const window = {
    document, navigator: {language: locale, userAgent: "Shared select physical VM", sendBeacon: deny("sendBeacon")},
    location: {pathname: "/documents/split", search: "", href: "https://unit.invalid/documents/split",
      origin: "https://unit.invalid", assign: deny("navigation")},
    addEventListener: (name, handler) => listeners.set(name, handler), dispatchEvent: deny("dispatchEvent"),
    CustomEvent: function () {}, matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("localStorage"), sessionStorage: storage("sessionStorage"),
    fetch: deny("fetch"), XMLHttpRequest: deny("XMLHttpRequest"),
    WebSocket: deny("WebSocket"), indexedDB: {open: deny("indexedDB.open"), deleteDatabase: deny("indexedDB.deleteDatabase")},
    setTimeout: noop, clearTimeout: noop, setInterval: noop, clearInterval: noop
  };
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console,
    setTimeout: noop, clearTimeout: noop, fetch: window.fetch, XMLHttpRequest: window.XMLHttpRequest, WebSocket: window.WebSocket
  });
  vm.runInContext(source.raw.i18n, sandbox, {filename: source.paths.i18n});
  const i18n = window.TOANAASI18n;
  i18n.setLocale(locale, {emit: false});
  let translator = i18n;
  const renderWindow = Object.create(window);
  Object.defineProperty(renderWindow, "TOANAASI18n", {get: () => translator});
  sandbox.window = renderWindow;
  const marker = "  window.TOANAASPortal = Object.freeze({";
  assert.equal(source.raw.portal.split(marker).length - 1, 1, "Unique physical renderer exposure marker");
  const exposure = "  window.__sharedSelectQA = Object.freeze({renderFields});\n";
  const executed = source.raw.portal.replace(marker, exposure + marker);
  vm.runInContext(executed, sandbox, {filename: source.paths.portal});
  assert.equal(typeof renderWindow.__sharedSelectQA.renderFields, "function");
  assert.deepEqual(attempts, [], "Loading physical bundles must remain side-effect free");
  return {
    source, messages: i18n.messages,
    binding: {hashes: source.hashes, executedPortalHash: hash(executed), exposureCount: 1,
      physicalPortalBytes: Buffer.byteLength(source.raw.portal), executedPortalBytes: Buffer.byteLength(executed),
      exposureBytes: Buffer.byteLength(exposure)},
    setLocale: value => i18n.setLocale(value, {emit: false}),
    currentLocale: () => i18n.currentLocale(),
    missingTranslator: value => { translator = value === false ? i18n : undefined; },
    render(fields, enabled = true, context = {}, values = {}, namespace = "shared-select-qa") {
      const inputs = [fields, context, values], before = inputs.map(value => JSON.stringify(value));
      const html = renderWindow.__sharedSelectQA.renderFields(fields, enabled, context, values, namespace);
      assert.deepEqual(inputs.map(value => JSON.stringify(value)), before, "Caller inputs must stay byte-exact");
      assert.deepEqual(attempts, [], "Rendering cannot fetch, navigate, dispatch or access browser storage");
      return html;
    },
    attempts: () => [...attempts]
  };
}
export function asset(kind, id = IDS[0], changes = {}) {
  const image = kind === "image";
  return {id, display_name: "SYNTHETIC FILE", original_filename: image ? "synthetic.png" : "synthetic.pdf",
    extension: image ? ".png" : ".pdf", content_type: image ? "image/png" : "application/pdf",
    byte_size: 1536, state: "active", updated_at: "2026-11-20T00:00:00Z", ...changes};
}
export function context(family, rows) {
  if (family === "pdfVaultAssets") return {
    path: "/documents/split", documentAssetReferenceReadState: "ready",
    documentAssetReferences: {pdf: rows, image: [], pinned_pdf: [], pinned_image: [], pdf_listing: {}, image_listing: {}}
  };
  if (family === "imageVaultAssets") return {
    path: "/image/resize", imageOperationAssetReferenceReadState: "ready",
    imageOperationAssetReferences: {items: rows, pinned: [], listing: {}}
  };
  return {[family]: rows};
}
