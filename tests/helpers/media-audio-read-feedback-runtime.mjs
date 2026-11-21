import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze([
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222",
  "33333333-3333-4333-8333-333333333333"
]);
export const CUSTOMER = 'CUSTOMER Facebook TikTok <img src=x onerror="literal"> & audio';
export const plain = value => JSON.parse(JSON.stringify(value));
export const hash = value => createHash("sha256").update(value).digest("hex");
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
// Mirrors _audio_asset_public's complete metadata-only shape. No asset URL,
// storage key, binary download, provider result or real account is used.
export function asset(id = IDS[1], changes = {}) {
  return freeze({
    id, project_id: IDS[2], display_name: CUSTOMER, original_filename: CUSTOMER + ".wav",
    extension: ".wav", content_type: "audio/wav", byte_size: 44, state: "active",
    created_at: "2026-11-20T08:00:00Z", updated_at: "2026-11-20T09:00:00Z",
    archived_at: null, download_available: true, ...changes
  });
}
export function physicalSources(root = ROOT) {
  const paths = {integration: path.join(root, "static/portal/integration.js"),
    i18n: path.join(root, "static/portal/portal-i18n.js")};
  const sources = Object.fromEntries(Object.entries(paths).map(([key, file]) => [key, fs.readFileSync(file, "utf8")]));
  return {root, paths, sources, hashes: Object.fromEntries(Object.entries(sources).map(([key, value]) => [key, hash(value)]))};
}

