import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze([
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222"
]);
export const CUSTOMER = 'CUSTOMER Facebook TikTok <img src=x onerror="literal"> & audio';
export const plain = value => JSON.parse(JSON.stringify(value));
export const hash = value => createHash("sha256").update(value).digest("hex");
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
export const collection = (id = IDS[0]) => freeze({
  id, account_id: IDS[1], title: CUSTOMER, description: CUSTOMER, creative_brief: CUSTOMER,
  brief_excerpt: CUSTOMER, description_excerpt: CUSTOMER, prompt_mode: "background",
  use_context: CUSTOMER, tags: ["customer tag", "TikTok"], project_id: null,
  rights_note: CUSTOMER, policy: {status: "clear", marker: null}, state: "active",
  revision: 7, created_at: "2026-11-20T08:00:00Z", updated_at: "2026-11-20T09:00:00Z",
  archived_at: null, execution: "authoring_only"
});
const pagination = (offset, returned = 0) => ({
  limit: 50, offset, returned, has_more: returned > 0,
  next_offset: returned > 0 ? offset + 50 : null, previous_offset: offset >= 50 ? offset - 50 : null
});

export function physicalSources(root = ROOT) {
  const paths = {
    integration: path.join(root, "static/portal/integration.js"),
    i18n: path.join(root, "static/portal/portal-i18n.js")
  };
  const sources = Object.fromEntries(Object.entries(paths).map(([key, file]) => [key, fs.readFileSync(file, "utf8")]));
  return {root, paths, sources, hashes: Object.fromEntries(Object.entries(sources).map(([key, value]) => [key, hash(value)]))};
}

