import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";
import {fileURLToPath} from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze(["11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"]);
export const ACTION = "audio-hub-review-pack-compose";
export const ROUTE = "/audio-hub/" + IDS[0];
export const CONTRACT = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/audio-review-contract.json"), "utf8"));
export const plain = value => JSON.parse(JSON.stringify(value));
export const hash = value => createHash("sha256").update(value).digest("hex");
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
export function boundary() {
  return {execution: "web_native_collection_review_only", collection_mutated: false,
    review_pack_persisted: false, approval_recorded: false, input_persisted: false,
    source_audio_inspected: false, source_video_inspected: false, provider_called: false,
    catalog_searched: false, player_opened: false, preview_created: false, audio_created: false,
    output_created: false, job_created: false, wallet_mutated: false, payment_started: false,
    asset_saved: false, delivery_created: false, bot_called: false, telegram_called: false,
    rights_verified: false, release_approved: false};
}
export function receipt() {
  const rows = CONTRACT.resultRows;
  return {...boundary(), collection_id: IDS[0], revision: 7, review_pack: {
    review_state: "needs_reference_metadata", policy: {status: "clear", marker: null},
    reference_summary: {total: 3, music: 1, sfx: 1, reference: 1, favorite: 1,
      duration_declared: 2, attribution_missing: 1, license_missing: 1,
      unavailable: 1, collection_rights_note_declared: true},
    checks: ["brief_originality", "reference_metadata", "mix_accessibility", "release_handoff"]
      .map((id, index) => ({id, state: index === 1 ? "needs_metadata" : "needs_human_review",
        label: rows[index * 2].old, note: rows[index * 2 + 1].old})),
    cautions: rows.slice(8).map(row => row.old)
  }};
}
export function reply(data = receipt(), {ok = true, status = "draft", message, httpStatus = 200} = {}) {
  return {status: httpStatus, payload: {ok, status, data, ...(message === undefined ? {} : {message})}};
}
export function physicalSources() {
  const files = {integration: "static/portal/integration.js", i18n: "static/portal/portal-i18n.js"};
  const sources = Object.fromEntries(Object.entries(files).map(([key, file]) =>
    [key, fs.readFileSync(path.join(ROOT, file), "utf8")]));
  return {sources, paths: Object.fromEntries(Object.entries(files).map(([key, file]) => [key, path.join(ROOT, file)])),
    hashes: Object.fromEntries(Object.entries(sources).map(([key, value]) => [key, hash(value)]))};
}
const NAMES = ["api", "handleAction", "audioHubReviewPackBoundaryIsSafe", "audioHubReviewPackResultIsSafe",
  "audioHubReviewPackRequestIsCurrent"];