// Full physical integration+i18n execution. Only browser/HTTP boundaries are
// controlled; no application function is extracted, replaced or reverse-patched.
export function audioRuntime(locale = "vi", {root = "/media-workspace", source = physicalSources()} = {}) {
  assert.ok(["/media-workspace", "/audio-hub"].includes(root));
  const route = root + "/" + IDS[0];
  let state = {
    path: route, interfaceLocale: locale,
    session: {authenticated: true, csrfToken: "SYNTHETIC_ONLY"},
    capabilities: {"media-workspace-view": true, "media-audio-page": true},
    mediaWorkspaceEnabled: true, mediaWorkspaceReadState: "ready",
    mediaCollections: [], mediaWorkspaceSummary: {}, mediaWorkspacePolicy: {},
    mediaCollectionDetail: freeze({
      collection: {id: IDS[0], title: CUSTOMER, state: "active", revision: 7},
      versions: [{revision: 7, title: CUSTOMER}], items: [], item_count: 0, item_limit: 250
    }),
    mediaAudioAssets: freeze([asset(IDS[2])]),
    mediaAudioAssetFilter: freeze({q: "OLD_AUDIO"}),
    mediaAudioAssetListing: freeze({filters: {q: "OLD_AUDIO"},
      pagination: {limit: 50, offset: 50, returned: 1, has_more: true, next_offset: 100, previous_offset: 0}}),
    pageStates: freeze({[route]: "read_only"}), bridge: {available: false}
  };
  const listeners = new Map(), pending = [], network = [], toasts = [], forbidden = [];
  const noop = () => {};
  const deny = kind => () => {
    forbidden.push(kind);
    const error = new Error("Forbidden audio QA boundary: " + kind);
    error.status = 422; // Boundary defects may not disappear into api retry.
    throw error;
  };
  const storage = name => ({getItem: () => null, setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  const node = () => ({
    className: "", textContent: "", attributes: {},
    get innerHTML() { return ""; },
    set innerHTML(_) { deny("toast.innerHTML")(); },
    set outerHTML(_) { deny("toast.outerHTML")(); },
    insertAdjacentHTML: deny("toast.insertAdjacentHTML"),
    setAttribute(key, value) { this.attributes[key] = value; },
    remove() { const at = toasts.indexOf(this); if (at >= 0) toasts.splice(at, 1); }
  });
  const region = {appendChild: value => toasts.push(value), querySelectorAll: () => toasts};
  const document = {
    readyState: "loading", visibilityState: "visible", addEventListener: noop,
    createElement: tag => { assert.equal(tag, "div"); return node(); },
    querySelector: selector => selector === "[data-portal-toast]" ? region : null,
    querySelectorAll: () => [], write: deny("document.write"),
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null},
    body: {classList: {add: noop, remove: noop, toggle: noop}}
  };
  const location = {
    pathname: route, search: "", origin: "https://unit.invalid",
    get href() { return "https://unit.invalid" + this.pathname; },
    set href(_) { deny("navigation.href")(); },
    assign: deny("navigation.assign"), replace: deny("navigation.replace"), reload: deny("navigation.reload")
  };
  const window = {
    document, location, navigator: {language: locale, sendBeacon: deny("sendBeacon")},
    addEventListener: (name, fn) => listeners.set(name, fn), dispatchEvent: deny("dispatchEvent"),
    setTimeout: () => 0, clearTimeout: noop, setInterval: deny("setInterval"), clearInterval: noop,
    matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("local"), sessionStorage: storage("session"), crypto: webcrypto,
    history: {pushState: deny("history.pushState"), replaceState: deny("history.replaceState")},
    XMLHttpRequest: deny("XMLHttpRequest"), WebSocket: deny("WebSocket"),
    indexedDB: {open: deny("indexedDB.open"), deleteDatabase: deny("indexedDB.deleteDatabase")}
  };
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {get: () => state, set: value => { state = value; }});
  const fetch = (url, options = {}) => {
    let parsed;
    try {
      parsed = new URL(url, location.origin);
      assert.equal(parsed.origin, location.origin, "No real network origin");
      assert.equal(parsed.pathname, "/api/v1/media-workspace/audio-assets", "Exact audio GET boundary only");
      assert.equal(options.method || "GET", "GET", "No product writes");
      assert.equal(options.body, undefined);
      assert.equal(options.credentials, "same-origin");
      assert.equal(options.cache, "no-store");
      assert.equal(options.headers.get("Accept"), "application/json");
      assert.equal(options.headers.has("X-CSRF-Token"), false);
      assert.match(options.headers.get("X-Request-ID"), /^web-[0-9a-f]{32}$/);
      assert.ok([...parsed.searchParams.keys()].every(key => ["limit", "offset", "q"].includes(key)));
      assert.equal(parsed.searchParams.get("limit"), "50");
      assert.match(parsed.searchParams.get("offset"), /^\d+$/);
    } catch (error) {
      forbidden.push("fetch: " + error.message);
      error.status = 422;
      return Promise.reject(error);
    }
    const entry = {path: parsed.pathname, method: "GET", query: Object.fromEntries(parsed.searchParams)};
    network.push(entry);
    let resolve;
    const work = new Promise(yes => { resolve = yes; });
    pending.push({resolve, entry, settled: false});
    return work;
  };
  window.fetch = fetch;
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Headers, FormData, Blob,
    AbortController, Intl, console, fetch, crypto: webcrypto, location,
    localStorage: window.localStorage, sessionStorage: window.sessionStorage,
    XMLHttpRequest: window.XMLHttpRequest, WebSocket: window.WebSocket,
    setTimeout: window.setTimeout, clearTimeout: noop
  });
  vm.runInContext(source.sources.i18n, sandbox, {filename: source.paths.i18n, timeout: 10000});
  const normalI18n = window.TOANAASI18n;
  normalI18n.setLocale(locale, {emit: false});
  let translator = normalI18n;
  const integrationWindow = Object.create(window);
  Object.defineProperty(integrationWindow, "TOANAASI18n", {get: () => translator});
  sandbox.window = integrationWindow;
  const anchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(source.sources.integration.split(anchor).length - 1, 1, "Unique physical exposure anchor");
  const exposure = "  window.__mediaAudioReadFeedbackProbe=Object.freeze({session:()=>{mediaWorkspaceSessionEpoch+=1;},audioEpoch:()=>{mediaWorkspaceAudioHydrationEpoch+=1;},listEpoch:()=>{mediaWorkspaceListHydrationEpoch+=1;},detailEpoch:()=>{mediaWorkspaceDetailHydrationEpoch+=1;},readAudio:(...args)=>hydrateMediaAudioAssets(...args)});\n";
  const executed = source.sources.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executed, sandbox, {filename: source.paths.integration, timeout: 10000});
  assert.equal(network.length, 0, "DOMContentLoaded not fired; original startup is not stubbed");
  assert.deepEqual(forbidden, [], "No initialization side effects");
  const probe = integrationWindow.__mediaAudioReadFeedbackProbe;
  return {
    source, pending, network,
    binding: {root: source.root, paths: source.paths, hashes: source.hashes,
      executedIntegrationHash: hash(executed), exposureCount: 1, replacedProductionFunctions: 0,
      physicalIntegrationBytes: Buffer.byteLength(source.sources.integration),
      executedIntegrationBytes: Buffer.byteLength(executed), exposureBytes: Buffer.byteLength(exposure)},
    get state() { return state; },
    start(action = "filter", fields = {}) {
      assert.ok(["filter", "clear", "page"].includes(action));
      const name = action === "clear" ? "filter-clear" : action;
      freeze(fields);
      const before = JSON.stringify(fields), from = pending.length;
      const work = listeners.get("toanaas:portal-action")({
        detail: freeze({action: "media-audio-" + name, route: state.path, fields})
      });
      return {indices: pending.slice(from).map((_, index) => from + index),
        work: Promise.resolve(work).finally(() => assert.equal(JSON.stringify(fields), before, "Frozen caller fields remain exact"))};
    },
    readAudio: (...args) => {
      args.forEach(freeze);
      return probe.readAudio(...args);
    },
    settle(index, {failed = false, items = [asset()], data} = {}) {
      const row = pending[index];
      assert.ok(row, "Controlled audio GET exists");
      assert.equal(row.settled, false);
      row.settled = true;
      const offset = Number(row.entry.query.offset), hasMore = items.length > 0;
      const envelope = freeze({
        ok: !failed, status: failed ? "error" : "read_only",
        message: failed ? "SYNTHETIC_SERVER_FAILURE_DO_NOT_TRANSLATE_OR_DISPLAY" : "SYNTHETIC_SERVER_SUCCESS_NOT_ACTION_FEEDBACK",
        data: failed ? {} : (data ?? {
          items, has_more: hasMore, next_offset: hasMore ? offset + 50 : null,
          filters: {q: row.entry.query.q || ""},
          pagination: {limit: 50, offset, returned: items.length}, source: "asset_vault_owner_scoped"
        })
      });
      row.resolve({ok: !failed, status: failed ? 422 : 200, json: async () => envelope});
    },
    mutate(type, value) {
      if (["session", "audioEpoch", "listEpoch", "detailEpoch"].includes(type)) probe[type]();
      else if (type === "route") {
        state = {...state, path: value || "/dashboard"};
        location.pathname = state.path;
      } else if (type === "logout") state = {...state, session: {authenticated: false}};
      else if (type === "disabled") state = {...state, mediaWorkspaceEnabled: false};
      else if (type === "filterCapability") state = {...state, capabilities: {...state.capabilities, "media-workspace-view": value}};
      else if (type === "pageCapability") state = {...state, capabilities: {...state.capabilities, "media-audio-page": value}};
      else if (type === "collectionReadState") state = {...state, mediaWorkspaceReadState: value};
      else throw Error("Unknown controlled audio boundary: " + type);
    },
    translation(mode) {
      if (mode === "missing") translator = undefined;
      else if (mode === "empty") translator = {t: () => ""};
      else if (mode === "hostile") translator = {...normalI18n,
        t: key => key.startsWith("mediaReadFeedback.") ? CUSTOMER : normalI18n.t(key)};
      else if (mode === "normal") translator = normalI18n;
      else throw Error("Unknown translator boundary");
    },
    observe() {
      return plain({state, network, forbidden, toasts: toasts.map(value => ({
        text: value.textContent, role: value.attributes.role, className: value.className
      }))});
    }
  };
}