// Only HTTP/browser boundaries are controlled. Complete physical bundles execute;
// dispatcher, api, hydrators, projections, currentness and toast remain unchanged.
export function mediaRuntime(locale = "vi", {root = "/media-workspace", detail = false, source = physicalSources()} = {}) {
  assert.ok(["/media-workspace", "/audio-hub"].includes(root));
  const route = root + (detail ? "/" + IDS[0] : "");
  let state = {
    path: route, interfaceLocale: locale,
    session: {authenticated: true, csrfToken: "SYNTHETIC_ONLY"},
    capabilities: {"media-workspace-page": true, "media-workspace-view": true,
      "media-workspace-refresh": true, "audio-change-request-view": true},
    mediaWorkspaceEnabled: true, mediaWorkspaceReadState: "ready",
    mediaCollections: freeze([collection()]),
    mediaWorkspaceSummary: {}, mediaWorkspacePolicy: {}, mediaWorkspaceEvents: [],
    mediaWorkspaceListing: freeze({
      filters: {q: "OLD_QUERY", tag: "OLD_TAG", prompt_mode: "background", state: "archived"},
      pagination: pagination(50, 1)
    }),
    mediaCollectionDetail: detail ? freeze({
      collection: collection(), versions: [{revision: 7, title: CUSTOMER}],
      items: [], item_count: 0, item_limit: 250
    }) : {},
    mediaAudioAssets: [], mediaAudioAssetFilter: {q: "OLD_AUDIO"},
    mediaAudioAssetListing: freeze({filters: {q: "OLD_AUDIO"}, pagination: pagination(50)}),
    audioChangeRequestsEnabled: true, audioChangeRequests: [], audioChangeRequestReadState: "ready",
    pageStates: {[route]: detail ? "read_only" : "ready"}, bridge: {available: false}
  };
  const listeners = new Map(), pending = [], network = [], toasts = [], forbidden = [];
  const noop = () => {};
  const deny = kind => () => {
    forbidden.push(kind);
    const error = new Error("Forbidden test boundary: " + kind);
    error.status = 422; // Do not let the real retry loop hide a boundary violation.
    throw error;
  };
  const storage = name => ({getItem: () => null, setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  const node = () => ({
    className: "", textContent: "", attributes: {},
    get innerHTML() { return ""; },
    set innerHTML(_) { deny("toast.innerHTML")(); },
    setAttribute(key, value) { this.attributes[key] = value; },
    getAttribute(key) { return this.attributes[key] ?? null; },
    remove() { const at = toasts.indexOf(this); if (at >= 0) toasts.splice(at, 1); }
  });
  const region = {appendChild: value => toasts.push(value), querySelectorAll: () => toasts};
  const document = {
    readyState: "loading", visibilityState: "visible", addEventListener: noop,
    createElement: tag => { assert.equal(tag, "div"); return node(); },
    querySelector: selector => selector === "[data-portal-toast]" ? region : null,
    querySelectorAll: () => [],
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null},
    body: {classList: {add: noop, remove: noop, toggle: noop}}
  };
  const location = {pathname: route, search: "", origin: "https://unit.invalid",
    href: "https://unit.invalid" + route, assign: deny("navigation.assign"),
    replace: deny("navigation.replace"), reload: deny("navigation.reload")};
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
    let parsed, kind;
    try {
      parsed = new URL(url, location.origin);
      assert.equal(parsed.origin, location.origin, "No real network origin");
      const p = parsed.pathname;
      kind = p === "/api/v1/media-workspace/summary" ? "summary"
        : p === "/api/v1/media-workspace/policy" ? "policy"
        : p === "/api/v1/media-workspace/collections" ? "list"
        : p === "/api/v1/media-workspace/events" ? "events"
        : p === `/api/v1/media-workspace/collections/${IDS[0]}` ? "detail"
        : p === "/api/v1/media-workspace/audio-assets" ? "assets"
        : p === "/api/v1/audio-change-requests/drafts" ? "secondary" : "";
      assert.ok(kind, "Only exact media read allowlist");
      assert.equal(options.method || "GET", "GET", "No product writes");
      assert.equal(options.body, undefined);
      assert.equal(options.credentials, "same-origin");
      assert.equal(options.cache, "no-store");
      assert.equal(options.headers.get("Accept"), "application/json");
      assert.equal(options.headers.has("X-CSRF-Token"), false);
      assert.ok(options.headers.get("X-Request-ID"));
      const keys = [...parsed.searchParams.keys()];
      const allowed = kind === "list" ? ["state", "limit", "offset", "q", "tag", "prompt_mode"]
        : kind === "assets" ? ["limit", "offset", "q"]
        : kind === "events" ? ["limit"]
        : kind === "secondary" ? ["collection_id", "limit"] : [];
      assert.ok(keys.every(key => allowed.includes(key)), "Read query allowlist");
      if (["list", "assets", "events"].includes(kind)) assert.equal(parsed.searchParams.get("limit"), "50");
      if (["list", "assets"].includes(kind)) assert.match(parsed.searchParams.get("offset"), /^\d+$/);
      if (kind === "secondary") {
        assert.equal(parsed.searchParams.get("collection_id"), IDS[0]);
        assert.equal(parsed.searchParams.get("limit"), "24");
      }
    } catch (error) {
      forbidden.push("fetch: " + error.message);
      error.status = 422;
      return Promise.reject(error);
    }
    const entry = {path: parsed.pathname, method: "GET", query: Object.fromEntries(parsed.searchParams)};
    network.push(entry);
    let resolve;
    const promise = new Promise(yes => { resolve = yes; });
    pending.push({resolve, entry, kind, settled: false});
    return promise;
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
  assert.equal(source.sources.integration.split(anchor).length - 1, 1, "Unique test-only exposure anchor");
  const exposure = "  window.__mediaReadFeedbackProbe=Object.freeze({session:()=>{mediaWorkspaceSessionEpoch+=1;},listEpoch:()=>{mediaWorkspaceListHydrationEpoch+=1;},detailEpoch:()=>{mediaWorkspaceDetailHydrationEpoch+=1;},readList:(...args)=>hydrateMediaWorkspace(...args),readDetail:()=>hydrateMediaCollection('" + IDS[0] + "',currentPortalPath())});\n";
  const executed = source.sources.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executed, sandbox, {filename: source.paths.integration, timeout: 10000});
  assert.equal(network.length, 0, "DOMContentLoaded hydration is suppressed, not replaced");
  assert.deepEqual(forbidden, [], "No initialization side effects");
  const probe = integrationWindow.__mediaReadFeedbackProbe;
  function settle(index, {failed = false, empty = false, malformed = false, data} = {}) {
    const row = pending[index];
    assert.ok(row, "Expected controlled GET exists");
    assert.equal(row.settled, false);
    row.settled = true;
    const offset = Number(row.entry.query.offset || 0);
    const rows = empty ? [] : [collection(IDS[1])];
    const defaults = {
      summary: {collections: {total: rows.length, active: rows.length, archived: 0},
        items: {total: 0, favorites: 0}, execution: {authoring: "ready", generation: "guarded"}},
      policy: {status: "clear", policy: [], guarded_capabilities: []},
      list: {items: rows, has_more: !empty, next_offset: empty ? null : offset + 50},
      events: {items: []},
      detail: malformed ? {collection: collection(IDS[1]), versions: [], items: []}
        : {collection: collection(), versions: [{revision: 7, title: CUSTOMER}], items: [], item_count: 0, item_limit: 250},
      assets: {items: [], has_more: false, next_offset: null},
      secondary: {requests: []}
    };
    const envelope = freeze({
      ok: !failed, status: failed ? "error" : "read_only",
      message: failed ? "SYNTHETIC_RAW_FAILURE_DO_NOT_DISPLAY" : "",
      data: failed ? {} : (data ?? defaults[row.kind])
    });
    row.resolve({ok: !failed, status: failed ? 422 : 200, json: async () => envelope});
  }
  return {
    source, pending, network,
    binding: {root: source.root, paths: source.paths, hashes: source.hashes,
      executedIntegrationHash: hash(executed), exposureCount: 1, replacedProductionFunctions: 0,
      instrumentedBytes: Buffer.byteLength(executed), physicalIntegrationBytes: Buffer.byteLength(source.sources.integration),
      exposureBytes: Buffer.byteLength(exposure)},
    get state() { return state; },
    start(action = "listrefresh", fields = {}) {
      const names = {filter: "filter", clear: "filter-clear", page: "page",
        listrefresh: "refresh", detailrefresh: "refresh"};
      assert.ok(Object.hasOwn(names, action));
      freeze(fields);
      const before = JSON.stringify(fields), from = pending.length;
      const work = listeners.get("toanaas:portal-action")({
        detail: freeze({action: "media-workspace-" + names[action], route: state.path, fields})
      });
      return {action, indices: pending.slice(from).map((_, at) => from + at),
        work: Promise.resolve(work).finally(() => assert.equal(JSON.stringify(fields), before, "Caller fields unchanged"))};
    },
    settle,
    settlePrimary(job, options = {}) {
      for (const index of job.indices) {
        const kind = pending[index].kind;
        settle(index, {...options, failed: options.failed === true && ["list", "detail"].includes(kind)});
      }
    },
    mutate(type, value) {
      if (type === "route") { state = {...state, path: value || "/dashboard"}; location.pathname = state.path; }
      else if (["session", "listEpoch", "detailEpoch"].includes(type)) probe[type]();
      else if (type === "logout") state = {...state, session: {authenticated: false}};
      else if (type === "disabled") state = {...state, mediaWorkspaceEnabled: false};
      else if (type === "capability") state = {...state, capabilities: {...state.capabilities, "media-workspace-page": value}};
      else throw Error("Unknown controlled boundary: " + type);
    },
    readList: (...args) => probe.readList(...args),
    readDetail: () => probe.readDetail(),
    translation(mode) {
      if (mode === "missing") translator = undefined;
      else if (mode === "empty") translator = {t: () => ""};
      else if (mode === "hostile") translator = {
        ...normalI18n, t: key => key.startsWith("mediaReadFeedback.") ? CUSTOMER : normalI18n.t(key)
      };
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
