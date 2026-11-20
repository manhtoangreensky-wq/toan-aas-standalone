import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import vm from "node:vm";
import {createHash, webcrypto} from "node:crypto";
import {File} from "node:buffer";

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const ASSET_ID = "11111111-1111-4111-8111-111111111111";
export const PROJECT_ID = "22222222-2222-4222-8222-222222222222";
export const CSRF = "SYNTHETIC_UNIT_ONLY_CSRF";
export const HOSTILE = 'CUSTOMER <img src=x onerror="alert(1)"> & Bot provider media CSRF';
export const PNG_BYTES = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4ioAAAAASUVORK5CYII=", "base64");
export const ACTION = Object.freeze({upload: "asset-vault-upload", archive: "asset-vault-archive", restore: "asset-vault-lifecycle-restore"});
const clone = value => JSON.parse(JSON.stringify(value));
const hash = value => createHash("sha256").update(value).digest("hex");

export function syntheticFile() {
  return new File([PNG_BYTES], "SYNTHETIC.png", {type: "image/png", lastModified: 1795132800000});
}
export function publicAsset(state = "active") {
  return {
    id: ASSET_ID, project_id: PROJECT_ID, display_name: "SYNTHETIC DISPLAY",
    original_filename: "SYNTHETIC.png", extension: ".png", content_type: "image/png",
    byte_size: PNG_BYTES.length, state, created_at: "2026-11-19T00:00:00Z",
    updated_at: "2026-11-20T00:00:00Z",
    archived_at: state === "archived" ? "2026-11-20T00:00:00Z" : null
  };
}
export function publicLifecycle(state = "active", revision = 7) {
  return {
    state, state_reason: state === "archived" ? "owner_archived" : "available",
    lifecycle_revision: revision, created_at: "2026-11-19T00:00:00Z",
    updated_at: "2026-11-20T00:00:00Z",
    archived_at: state === "archived" ? "2026-11-20T00:00:00Z" : null,
    restore_available: state === "archived",
    reference_summary: {total_count: 3, hard_blocker_count: 1, references: [
      {reason: "support_evidence_retention", count: 1, hard_blocker: true},
      {reason: "media_library_reference", count: 2, hard_blocker: false}
    ]}
  };
}
export function writeSources(repoRoot = process.env.VAULT07_REPO_ROOT || REPO_ROOT) {
  const root = path.resolve(repoRoot);
  const paths = {integration: path.join(root, "static/portal/integration.js"), i18n: path.join(root, "static/portal/portal-i18n.js")};
  const raw = Object.fromEntries(Object.entries(paths).map(([key, file]) => [key, fs.readFileSync(file, "utf8")]));
  return {root, paths, raw, hashes: Object.fromEntries(Object.entries(raw).map(([key, text]) => [key, hash(text)]))};
}

