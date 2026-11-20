import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

export const BASE = "4080b879ad8d6ded081aa47313bf9cac67121f0b";
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const IDS = Object.freeze(["11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"]);
export const CUSTOMER = `Facebook TikTok <img src=x onerror="literal"> 'customer' & "quoted"`;
export const OLD_RIGHTS = "Tôi xác nhận có quyền sử dụng các tệp và brief trong collection này.";
const FILES = Object.freeze({portal: "static/portal/portal.js", i18n: "static/portal/portal-i18n.js"});
const BASE_LF = Object.freeze({portal: "11f9b1ab0fda5b0f4aa26538a14d72c94053a2cdf8def49c60754c9ae638b214",
  i18n: "768b1ba4102ed67b387ba4f62b98009cbcd82fb76decdc1992365aa84393aed2"});
const EXPOSE = Object.freeze(["mediaCollectionValues", "renderMediaWorkspace", "renderMediaCollectionCards",
  "renderMediaWorkspacePagination", "renderMemoryPagination", "mediaCollectionFormFields",
  "mediaCollectionShellFormFields", "renderMediaWorkspaceDetail"]);
export const plain = value => JSON.parse(JSON.stringify(value));
export const hash = value => createHash("sha256").update(value).digest("hex");
export function freeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
export function sources({baseline = false, root = ROOT} = {}) {
  const raw = Object.fromEntries(Object.entries(FILES).map(([key, relative]) => [key,
    baseline ? execFileSync("git", ["show", BASE + ":" + relative], {
      cwd: root, encoding: "utf8", maxBuffer: 30e6, windowsHide: true
    }) : fs.readFileSync(path.join(root, relative), "utf8")]));
  const hashes = Object.fromEntries(Object.entries(raw).map(([key, value]) => [key, hash(value)]));
  if (baseline) for (const key of Object.keys(raw)) assert.equal(hash(raw[key].replace(/\r\n/g, "\n")), BASE_LF[key], "Immutable BASE full bundle");
  return {raw, hashes, baseline, paths: Object.fromEntries(Object.entries(FILES).map(([key, value]) => [key, path.join(root, value)]))};
}

// Full physical bundles, one unique exposure insertion, no extracted/replaced app function.
export function runtime(source, locale = "vi") {
  const attempts = [], attrs = {}, noop = () => {};
  const deny = kind => (..._args) => { attempts.push(kind); throw Error("Forbidden VM side effect: " + kind); };
  const storage = name => ({getItem: deny(name + ".getItem"), setItem: deny(name + ".setItem"),
    removeItem: deny(name + ".removeItem"), clear: deny(name + ".clear")});
  const document = {readyState: "loading", title: "", addEventListener: noop, querySelector: () => null,
    querySelectorAll: () => [], getElementById: () => null, createElement: deny("document.createElement"),
    documentElement: {lang: locale, setAttribute: (key, value) => { attrs[key] = value; },
      getAttribute: key => attrs[key] ?? null, classList: {add: noop, remove: noop}},
    body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop}};
  const location = {pathname: "/media-workspace", search: "", href: "https://unit.invalid/media-workspace",
    origin: "https://unit.invalid", assign: deny("navigation.assign"), replace: deny("navigation.replace"), reload: deny("navigation.reload")};
  const window = {document, navigator: {language: locale, userAgent: "Media collection full physical VM", sendBeacon: deny("sendBeacon")},
    location, addEventListener: noop, dispatchEvent: deny("dispatchEvent"), CustomEvent: function () {},
    matchMedia: () => ({matches: false, addEventListener: noop}), localStorage: storage("localStorage"),
    sessionStorage: storage("sessionStorage"), fetch: deny("fetch"), XMLHttpRequest: deny("XMLHttpRequest"),
    WebSocket: deny("WebSocket"), indexedDB: {open: deny("indexedDB.open"), deleteDatabase: deny("indexedDB.deleteDatabase")},
    history: {pushState: deny("history.pushState"), replaceState: deny("history.replaceState")},
    setTimeout: deny("setTimeout"), clearTimeout: deny("clearTimeout"),
    setInterval: deny("setInterval"), clearInterval: deny("clearInterval"),
    requestAnimationFrame: deny("requestAnimationFrame"), cancelAnimationFrame: deny("cancelAnimationFrame")};
  const sandbox = vm.createContext({window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console,
    fetch: window.fetch, XMLHttpRequest: window.XMLHttpRequest, WebSocket: window.WebSocket,
    localStorage: window.localStorage, sessionStorage: window.sessionStorage, location, history: window.history,
    setTimeout: window.setTimeout, clearTimeout: window.clearTimeout, setInterval: window.setInterval,
    clearInterval: window.clearInterval, requestAnimationFrame: window.requestAnimationFrame});
  vm.runInContext(source.raw.i18n, sandbox, {filename: source.paths.i18n, timeout: 10000});
  const i18n = window.TOANAASI18n;
  i18n.setLocale(locale, {emit: false});
  let translator = i18n;
  const renderWindow = Object.create(window);
  Object.defineProperty(renderWindow, "TOANAASI18n", {get: () => translator});
  Object.defineProperty(renderWindow, "TOAN_AAS_I18N", {get: () => translator});
  sandbox.window = renderWindow;
  const marker = "  window.TOANAASPortal = Object.freeze({";
  assert.equal(source.raw.portal.split(marker).length - 1, 1, "Exactly one physical exposure anchor");
  const exposure = `  window.__mediaCollectionQA = Object.freeze({${EXPOSE.join(",")}});\n`;
  const executed = source.raw.portal.replace(marker, exposure + marker);
  vm.runInContext(executed, sandbox, {filename: source.paths.portal, timeout: 10000});
  const api = renderWindow.__mediaCollectionQA;
  for (const name of EXPOSE) assert.equal(typeof api[name], "function", "Real renderer export: " + name);
  assert.deepEqual(attempts, [], "Full physical initialization cannot cause side effects");
  return {
    source, messages: i18n.messages,
    binding: {hashes: source.hashes, executedPortalHash: hash(executed), exposureCount: 1,
      physicalPortalBytes: Buffer.byteLength(source.raw.portal), executedPortalBytes: Buffer.byteLength(executed),
      exposureBytes: Buffer.byteLength(exposure), replacedProductionFunctions: 0},
    setLocale(value) { i18n.setLocale(value, {emit: false}); assert.deepEqual(attempts, []); },
    currentLocale: () => i18n.currentLocale(),
    missingTranslator(value = true) { translator = value ? undefined : i18n; },
    page(route) { return renderWindow.TOANAASPortal.resolvePage(route); },
    body(name) { assert.ok(EXPOSE.includes(name)); return String(api[name]); },
    call(name, ...args) {
      assert.ok(EXPOSE.includes(name), "Only frozen exact exposures");
      const before = args.map(value => JSON.stringify(value));
      args.forEach(freeze);
      const result = api[name](...args);
      assert.deepEqual(args.map(value => JSON.stringify(value)), before, "Frozen caller inputs remain exact");
      assert.deepEqual(attempts, [], "No fetch/storage/navigation/dispatch/timer side effects");
      return result;
    },
    attempts: () => [...attempts]
  };
}

