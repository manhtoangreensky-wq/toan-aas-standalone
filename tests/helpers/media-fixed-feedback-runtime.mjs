import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";
import {fileURLToPath} from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze(["11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"]);
export const CUSTOMER = 'Facebook TikTok CUSTOMER <img src=x onerror="literal"> & audio';
export const plain = value => JSON.parse(JSON.stringify(value));
export const hash = raw => createHash("sha256").update(raw).digest("hex");
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
export function physicalSources(root = ROOT) {
  const files = {integration: "static/portal/integration.js", i18n: "static/portal/portal-i18n.js"};
  const sources = Object.fromEntries(Object.entries(files).map(([key, file]) => [key, fs.readFileSync(path.join(root, file), "utf8")]));
  return {root, sources, paths: Object.fromEntries(Object.entries(files).map(([key, file]) => [key, path.join(root, file)])),
    hashes: Object.fromEntries(Object.entries(sources).map(([key, raw]) => [key, hash(raw)]))};
}
export function collectionFields(changes = {}) {
  return {title: CUSTOMER, description: CUSTOMER, creative_brief: CUSTOMER, prompt_mode: "background",
    use_context: "Customer context", rights_note: "Owned rights", tags: "Keep,keep,TikTok", project_id: IDS[2], ...changes};
}
export function itemFields(changes = {}) {
  return {asset_id: IDS[1], role: "music", title_override: CUSTOMER, attribution: CUSTOMER,
    license_note: "Owned rights", tags: "Keep,keep,TikTok", favorite: true, user_declared_duration_seconds: "90", ...changes};
}
const NAMES = Object.freeze(["mediaWorkspaceSafetyError", "mediaWorkspaceLine", "mediaWorkspaceContent",
  "mediaWorkspaceTags", "mediaWorkspaceFilterPayload", "mediaAudioAssetFilterPayload", "mediaCollectionPayload",
  "mediaItemPayload", "musicSfxEditorialErrorText", "mediaWorkspaceListOffset", "handleAction"]);