// Complete physical application code executes. Only browser/HTTP boundaries
// are controlled; the single exposure reads submission state without changing it.
export function writeRuntime(locale = "vi", {operation = "upload", source = writeSources()} = {}) {
  assert.ok(Object.hasOwn(ACTION, operation));
  const beforeState = operation === "restore" ? "archived" : "active";
  let state = {
    path: "/asset-vault", session: {authenticated: true, csrfToken: CSRF},
    capabilities: {"asset-vault-refresh": true, "asset-vault-archive": true, "asset-vault-restore": true, "asset-vault-lifecycle-view": true},
    assetVaultEnabled: true, assetVaultReadState: "ready", vaultItems: [publicAsset(beforeState)],
    assetVaultListing: {filters: {q: "SYNTHETIC_QUERY", state: "all"},
      pagination: {limit: 50, offset: 50, returned: 1, has_more: false, next_offset: null, previous_offset: 0}},
    assetVaultLifecycle: operation === "upload" ? {asset_id: "", lifecycle: null, readState: "idle"}
      : {asset_id: ASSET_ID, lifecycle: publicLifecycle(beforeState, 2), readState: "ready"},
    pageStates: {"/asset-vault": "ready"}, bridge: {available: false}
  };
  const file = syntheticFile(), listeners = new Map(), pending = [], network = [], toasts = [];
  const storageWrites = [], navigations = [], stateHistory = [], busyEvents = [];
  const noop = () => {};
  const control = action => ({
    disabled: false, attributes: {"data-portal-action": action, "data-portal-route": "/asset-vault", "aria-busy": "false"},
    getAttribute(key) { return this.attributes[key] ?? null; },
    setAttribute(key, value) { this.attributes[key] = value; if (key === "aria-busy") busyEvents.push({action, value}); }
  });
  const buttons = Object.fromEntries(Object.values(ACTION).map(action => [action, control(action)]));
  const submits = Object.fromEntries(Object.values(ACTION).map(action => [action, control(action)]));
  const forms = Object.values(ACTION).map(action => ({
    getAttribute: key => key === "data-portal-action" ? action : key === "data-portal-route" ? "/asset-vault" : null,
    querySelector: selector => selector === 'button[type="submit"]' ? submits[action] : null
  }));
  const toastNode = () => ({
    className: "", textContent: "", attributes: {},
    get innerHTML() { return ""; },
    set innerHTML(_) { throw Error("Write feedback must stay plain textContent"); },
    getAttribute(key) { return this.attributes[key] ?? null; },
    setAttribute(key, value) { this.attributes[key] = value; },
    remove() { const index = toasts.indexOf(this); if (index >= 0) toasts.splice(index, 1); }
  });
  const region = {appendChild: value => toasts.push(value), querySelectorAll: () => toasts};
  const document = {
    readyState: "loading", visibilityState: "visible", addEventListener: noop,
    createElement: tag => { assert.equal(tag, "div"); return toastNode(); },
    querySelector: selector => selector === "[data-portal-toast]" ? region : null,
    querySelectorAll: selector => selector === "[data-portal-action]" ? Object.values(buttons) : selector === "[data-portal-form]" ? forms : [],
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null},
    body: {classList: {add: noop, remove: noop, toggle: noop}}
  };
  const storage = name => ({
    getItem: () => null, setItem: (...args) => storageWrites.push({name, operation: "set", args}),
    removeItem: (...args) => storageWrites.push({name, operation: "remove", args})
  });
  const window = {
    document, navigator: {language: locale},
    location: {pathname: "/asset-vault", search: "", origin: "https://unit.invalid", href: "https://unit.invalid/asset-vault", assign: value => navigations.push(value)},
    addEventListener: (name, fn) => listeners.set(name, fn), dispatchEvent: noop,
    setTimeout: () => 0, clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: storage("local"), sessionStorage: storage("session"), crypto: webcrypto
  };
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {
    get: () => state, set: value => { state = value; stateHistory.push(clone(value)); }
  });
  const fetch = (url, options = {}) => {
    const parsed = new URL(url, "https://unit.invalid"), method = options.method || "GET";
    assert.equal(parsed.origin, "https://unit.invalid", "Synthetic requests cannot leave unit.invalid");
    const list = parsed.pathname === "/api/v1/asset-vault";
    const lifecycle = parsed.pathname === `/api/v1/asset-vault/${ASSET_ID}/lifecycle`;
    const mutation = ["/api/v1/asset-vault/upload", `/api/v1/asset-vault/${ASSET_ID}/archive`, `/api/v1/asset-vault/${ASSET_ID}/restore`].includes(parsed.pathname);
    assert.ok((method === "GET" && (list || lifecycle)) || (method === "POST" && mutation), "Only synthetic Vault transport allowed");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    assert.equal(options.headers.get("Accept"), "application/json");
    assert.match(options.headers.get("X-Request-ID"), /^[A-Za-z0-9._:-]{12,160}$/);
    if (method === "GET") {
      assert.equal(options.body, undefined);
      assert.equal(options.headers.has("X-CSRF-Token"), false);
      if (list) assert.ok([...parsed.searchParams.keys()].every(key => ["limit", "offset", "q", "state"].includes(key)));
      else assert.equal(parsed.search, "");
    } else {
      assert.equal(options.headers.get("X-CSRF-Token"), CSRF);
      assert.equal(parsed.search, "");
    }
    const entry = {path: parsed.pathname, method, query: Object.fromEntries(parsed.searchParams), headers: Object.fromEntries(options.headers)};
    network.push(entry);
    let resolve;
    const promise = new Promise(yes => { resolve = yes; });
    pending.push({resolve, options, entry, kind: method === "POST" ? "mutation" : list ? "list" : "lifecycle", settled: false});
    return promise;
  };
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Headers, FormData, File, Blob,
    AbortController, Intl, console, fetch, crypto: webcrypto, setTimeout: window.setTimeout, clearTimeout: noop
  });
  vm.runInContext(source.raw.i18n, sandbox, {filename: source.paths.i18n});
  window.TOANAASI18n.setLocale(locale, {emit: false});
  const anchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(source.raw.integration.split(anchor).length - 1, 1, "Unique test exposure anchor");
  const exposure = "  window.__vaultWriteProbe={submissions:()=>Array.from(submissions.entries()).map(([scope,entry])=>({scope,...entry}))};\n";
  const executed = source.raw.integration.replace(anchor, exposure + anchor);
  vm.runInContext(executed, sandbox, {filename: source.paths.integration});
  assert.equal(network.length, 0, "Initial hydration remains untriggered");
  return {
    source, operation, pending, network, stateHistory, file,
    binding: {paths: source.paths, hashes: source.hashes, executedHash: hash(executed),
      physicalBytes: Buffer.byteLength(source.raw.integration), executedBytes: Buffer.byteLength(executed), exposureBytes: Buffer.byteLength(exposure)},
    get state() { return state; },
    run(action = operation, fields = {}, detail = {}) {
      return listeners.get("toanaas:portal-action")({detail: {
        action: ACTION[action], route: "/asset-vault", vaultAssetId: ASSET_ID,
        fields: {file, display_name: "  SYNTHETIC   DISPLAY  ", project_id: " " + PROJECT_ID + " ", ...fields}, ...detail
      }});
    },
    settle(index, settings = {}) {
      const row = pending[index];
      assert.ok(row, "Expected controlled request");
      assert.equal(row.settled, false);
      row.settled = true;
      const payload = {ok: settings.payloadOk ?? true, status: settings.payloadOk === false ? "error" : "ok", data: settings.data ?? {}};
      if (Object.hasOwn(settings, "message")) payload.message = settings.message;
      row.resolve({ok: settings.responseOk ?? true, status: settings.status ?? 200, json: async () => payload});
    },
    submissions: () => clone(window.__vaultWriteProbe.submissions()),
    busy(action = operation) {
      const key = ACTION[action];
      return clone({button: {disabled: buttons[key].disabled, aria: buttons[key].attributes["aria-busy"]},
        submit: {disabled: submits[key].disabled, aria: submits[key].attributes["aria-busy"]}});
    },
    mutate(type, value) {
      if (type === "route") { state = {...state, path: value}; window.location.pathname = value; }
      else if (type === "capability") state = {...state, capabilities: {...state.capabilities, [value]: false}};
      else throw Error("Unknown synthetic mutation");
    },
    clearToasts() { for (const node of [...toasts]) node.remove(); },
    observe() {
      return clone({state, network, storageWrites, navigations, busyEvents,
        toasts: toasts.map(node => ({text: node.textContent, role: node.attributes.role, className: node.className}))});
    }
  };
}