export function collection(changes = {}) {
  return {id: IDS[0], account_id: IDS[2], title: CUSTOMER, description: CUSTOMER, creative_brief: CUSTOMER,
    brief_excerpt: CUSTOMER, description_excerpt: CUSTOMER, prompt_mode: "background", use_context: "Customer usage",
    tags: ["customer tag", "TikTok"], project_id: IDS[1], rights_note: CUSTOMER,
    policy: {status: "clear", marker: null}, state: "active", revision: 7,
    created_at: "2026-11-20T08:00:00Z", updated_at: "2026-11-20T09:00:00Z",
    archived_at: null, execution: "authoring_only", ...changes};
}
export function context({canView = true, canCreate = true, row = collection(), overrides = {}} = {}) {
  const capabilities = Object.fromEntries(["view", "create", "update", "archive", "restore", "duplicate",
    "restore-version", "compose", "item-attach", "item-update"].map(key => ["media-workspace-" + key, true]));
  capabilities["media-workspace-view"] = canView; capabilities["media-workspace-create"] = canCreate;
  return {path: "/media-workspace", interfaceLocale: "vi", capabilities,
    session: {authenticated: true, csrfToken: "SYNTHETIC_UNIT_ONLY"},
    projects: [{id: IDS[1], title: "SYNTHETIC PROJECT", state: "active"}],
    mediaWorkspaceReadState: "ready", mediaCollections: [row],
    mediaWorkspaceSummary: {collections: {total: 1, active: 1, archived: 0}, items: {total: 0, favorites: 0},
      execution: {authoring: "ready", generation: "guarded"}},
    mediaWorkspaceListing: {filters: {q: "", tag: "", prompt_mode: "", state: "all"},
      pagination: {limit: 50, offset: 0, returned: 1, previous_offset: null, has_more: true, next_offset: 50}},
    mediaWorkspaceEvents: [{id: IDS[2], collection_id: IDS[0], action: "collection_created",
      revision: 7, created_at: "2026-11-20T09:01:02Z"}],
    mediaWorkspacePolicy: {policy: ["QA_CANONICAL_PROVIDER_TECHNICAL_POLICY"],
      guarded_capabilities: ["qa_provider_runtime_guarded"], status: "guarded"},
    mediaCollectionDetail: {collection: row, versions: [{revision: 7, title: CUSTOMER,
      prompt_mode: "background", created_at: row.created_at}], items: [], item_count: 0, item_limit: 250},
    mediaAudioAssets: [], mediaAudioAssetListing: {filters: {q: ""},
      pagination: {limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null}},
    ...overrides};
}
