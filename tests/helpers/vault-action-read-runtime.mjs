import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";

export const DEFAULT_REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze([
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222"
]);
export const HOSTILE_TEXT = 'CUSTOMER <img src=x onerror="alert(1)"> Bot provider media CSRF Facebook TikTok &';
const hash = value => createHash("sha256").update(value).digest("hex");
const clone = value => JSON.parse(JSON.stringify(value));
export const item = (id = IDS[0]) => ({
  id, display_name: HOSTILE_TEXT, original_filename: HOSTILE_TEXT + ".pdf",
  extension: ".pdf", content_type: "application/pdf", state: "active",
  byte_size: 1024, updated_at: "2026-11-20T00:00:00Z"
});
export const lifecycle = () => ({
  state: "active", state_reason: "available", lifecycle_revision: 3,
  created_at: "2026-11-19T00:00:00Z", updated_at: "2026-11-20T00:00:00Z",
  archived_at: "", restore_available: false,
  reference_summary: {total_count: 0, hard_blocker_count: 0, references: []}
});

export function physicalSources(repoRoot = process.env.VAULT07_REPO_ROOT || DEFAULT_REPO_ROOT) {
  const root = path.resolve(repoRoot);
  const paths = {
    integration: path.join(root, "static/portal/integration.js"),
    i18n: path.join(root, "static/portal/portal-i18n.js")
  };
  const sources = Object.fromEntries(Object.entries(paths).map(([key, file]) => [key, fs.readFileSync(file, "utf8")]));
  return {root, paths, sources, hashes: Object.fromEntries(Object.entries(sources).map(([key, value]) => [key, hash(value)]))};
}