// Both whole physical bundles execute unchanged except one observation insertion.
// Only browser/HTTP boundaries are doubled; no production function is extracted or replaced.
export function runtime(locale = "vi", source = physicalSources()) {
  const listeners = new Map(), toasts = [], forbidden = [], network = [], focus = [], merges = [], busy = [], raf = [];
  const noop = () => {};
  const deny = kind => () => { forbidden.push(kind); throw Error("Forbidden audio-review QA boundary: " + kind); };
  const storage = name => ({getItem: () => null, setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  let responder = null;
  let state = freeze({path: ROUTE, interfaceLocale: locale,
    session: {authenticated: true, csrfToken: "SYNTHETIC_AUDIO_REVIEW_ONLY"},
    capabilities: {[ACTION]: true, "media-workspace-view": true}, mediaWorkspaceEnabled: true,
    mediaWorkspaceReadState: "ready", mediaCollections: [], mediaAudioAssets: [],
    mediaWorkspaceSummary: {}, mediaWorkspacePolicy: {}, audioHubReviewPack: {previous: "transient"},
    mediaCollectionDetail: {collection: {id: IDS[0], title: "SYNTHETIC COLLECTION",
      state: "active", revision: 7, policy: {status: "clear", marker: null}},
    versions: [], items: [], item_count: 0, item_limit: 250}, bridge: {available: false}});
  const control = {
    attributes: {"data-portal-action": ACTION, "data-portal-route": ROUTE},
    disabled: false, getAttribute(key) { return this.attributes[key] ?? null; },
    setAttribute(key, value) {
      this.attributes[key] = value;
      if (key === "aria-busy") busy.push({value, disabled: this.disabled});
    }
  };
  const status = {focus: options => focus.push({selector: "review-status", options: plain(options)})};
  const region = {appendChild: node => toasts.push(node), querySelectorAll: () => toasts};
  const document = {
    readyState: "loading", visibilityState: "visible", addEventListener: noop,
    querySelector(selector) {
      if (selector === "[data-portal-toast]") return region;
      if (selector === `[data-audio-hub-review-pack-status][data-media-collection-id="${IDS[0]}"]`) return status;
      return null;
    },
    querySelectorAll: selector => selector === "[data-portal-action]" ? [control] : [],
    getElementById: () => null, write: deny("document.write"),
    createElement(tag) {
      assert.equal(tag, "div");
      return {className: "", textContent: "", attributes: {},
        set innerHTML(_) { deny("toast.innerHTML")(); }, set outerHTML(_) { deny("toast.outerHTML")(); },
        insertAdjacentHTML: deny("toast.insertAdjacentHTML"),
        setAttribute(key, value) { this.attributes[key] = value; },
        remove() { const index = toasts.indexOf(this); if (index >= 0) toasts.splice(index, 1); }};
    },
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null},
    body: {classList: {add: noop, remove: noop, toggle: noop}}
  };
  const location = {pathname: ROUTE, search: "", origin: "https://unit.invalid",
    get href() { return this.origin + this.pathname; }, set href(_) { deny("navigation.href")(); },
    assign: deny("navigation.assign"), replace: deny("navigation.replace"), reload: deny("navigation.reload")};
  const window = {document, location, navigator: {language: locale, sendBeacon: deny("sendBeacon")},
    addEventListener: (name, listener) => listeners.set(name, listener), dispatchEvent: deny("dispatchEvent"),
    setTimeout: () => 0, clearTimeout: noop, setInterval: deny("setInterval"), clearInterval: noop,
    requestAnimationFrame: callback => { raf.push(callback); return raf.length; },
    cancelAnimationFrame: deny("cancelAnimationFrame"), matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("localStorage"), sessionStorage: storage("sessionStorage"), crypto: webcrypto,
    history: {pushState: deny("history.pushState"), replaceState: deny("history.replaceState")},
    XMLHttpRequest: deny("XMLHttpRequest"), WebSocket: deny("WebSocket"),
    indexedDB: {open: deny("indexedDB.open"), deleteDatabase: deny("indexedDB.deleteDatabase")}};
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {get: () => state, set: next => {
    state = freeze(next); merges.push(plain(next));
  }});
  const fetch = async (url, options = {}) => {
    const parsed = new URL(url, location.origin), headers = options.headers;
    const entry = freeze({url: parsed.href, path: parsed.pathname, method: options.method || "GET",
      query: Object.fromEntries(parsed.searchParams), credentials: options.credentials, cache: options.cache,
      headers: Object.fromEntries(headers.entries()), body: options.body ? JSON.parse(options.body) : null});
    network.push(entry);
    try {
      assert.equal(parsed.origin, location.origin);
      assert.equal(parsed.pathname, `/api/v1/media-workspace/collections/${IDS[0]}/review-pack`);
      assert.equal(parsed.search, ""); assert.equal(entry.method, "POST");
      assert.equal(options.credentials, "same-origin"); assert.equal(options.cache, "no-store");
      assert.equal(headers.get("Accept"), "application/json"); assert.equal(headers.get("Content-Type"), "application/json");
      assert.equal(headers.get("X-CSRF-Token"), "SYNTHETIC_AUDIO_REVIEW_ONLY");
      assert.match(headers.get("X-Request-ID"), /^web-[a-f0-9]{32}$/);
      assert.deepEqual(entry.body, {expected_revision: 7});
      assert.equal(typeof responder, "function", "Explicit controlled review HTTP responder required");
    } catch (error) { forbidden.push("HTTP_CONTRACT:" + error.message); throw error; }
    const result = await responder(entry);
    return {ok: result.status >= 200 && result.status < 300, status: result.status,
      json: async () => freeze(result.payload)};
  };
  window.fetch = fetch;
  const box = vm.createContext({window, document, location, navigator: window.navigator, fetch,
    URL, URLSearchParams, Headers, FormData, Blob, AbortController, Intl, console, crypto: webcrypto,
    localStorage: window.localStorage, sessionStorage: window.sessionStorage,
    XMLHttpRequest: window.XMLHttpRequest, WebSocket: window.WebSocket,
    setTimeout: window.setTimeout, clearTimeout: noop});
  vm.runInContext(source.sources.i18n, box, {filename: source.paths.i18n, timeout: 10000});
  const i18n = window.TOANAASI18n;
  i18n.setLocale(locale, {emit: false});
  let translator = i18n;
  const integrationWindow = Object.create(window);
  Object.defineProperty(integrationWindow, "TOANAASI18n", {get: () => translator});
  box.window = integrationWindow;
  const anchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(source.sources.integration.split(anchor).length - 1, 1);
  const exposure = "  window.__audioReviewQA=Object.freeze({" + NAMES.join(",")
    + ",epochs:()=>({request:mediaWorkspaceReviewPackRequestEpoch,session:mediaWorkspaceSessionEpoch})});\n";
  const executed = source.sources.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executed, box, {filename: source.paths.integration, timeout: 10000});
  const probe = integrationWindow.__audioReviewQA;
  assert.equal(typeof listeners.get("toanaas:portal-action"), "function");
  assert.deepEqual(network, []); assert.deepEqual(forbidden, []);
  return {
    messages: i18n.messages, source,
    binding: {hashes: source.hashes, executedIntegrationHash: hash(executed), exposureCount: 1,
      exposureBytes: Buffer.byteLength(exposure), physicalIntegrationBytes: Buffer.byteLength(source.sources.integration),
      executedIntegrationBytes: Buffer.byteLength(executed), replacedProductionFunctions: 0},
    respond(fn) { responder = fn; },
    patch(patch) { state = freeze({...state, ...patch}); },
    path(value) { location.pathname = value; state = freeze({...state, path: value}); },
    translation(mode) {
      translator = mode === "missing" ? undefined : mode === "key" ? {t: key => key}
        : mode === "empty" ? {t: () => ""} : mode === "number" ? {t: () => 17} : i18n;
    },
    epochs: () => plain(probe.epochs()),
    call(name, ...args) {
      assert.ok(NAMES.includes(name));
      const before = args.map(value => JSON.stringify(value)); args.forEach(freeze);
      try { return probe[name](...args); }
      finally { assert.deepEqual(args.map(value => JSON.stringify(value)), before); }
    },
    async dispatch(details = {}, action = ACTION) {
      const event = freeze({detail: {action, route: ROUTE, fields: {},
        mediaCollectionId: IDS[0], mediaCollectionRevision: 7, ...details}});
      const before = JSON.stringify(event);
      await listeners.get("toanaas:portal-action")(event);
      assert.equal(JSON.stringify(event), before, "Caller event remains frozen and unchanged");
      return toasts.at(-1)?.textContent;
    },
    flushRAF() { while (raf.length) raf.shift()(0); },
    observe() { return plain({state, network, focus, merges, busy, forbidden, pendingRAF: raf.length,
      control: {disabled: control.disabled, attributes: control.attributes},
      toasts: toasts.map(node => ({text: node.textContent, attributes: node.attributes, className: node.className}))}); }
  };
}