// Execute both whole physical bundles. Browser/network boundaries are controlled;
// no production function is extracted, replaced or reverse-projected.
export function runtime(locale = "vi", {root = "/media-workspace", source = physicalSources()} = {}) {
  assert.ok(["/media-workspace", "/audio-hub"].includes(root));
  const route = root + "/" + IDS[0], listeners = new Map(), toasts = [], forbidden = [], network = [], navigation = [], focus = [];
  let responder = null;
  const noop = () => {};
  const deny = kind => () => {
    forbidden.push(kind);
    throw Object.assign(new Error("Forbidden MFF QA boundary: " + kind), {status: 422});
  };
  const storage = name => ({getItem: () => null, setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  let state = {
    path: route, interfaceLocale: locale, session: {authenticated: true, csrfToken: "SYNTHETIC_ONLY"},
    capabilities: {"media-workspace-view": true, "media-audio-page": true, "audio-asset-operation-view": false},
    mediaWorkspaceEnabled: true, mediaWorkspaceReadState: "ready", mediaCollections: [],
    mediaWorkspaceSummary: {}, mediaWorkspacePolicy: {}, mediaAudioAssets: [],
    mediaCollectionDetail: {collection: {id: IDS[0], title: CUSTOMER, state: "active", revision: 7},
      versions: [], items: [], item_count: 0, item_limit: 250},
    bridge: {available: false}
  };
  const region = {appendChild: node => toasts.push(node), querySelectorAll: () => toasts};
  const createNode = () => ({
    className: "", textContent: "", attributes: {},
    get innerHTML() { return ""; }, set innerHTML(_) { deny("toast.innerHTML")(); },
    set outerHTML(_) { deny("toast.outerHTML")(); }, insertAdjacentHTML: deny("toast.insertAdjacentHTML"),
    setAttribute(key, value) { this.attributes[key] = value; },
    remove() { const index = toasts.indexOf(this); if (index >= 0) toasts.splice(index, 1); }
  });
  const document = {
    readyState: "loading", visibilityState: "visible", addEventListener: noop,
    createElement: tag => { assert.equal(tag, "div"); return createNode(); },
    querySelector: selector => selector === "[data-portal-toast]" ? region : null,
    querySelectorAll: () => [], getElementById: id => responder && id === "audio-asset-source"
      ? {disabled: false, focus: options => focus.push({id, options})} : null, write: deny("document.write"),
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null},
    body: {classList: {add: noop, remove: noop, toggle: noop}}
  };
  const location = {pathname: route, search: "", origin: "https://unit.invalid",
    get href() { return this.origin + this.pathname; }, set href(_) { deny("navigation.href")(); },
    assign: value => { if (!responder) return deny("navigation.assign")(); navigation.push({kind: "assign", value}); },
    replace: deny("navigation.replace"), reload: deny("navigation.reload")};
  const window = {
    document, location, navigator: {language: locale, sendBeacon: deny("sendBeacon")},
    addEventListener: (name, fn) => listeners.set(name, fn), dispatchEvent: deny("dispatchEvent"),
    setTimeout: () => 0, clearTimeout: noop, setInterval: deny("setInterval"), clearInterval: noop,
    matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("local"), sessionStorage: storage("session"), crypto: webcrypto,
    history: {pushState: (data, title, value) => {
      if (!responder) return deny("history.pushState")();
      assert.equal(value, "/audio/assets"); navigation.push({kind: "pushState", value});
      location.pathname = value;
    }, replaceState: deny("history.replaceState")},
    XMLHttpRequest: deny("XMLHttpRequest"), WebSocket: deny("WebSocket"),
    indexedDB: {open: deny("indexedDB.open"), deleteDatabase: deny("indexedDB.deleteDatabase")}
  };
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {get: () => state, set: value => { state = value; }});
  const fetch = (url, options = {}) => {
    const parsed = new URL(url, location.origin), method = options.method || "GET";
    const entry = {path: parsed.pathname.replace(/^\/api\/v1/, ""), method,
      query: Object.fromEntries(parsed.searchParams), body: options.body ? JSON.parse(options.body) : null};
    network.push(entry);
    if (!responder) return Promise.reject(Object.assign(new Error("No HTTP is permitted in the local-validation slice."), {status: 422}));
    assert.equal(parsed.origin, location.origin); assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    const metadata = /^\/media-workspace\/(?:summary|policy|events|audio-assets|collections(?:\/[a-f0-9-]{36}(?:\/(?:archive|restore|duplicate|restore-version|compose|items(?:\/[a-f0-9-]{36}(?:\/detach)?)?))?)?)$/;
    assert.ok(metadata.test(entry.path) || (method === "GET" && ["/asset-vault", "/audio-asset-operations"].includes(entry.path)));
    assert.ok(["GET", "POST", "PATCH"].includes(method));
    assert.equal(options.headers.get("Accept"), "application/json");
    assert.match(options.headers.get("X-Request-ID"), /^web-[0-9a-f]{32}$/);
    assert.equal(options.headers.has("X-CSRF-Token"), method !== "GET");
    return Promise.resolve(responder(freeze(entry))).then(result => ({
      ok: result.ok !== false, status: result.status ?? 200, json: async () => freeze(result.payload)
    }));
  };
  window.fetch = fetch;
  const box = vm.createContext({window, document, navigator: window.navigator, URL, URLSearchParams,
    Headers, FormData, Blob, AbortController, Intl, console, fetch, crypto: webcrypto, location,
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
  const exposure = "  window.__mediaFixedFeedbackProbe=Object.freeze({" + NAMES.join(",")
    + ',errorText:typeof mediaWorkspaceErrorText==="function"?mediaWorkspaceErrorText:null,'
    + 'feedbackText:typeof mediaWorkspaceFeedbackText==="function"?mediaWorkspaceFeedbackText:null});\n';
  const executed = source.sources.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executed, box, {filename: source.paths.integration, timeout: 10000});
  const probe = integrationWindow.__mediaFixedFeedbackProbe;
  assert.equal(typeof listeners.get("toanaas:portal-action"), "function");
  assert.deepEqual(network, []); assert.deepEqual(forbidden, []);
  return {
    source, messages: i18n.messages, probe,
    binding: {sourceHashes: source.hashes, executedIntegrationHash: hash(executed), exposureCount: 1,
      replacedProductionFunctions: 0, exposureBytes: Buffer.byteLength(exposure),
      physicalIntegrationBytes: Buffer.byteLength(source.sources.integration), executedIntegrationBytes: Buffer.byteLength(executed)},
    call(name, ...args) {
      assert.ok(NAMES.includes(name));
      const before = args.map(value => JSON.stringify(value)); args.forEach(freeze);
      try { return probe[name](...args); }
      finally { assert.deepEqual(args.map(value => JSON.stringify(value)), before); }
    },
    async dispatch(action, fields = {}, details = {}) {
      const event = freeze({detail: {action, route, fields, mediaCollectionId: IDS[0],
        mediaCollectionRevision: 7, mediaItemId: IDS[2], ...details}});
      const before = JSON.stringify(event);
      await listeners.get("toanaas:portal-action")(event);
      assert.equal(JSON.stringify(event), before);
      return toasts.at(-1)?.textContent;
    },
    errorText(error) { assert.equal(typeof probe.errorText, "function", "REAL_LOCAL_PRESENTATION_HELPER_MISSING"); return probe.errorText(error); },
    feedback(key, fallback) { assert.equal(typeof probe.feedbackText, "function", "REAL_FIXED_FEEDBACK_HELPER_MISSING"); return probe.feedbackText(key, fallback); },
    translation(mode) {
      translator = mode === "missing" ? undefined : mode === "empty" ? {t: () => ""}
        : mode === "key" ? {t: key => key} : mode === "number" ? {t: () => 0} : i18n;
    },
    setCapability(name, value) { state = {...state, capabilities: {...state.capabilities, [name]: value}}; },
    controlledMetadataHTTP(fn, seed = {}) { assert.equal(typeof fn, "function"); responder = fn; state = {...state, ...freeze(seed)}; },
    observe() { return plain({state, network, navigation, focus, forbidden, toasts: toasts.map(node => ({text: node.textContent, attributes: node.attributes}))}); }
  };
}