// Only browser/HTTP boundaries are controlled. The complete physical dispatcher,
// api(), hydrators, projections, currentness fences and toast renderer run as-is.
export function vaultRuntime(locale = "vi", {selected = false, source = physicalSources()} = {}) {
  const initialListing = {
    filters: {q: "OLD_QUERY", state: "archived"},
    pagination: {limit: 50, offset: 50, returned: 1, has_more: false, next_offset: null, previous_offset: 0}
  };
  let state = {
    path: "/asset-vault", session: {authenticated: true, csrfToken: "SYNTHETIC_ONLY"},
    capabilities: {"asset-vault-refresh": true, "asset-vault-lifecycle-view": true},
    assetVaultEnabled: true, assetVaultReadState: "ready", vaultItems: [item()],
    assetVaultListing: initialListing,
    assetVaultLifecycle: selected
      ? {asset_id: IDS[0], lifecycle: lifecycle(), readState: "ready"}
      : {asset_id: "", lifecycle: null, readState: "idle"},
    pageStates: {"/asset-vault": "ready"}, bridge: {available: false}
  };
  const listeners = new Map(), pending = [], network = [], toasts = [], storageWrites = [], navigations = [];
  const noop = () => {};
  const node = () => ({
    className: "", textContent: "", attributes: {},
    get innerHTML() { return ""; },
    set innerHTML(_) { throw Error("VAULT07 feedback must be plain textContent, never HTML"); },
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
  const storage = name => ({
    getItem: () => null,
    setItem: (...args) => storageWrites.push({name, operation: "setItem", args}),
    removeItem: (...args) => storageWrites.push({name, operation: "removeItem", args})
  });
  const window = {
    document, navigator: {language: locale},
    location: {pathname: "/asset-vault", search: "", origin: "https://unit.invalid",
      href: "https://unit.invalid/asset-vault", assign: value => navigations.push(value)},
    addEventListener: (name, fn) => listeners.set(name, fn), dispatchEvent: noop,
    setTimeout: () => 0, clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("local"), sessionStorage: storage("session"), crypto: webcrypto
  };
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {get: () => state, set: value => { state = value; }});
  const fetch = (url, options = {}) => {
    const parsed = new URL(url, "https://unit.invalid");
    assert.equal(parsed.origin, "https://unit.invalid", "No real network origin");
    const isList = parsed.pathname === "/api/v1/asset-vault";
    const match = /^\/api\/v1\/asset-vault\/([0-9a-f-]+)\/lifecycle$/.exec(parsed.pathname);
    assert.ok(isList || (match && IDS.includes(match[1])), "Only list/selected-lifecycle GET allowed");
    assert.equal(options.method || "GET", "GET", "No product writes");
    assert.equal(options.body, undefined);
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    assert.equal(options.headers.get("Accept"), "application/json");
    assert.equal(options.headers.has("X-CSRF-Token"), false, "Read does not become a mutation");
    assert.ok(options.headers.get("X-Request-ID"));
    if (isList) {
      assert.ok([...parsed.searchParams.keys()].every(key => ["limit", "offset", "q", "state"].includes(key)));
      assert.equal(parsed.searchParams.get("limit"), "50");
      assert.match(parsed.searchParams.get("offset"), /^\d+$/);
    } else assert.equal(parsed.search, "", "Selected lifecycle ID stays in the path, not a query");
    const entry = {path: parsed.pathname, method: "GET", query: Object.fromEntries(parsed.searchParams)};
    network.push(entry);
    let resolve;
    const promise = new Promise(yes => { resolve = yes; });
    pending.push({resolve, entry, kind: isList ? "list" : "lifecycle", settled: false});
    return promise;
  };
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Headers, FormData, Blob,
    AbortController, Intl, console, fetch, crypto: webcrypto,
    setTimeout: window.setTimeout, clearTimeout: noop
  });
  vm.runInContext(source.sources.i18n, sandbox, {filename: source.paths.i18n});
  const normalI18n = window.TOANAASI18n;
  normalI18n.setLocale(locale, {emit: false});
  let integrationI18n = normalI18n;
  const integrationWindow = Object.create(window);
  Object.defineProperty(integrationWindow, "TOANAASI18n", {get: () => integrationI18n});
  sandbox.window = integrationWindow;
  const anchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(source.sources.integration.split(anchor).length - 1, 1, "Unique test-only exposure anchor");
  const exposure = "  window.__vault07Probe={session:()=>{assetVaultSessionEpoch+=1;},listEpoch:()=>{assetVaultListHydrationEpoch+=1;},lifecycleEpoch:()=>{assetVaultLifecycleHydrationEpoch+=1;},readList:(...args)=>hydrateAssetVault(...args),readLifecycle:id=>hydrateAssetVaultLifecycle(id)};\n";
  const executedIntegration = source.sources.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executedIntegration, sandbox, {filename: source.paths.integration});
  assert.equal(network.length, 0, "Initial DOMContentLoaded hydration is suppressed, not replaced");
  const probe = integrationWindow.__vault07Probe;
  const binding = {
    root: source.root, paths: source.paths, hashes: source.hashes,
    executedIntegrationHash: hash(executedIntegration),
    instrumentedBytes: Buffer.byteLength(executedIntegration),
    physicalIntegrationBytes: Buffer.byteLength(source.sources.integration),
    exposureBytes: Buffer.byteLength(exposure)
  };
  return {
    source, binding, pending, network, toasts,
    get state() { return state; },
    run(action = "refresh", fields = {}, detail = {}) {
      const suffix = action === "clear" ? "filter-clear" : action;
      return listeners.get("toanaas:portal-action")({
        detail: {action: "asset-vault-" + suffix, route: "/asset-vault", fields, ...detail}
      });
    },
    settle(index, {failed = false, items = [item(IDS[1])], data} = {}) {
      const row = pending[index];
      assert.ok(row, "Expected controlled GET exists");
      assert.equal(row.settled, false);
      row.settled = true;
      const offset = Number(row.entry.query.offset || 0);
      const hasMore = items.length > 0;
      const defaultData = row.kind === "lifecycle" ? {lifecycle: lifecycle()} : {
        items, has_more: hasMore, next_offset: hasMore ? offset + 50 : null,
        filters: {q: row.entry.query.q || "", state: row.entry.query.state || "active"},
        pagination: {limit: 50, offset, returned: items.length, has_more: hasMore,
          next_offset: hasMore ? offset + 50 : null, previous_offset: offset >= 50 ? offset - 50 : null}
      };
      row.resolve({ok: !failed, status: failed ? 422 : 200, json: async () => ({
        ok: !failed, status: failed ? "error" : "read_only",
        message: failed ? "SYNTHETIC_READ_FAILURE_DO_NOT_DISPLAY" : "",
        data: failed ? {} : (data ?? defaultData)
      })});
    },
    mutate(type, value) {
      if (type === "route") { state = {...state, path: value || "/dashboard"}; window.location.pathname = state.path; }
      else if (type === "session") probe.session();
      else if (type === "listEpoch") probe.listEpoch();
      else if (type === "lifecycleEpoch") probe.lifecycleEpoch();
      else if (type === "logout") state = {...state, session: {authenticated: false}};
      else if (type === "vaultDisabled") state = {...state, assetVaultEnabled: false};
      else if (type === "selection") state = {...state, assetVaultLifecycle: {asset_id: value || IDS[1], lifecycle: null, readState: "idle"}};
      else if (type === "capability") state = {...state, capabilities: {...state.capabilities, "asset-vault-refresh": value}};
      else throw Error("Unknown controlled boundary mutation: " + type);
    },
    readList: (...args) => probe.readList(...args),
    readLifecycle: id => probe.readLifecycle(id),
    setLocale: value => normalI18n.setLocale(value, {emit: false}),
    translation(mode, value = HOSTILE_TEXT) {
      if (mode === "missing") integrationI18n = undefined;
      else if (mode === "empty") integrationI18n = {t: () => ""};
      else if (mode === "hostile") integrationI18n = {
        ...normalI18n, t: key => key.startsWith("vaultFeedback.") ? value : normalI18n.t(key)
      };
      else if (mode === "normal") integrationI18n = normalI18n;
      else throw Error("Unknown translation boundary");
    },
    observe() {
      return clone({state, network, storageWrites, navigations,
        toasts: toasts.map(value => ({text: value.textContent, role: value.attributes.role, className: value.className}))});
    }
  };
}
