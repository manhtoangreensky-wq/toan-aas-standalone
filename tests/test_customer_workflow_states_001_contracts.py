"""Behavior contracts for truthful Customer Workspace, Jobs, and Assets states."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "static" / "portal" / "portal.js"
INTEGRATION = ROOT / "static" / "portal" / "integration.js"
I18N = ROOT / "static" / "portal" / "portal-i18n.js"


def _run_node(script: str, *paths: Path) -> dict:
    node = shutil.which("node")
    assert node, "Node.js is required for the workflow-state behavior contract"
    result = subprocess.run(
        [node, "-e", script, *(str(path) for path in paths)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


EXTRACTOR = r'''
const fs = require("fs");

function extractFunction(source, name) {
  const token = `function ${name}(`;
  const declarations = [];
  let searchFrom = 0;
  while (true) {
    const functionStart = source.indexOf(token, searchFrom);
    if (functionStart < 0) break;
    const start = source.slice(Math.max(0, functionStart - 6), functionStart) === "async " ? functionStart - 6 : functionStart;
    const open = source.indexOf("{", functionStart + token.length);
    if (open < 0) throw new Error(`missing body for production function ${name}`);
    let depth = 0;
    let quote = "";
    let escaped = false;
    let lineComment = false;
    let blockComment = false;
    let finish = -1;
    for (let index = open; index < source.length; index += 1) {
      const char = source[index];
      const next = source[index + 1] || "";
      if (lineComment) {
        if (char === "\n") lineComment = false;
        continue;
      }
      if (blockComment) {
        if (char === "*" && next === "/") { blockComment = false; index += 1; }
        continue;
      }
      if (quote) {
        if (escaped) { escaped = false; continue; }
        if (char === "\\") { escaped = true; continue; }
        if (char === quote) quote = "";
        continue;
      }
      if (char === "/" && next === "/") { lineComment = true; index += 1; continue; }
      if (char === "/" && next === "*") { blockComment = true; index += 1; continue; }
      if (char === "'" || char === '"' || char === "`") { quote = char; continue; }
      if (char === "{") depth += 1;
      if (char === "}") {
        depth -= 1;
        if (depth === 0) { finish = index + 1; break; }
      }
    }
    if (finish < 0) throw new Error(`unterminated production function ${name}`);
    declarations.push(source.slice(start, finish));
    searchFrom = finish;
  }
  if (!declarations.length) throw new Error(`missing production function ${name}`);
  if (declarations.some((value) => value !== declarations[0])) {
    throw new Error(`ambiguous non-equivalent production function ${name}`);
  }
  return declarations[0];
}

function maybeFunction(source, name) {
  return source.includes(`function ${name}(`) ? extractFunction(source, name) : "";
}

function safeText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
'''


def test_workspace_renderer_never_turns_nonready_reads_into_an_empty_library() -> None:
    result = _run_node(
        EXTRACTOR
        + r'''
const portal = fs.readFileSync(process.argv[1], "utf8");
const runtime = [
  extractFunction(portal, "validWorkspaceDraftId"),
  extractFunction(portal, "workspaceDraftItems"),
  extractFunction(portal, "workspaceDraftListing"),
  extractFunction(portal, "workspaceDraftText"),
  extractFunction(portal, "workspaceDraftStatus"),
  extractFunction(portal, "workspaceDraftReadState"),
  maybeFunction(portal, "deliveryListReadState"),
  maybeFunction(portal, "renderCollectionReadState"),
  extractFunction(portal, "renderWorkspaceDrafts")
].filter(Boolean).join("\n");

const ICONS = { refresh: "refresh", security: "security" };
function uiText(key, fallback) { return key || fallback; }
function badge(state) { return `<badge data-badge="${safeText(state)}"></badge>`; }
function portalStatusIcon(state) { return `icon-${state}`; }
function renderHero() { return "<hero></hero>"; }
function renderEmpty(title, body) { return `<empty data-empty-title="${safeText(title)}">${safeText(body)}</empty>`; }
function normalizeWorkspaceDraftListing(value) {
  const source = value && typeof value === "object" ? value : {};
  return {
    filters: source.filters || { q: "", state: "all", feature_key: "" },
    summary: source.summary || {},
    pagination: source.pagination || {}
  };
}
function workspaceDraftFilterFields() { return []; }
function workspaceDraftFilterIsActive(filter) { return Boolean(filter && (filter.q || filter.feature_key || filter.state && filter.state !== "all")); }
function renderFields() { return ""; }
function renderWorkspaceDraftPagination() { return ""; }
function validProjectId() { return false; }
function localizedCompareText(left, right) { return String(left).localeCompare(String(right)); }
eval(runtime);

const base = {
  capabilities: {
    "workspace-drafts-refresh": true,
    "workspace-draft-archive": true,
    "workspace-draft-resume": true,
    "workspace-draft-attach": true
  },
  workspaceDraftListing: { filters: { q: "", state: "all", feature_key: "" }, summary: {}, pagination: {} },
  workspaceDrafts: [],
  projects: [],
  catalog: [],
  workspaceDraftFeatures: []
};
const html = {};
for (const state of ["loading", "failed", "guarded"]) {
  html[state] = renderWorkspaceDrafts({ path: "/workspace" }, { ...base, workspaceDraftReadState: state });
}
html.empty = renderWorkspaceDrafts({ path: "/workspace" }, { ...base, workspaceDraftReadState: "ready" });
html.record = renderWorkspaceDrafts({ path: "/workspace" }, {
  ...base,
  workspaceDraftReadState: "ready",
  workspaceDrafts: [{
    id: "11111111-1111-4111-8111-111111111111",
    state: "draft",
    route: "/features",
    title: "<img src=x onerror=alert(1)>",
    feature_key: "content",
    feature_title: "Content",
    created_at: "2026-09-01"
  }]
});

const emptyKey = "workspaceDrafts.empty.title";
assert(html.loading.includes('data-workspace-draft-read-state="loading"'), "Workspace loading marker is missing");
assert(html.loading.includes('data-state="processing"'), "Workspace loading is not explicit processing");
assert(!html.loading.includes(emptyKey), "Workspace loading is disguised as ready-empty");
assert(!html.loading.includes('data-portal-action="workspace-drafts-refresh"'), "Workspace loading exposes an enabled refresh");
assert(html.failed.includes('data-workspace-draft-read-state="failed"'), "Workspace failed marker is missing");
assert((html.failed.match(/data-portal-action="workspace-drafts-refresh"/g) || []).length === 1, "Workspace failed must expose exactly one refresh");
assert(!html.failed.includes(emptyKey), "Workspace failed is disguised as ready-empty");
assert(html.guarded.includes('data-workspace-draft-read-state="guarded"'), "Workspace guarded marker is missing");
assert(html.guarded.includes('href="/account"'), "Workspace guarded state does not open Account");
assert(!html.guarded.includes('data-portal-action="workspace-drafts-refresh"'), "Workspace guarded state exposes refresh");
assert(!html.guarded.includes(emptyKey), "Workspace guarded is disguised as ready-empty");
assert(html.empty.includes('data-workspace-draft-read-state="ready"'), "Workspace ready marker is missing");
assert(html.empty.includes(emptyKey), "Workspace real empty state was lost");
assert(html.record.includes('data-workspace-draft-read-state="ready"'), "Workspace record state is not ready");
assert(html.record.includes("&lt;img src=x onerror=alert(1)&gt;"), "Workspace record no longer uses escaped presentation");
assert(!html.record.includes("<img src=x onerror=alert(1)>"), "Workspace record renders unsafe title markup");
assert(!html.record.includes(emptyKey), "Workspace record is disguised as empty");
process.stdout.write(JSON.stringify({ states: Object.keys(html) }));
''',
        PORTAL,
    )
    assert result == {"states": ["loading", "failed", "guarded", "empty", "record"]}


DELIVERY_RENDER_HARNESS = (
    EXTRACTOR
    + r'''
const portal = fs.readFileSync(process.argv[1], "utf8");
const runtime = [
  extractFunction(portal, "workspaceDraftReadState"),
  maybeFunction(portal, "deliveryListReadState"),
  maybeFunction(portal, "renderCollectionReadState")
].filter(Boolean);
function uiText(key, fallback) { return key || fallback; }
function deliveryCenterText(key, fallback) { return `deliveryCenter.${key}` || fallback; }
function badge(state) { return `<badge data-badge="${safeText(state)}"></badge>`; }
function portalStatusIcon(state) { return `icon-${state}`; }
function renderHero() { return "<hero></hero>"; }
function renderDeliveryWorkspaceNav(path) { return `<nav data-route="${safeText(path)}"></nav>`; }
function renderStatusCard() { return "<status-card></status-card>"; }
function renderSummary() { return "<summary-card></summary-card>"; }
function deliveryReadRefreshBusy() { return false; }
function deliveryReadReceiptAttribute() { return ""; }
function filterBar() { return "<filter-bar></filter-bar>"; }
function localizedDeliveryFilters(kind, filters) { return filters; }
function renderDeliveryReceiptSurface() { return "<receipt></receipt>"; }
function renderJobDeliverySummary() { return "jobs-summary"; }
function renderAssetDeliverySummary() { return "assets-summary"; }
function jobStatus(item) { return String(item && item.status || "queued"); }
function assetRecordStatus(item) { return String(item && item.status || "completed"); }
function assetRecordIdentity() { return { kind: "canonical" }; }
function jobCost() { return "0"; }
function reportedOutput() { return "none"; }
function assetJobLink(item) { return safeText(item && item.id); }
function assetDeliveryState() { return "guarded"; }
function renderJobMobileCard() { return ""; }
function renderAssetMobileCard() { return ""; }
function renderDeliveryRecords(kind, columns, rows, renderRow, renderCard, emptyTitle) {
  return rows.length
    ? `<records data-kind="${safeText(kind)}">${rows.map((row) => safeText(row.id)).join("|")}</records>`
    : `<empty data-empty-title="${safeText(emptyTitle)}"></empty>`;
}
const JOB_FILTERS = [["all", "All"], ["queued", "Queued"]];
const ASSET_FILTERS = [["all", "All"], ["completed", "Completed"]];
function stateFor() { return "read_only"; }
'''
)


def test_jobs_renderer_exposes_five_truthful_states_without_false_first_actions() -> None:
    result = _run_node(
        DELIVERY_RENDER_HARNESS
        + r'''
runtime.push(extractFunction(portal, "renderJobs"));
eval(runtime.join("\n"));
const base = { capabilities: { "refresh-jobs": true }, jobFilter: "all", jobs: [] };
const html = {};
for (const state of ["loading", "failed", "guarded"]) html[state] = renderJobs({ path: "/jobs" }, { ...base, jobsReadState: state });
html.empty = renderJobs({ path: "/jobs" }, { ...base, jobsReadState: "ready" });
html.record = renderJobs({ path: "/jobs" }, { ...base, jobsReadState: "ready", jobs: [{ id: "job-1", status: "queued" }] });
const firstKey = "deliveryCenter.jobs.first.note";
const emptyKey = "deliveryCenter.jobs.empty.title";
assert(html.loading.includes('data-delivery-read-state="loading"') && html.loading.includes('data-state="processing"'), "Jobs loading state is not explicit");
assert(!html.loading.includes(firstKey) && !html.loading.includes(emptyKey), "Jobs loading is disguised as ready-empty");
assert(!html.loading.includes('data-portal-action="refresh-jobs"'), "Jobs loading exposes refresh");
assert((html.failed.match(/data-portal-action="refresh-jobs"/g) || []).length === 1, "Jobs failed must expose exactly one refresh");
assert(!html.failed.includes(firstKey) && !html.failed.includes(emptyKey), "Jobs failed is disguised as ready-empty");
assert(html.guarded.includes('href="/account"'), "Jobs guarded state does not open Account");
assert(!html.guarded.includes('data-portal-action="refresh-jobs"'), "Jobs guarded state exposes refresh");
assert(!html.guarded.includes(firstKey) && !html.guarded.includes(emptyKey), "Jobs guarded is disguised as ready-empty");
assert(html.empty.includes('data-delivery-read-state="ready"') && html.empty.includes(firstKey) && html.empty.includes(emptyKey), "Jobs real empty state or first actions were lost");
assert(html.record.includes('data-delivery-read-state="ready"') && html.record.includes("job-1"), "Jobs ready record was lost");
assert(!html.record.includes(firstKey) && !html.record.includes(emptyKey), "Jobs ready record is disguised as empty");
process.stdout.write(JSON.stringify({ states: Object.keys(html) }));
''',
        PORTAL,
    )
    assert result == {"states": ["loading", "failed", "guarded", "empty", "record"]}


def test_assets_renderer_exposes_five_truthful_states_without_false_first_actions() -> None:
    result = _run_node(
        DELIVERY_RENDER_HARNESS
        + r'''
runtime.push(extractFunction(portal, "renderAssets"));
eval(runtime.join("\n"));
const base = { capabilities: { "refresh-assets": true }, assetFilter: "all", assets: [] };
const html = {};
for (const state of ["loading", "failed", "guarded"]) html[state] = renderAssets({ path: "/assets" }, { ...base, assetsReadState: state });
html.empty = renderAssets({ path: "/assets" }, { ...base, assetsReadState: "ready" });
html.record = renderAssets({ path: "/assets" }, { ...base, assetsReadState: "ready", assets: [{ id: "asset-1", status: "completed" }] });
const firstKey = "deliveryCenter.assets.first.note";
const emptyKey = "deliveryCenter.assets.empty.allTitle";
assert(html.loading.includes('data-delivery-read-state="loading"') && html.loading.includes('data-state="processing"'), "Assets loading state is not explicit");
assert(!html.loading.includes(firstKey) && !html.loading.includes(emptyKey), "Assets loading is disguised as ready-empty");
assert(!html.loading.includes('data-portal-action="refresh-assets"'), "Assets loading exposes refresh");
assert((html.failed.match(/data-portal-action="refresh-assets"/g) || []).length === 1, "Assets failed must expose exactly one refresh");
assert(!html.failed.includes(firstKey) && !html.failed.includes(emptyKey), "Assets failed is disguised as ready-empty");
assert(html.guarded.includes('href="/account"'), "Assets guarded state does not open Account");
assert(!html.guarded.includes('data-portal-action="refresh-assets"'), "Assets guarded state exposes refresh");
assert(!html.guarded.includes(firstKey) && !html.guarded.includes(emptyKey), "Assets guarded is disguised as ready-empty");
assert(html.empty.includes('data-delivery-read-state="ready"') && html.empty.includes(firstKey) && html.empty.includes(emptyKey), "Assets real empty state or first actions were lost");
assert(html.record.includes('data-delivery-read-state="ready"') && html.record.includes("asset-1"), "Assets ready record was lost");
assert(!html.record.includes(firstKey) && !html.record.includes(emptyKey), "Assets ready record is disguised as empty");
process.stdout.write(JSON.stringify({ states: Object.keys(html) }));
''',
        PORTAL,
    )
    assert result == {"states": ["loading", "failed", "guarded", "empty", "record"]}


def test_initial_jobs_and_assets_hydration_fences_every_terminal_state() -> None:
    result = _run_node(
        EXTRACTOR
        + r'''
const integration = fs.readFileSync(process.argv[1], "utf8");
const runtime = [
  extractFunction(integration, "isSafeDeliveryReadRecord"),
  extractFunction(integration, "deliveryReadItemsOrThrow"),
  extractFunction(integration, "hydrateDeliveryList")
].join("\n");
let state = {};
let merges = [];
let current = true;
let apiImpl = async () => ({ data: { items: [] } });
let apiPaths = [];
let polling = [];
function base() { return state; }
function merge(next) { merges.push(next); state = { ...state, ...next }; }
async function api(path) { apiPaths.push(path); return apiImpl(path); }
function scheduleJobPolling(path, items) { polling.push({ path, ids: items.map((item) => item.id) }); }
eval(runtime);

function reset(kind, path) {
  state = { pageStates: { [path]: "read_only" }, [kind]: [{ id: "stale", status: "completed" }] };
  merges = [];
  current = true;
  apiPaths = [];
  polling = [];
}

async function settled(kind, path, response, shouldThrow = false) {
  reset(kind, path);
  apiImpl = async () => { if (shouldThrow) throw new Error("network"); return response; };
  const value = await hydrateDeliveryList(kind, path, kind === "jobs" ? "Job Center" : "Assets", () => current);
  return { value, state, merges: merges.length, apiPaths: [...apiPaths], polling: [...polling] };
}

function deferredCase(kind, path, reject) {
  reset(kind, path);
  let resolvePromise;
  let rejectPromise;
  apiImpl = () => new Promise((resolve, rejectCall) => { resolvePromise = resolve; rejectPromise = rejectCall; });
  const promise = hydrateDeliveryList(kind, path, kind === "jobs" ? "Job Center" : "Assets", () => current);
  const loading = { state: { ...state }, merges: merges.length, apiPaths: [...apiPaths] };
  current = false;
  if (reject) rejectPromise(new Error("late failure"));
  else resolvePromise({ data: { items: [{ id: `${kind}-fresh`, status: "completed" }] } });
  return promise.then((value) => ({ loading, value, state: { ...state }, merges: merges.length, polling: [...polling] }));
}

(async () => {
  const cases = {};
  for (const [kind, path, record] of [
    ["jobs", "/jobs", { id: "job-1", status: "queued" }],
    ["assets", "/assets", { id: "asset-1", status: "completed" }]
  ]) {
    cases[kind] = {
      empty: await settled(kind, path, { data: { items: [] } }),
      record: await settled(kind, path, { data: { items: [record] } }),
      missing: await settled(kind, path, { data: {} }),
      nonArray: await settled(kind, path, { data: { items: {} } }),
      unsafeId: await settled(kind, path, { data: { items: [{ id: "unsafe id", status: "queued" }] } }),
      unsafeStatus: await settled(kind, path, { data: { items: [{ id: `${kind}-1`, status: "unsafe status" }] } }),
      thrown: await settled(kind, path, null, true),
      staleSuccess: await deferredCase(kind, path, false),
      staleFailure: await deferredCase(kind, path, true)
    };
  }

  for (const [kind, path] of [["jobs", "/jobs"], ["assets", "/assets"]]) {
    const currentCases = cases[kind];
    for (const key of ["empty", "record"]) {
      const item = currentCases[key];
      assert(item.state[`${kind}ReadState`] === "ready", `${kind} ${key} did not become ready`);
      assert(item.state.pageStates[path] === "read_only", `${kind} ${key} page is not read_only`);
      assert(item.merges === 2 && item.apiPaths.length === 1, `${kind} ${key} did not have one loading and one terminal merge`);
    }
    assert(currentCases.empty.state[kind].length === 0, `${kind} valid empty was not retained`);
    assert(currentCases.record.state[kind][0].id.endsWith("-1"), `${kind} valid record was not retained`);
    for (const key of ["missing", "nonArray", "unsafeId", "unsafeStatus", "thrown"]) {
      const item = currentCases[key];
      assert(item.value === null, `${kind} ${key} did not fail closed`);
      assert(item.state[kind].length === 0, `${kind} ${key} retained stale records`);
      assert(item.state[`${kind}ReadState`] === "failed", `${kind} ${key} is not failed`);
      assert(item.state.pageStates[path] === "guarded", `${kind} ${key} page is not guarded`);
      assert(item.merges === 2, `${kind} ${key} terminal state was not merged exactly once`);
      assert(item.polling.length === 0, `${kind} ${key} scheduled polling`);
    }
    for (const key of ["staleSuccess", "staleFailure"]) {
      const item = currentCases[key];
      assert(item.loading.state[kind].length === 0, `${kind} ${key} did not clear stale records before GET`);
      assert(item.loading.state[`${kind}ReadState`] === "loading", `${kind} ${key} did not enter loading before GET`);
      assert(item.loading.state.pageStates[path] === "loading", `${kind} ${key} page did not enter loading before GET`);
      assert(item.merges === 1, `${kind} ${key} performed a stale terminal overwrite`);
      assert(item.state[`${kind}ReadState`] === "loading", `${kind} ${key} changed the loading state after becoming stale`);
      assert(item.polling.length === 0, `${kind} ${key} scheduled polling`);
    }
    if (kind === "jobs") {
      assert(currentCases.empty.polling.length === 1 && currentCases.record.polling.length === 1, "Jobs polling was not scheduled after validated ready reads");
    } else {
      assert(currentCases.empty.polling.length === 0 && currentCases.record.polling.length === 0, "Assets unexpectedly scheduled job polling");
    }
  }
  process.stdout.write(JSON.stringify({ checked: ["jobs", "assets"], cases: Object.keys(cases.jobs) }));
})().catch((error) => { process.stderr.write(error.stack || String(error)); process.exit(1); });
''',
        INTEGRATION,
    )
    assert result["checked"] == ["jobs", "assets"]
    assert result["cases"] == [
        "empty",
        "record",
        "missing",
        "nonArray",
        "unsafeId",
        "unsafeStatus",
        "thrown",
        "staleSuccess",
        "staleFailure",
    ]


def test_state_catalog_and_bootstrap_wiring_are_symmetric_and_fail_closed() -> None:
    result = _run_node(
        r'''
require(process.argv[1]);
const api = globalThis.TOANAASI18n;
if (!api) throw new Error("Portal i18n API did not load");
const roots = ["workspaceDrafts.state", "deliveryCenter.jobs.state", "deliveryCenter.assets.state"];
const suffixes = ["loadingTitle", "loadingBody", "failedTitle", "failedBody", "failedAction", "guardedTitle", "guardedBody", "guardedAction"];
const values = {};
for (const locale of ["vi", "en", "zh"]) {
  values[locale] = {};
  for (const root of roots) {
    values[locale][root] = {};
    for (const suffix of suffixes) {
      const key = `${root}.${suffix}`;
      if (!Object.prototype.hasOwnProperty.call(api.messages[locale], key)) throw new Error(`missing ${locale}:${key}`);
      const value = String(api.messages[locale][key] || "").trim();
      if (!value) throw new Error(`blank ${locale}:${key}`);
      values[locale][root][suffix] = value;
    }
  }
}
const mixed = /\b(owner-scoped|signed|account|bridge|server|loading|failed|guarded)\b/i;
for (const locale of ["vi", "zh"]) {
  for (const root of roots) for (const value of Object.values(values[locale][root])) {
    if (mixed.test(value)) throw new Error(`mixed-language ${locale}: ${value}`);
  }
}
process.stdout.write(JSON.stringify({ locales: Object.keys(values), roots, suffixes }));
''',
        I18N,
    )
    assert result["locales"] == ["vi", "en", "zh"]
    assert len(result["roots"]) == 3
    assert len(result["suffixes"]) == 8

    portal = PORTAL.read_text(encoding="utf-8")
    integration = INTEGRATION.read_text(encoding="utf-8")
    assert 'jobsReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.jobsReadState || ""))' in portal
    assert 'assetsReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.assetsReadState || ""))' in portal
    assert 'jobsReadState: account && bridgeAvailable ? "loading" : "guarded"' in integration
    assert 'assetsReadState: account && bridgeAvailable ? "loading" : "guarded"' in integration
    assert 'await hydrateDeliveryList("jobs", path, "Job Center", isCurrent)' in integration
    assert 'await hydrateDeliveryList("assets", path, "Assets", isCurrent)' in integration
    assert "canonicalRequestIsCurrent()" not in integration


def test_manual_retry_success_restores_ready_state_for_jobs_and_assets() -> None:
    result = _run_node(
        EXTRACTOR
        + r'''
const integration = fs.readFileSync(process.argv[1], "utf8");
const runtime = extractFunction(integration, "mergeDeliveryReadSuccess");
let state = {
  jobs: [],
  jobsReadState: "failed",
  assets: [],
  assetsReadState: "failed",
  pageStates: { "/jobs": "guarded", "/assets": "guarded" }
};
function base() { return state; }
function merge(next) { state = { ...state, ...next }; }
eval(runtime);
const jobReceipt = { kind: "jobs", count: 1 };
const assetReceipt = { kind: "assets", count: 1 };
mergeDeliveryReadSuccess("jobs", "/jobs", [{ id: "job-1", status: "queued" }], jobReceipt);
const jobs = JSON.parse(JSON.stringify(state));
mergeDeliveryReadSuccess("assets", "/assets", [{ id: "asset-1", status: "completed" }], assetReceipt);
const assets = JSON.parse(JSON.stringify(state));
assert(jobs.jobsReadState === "ready" && jobs.pageStates["/jobs"] === "read_only", "Jobs retry did not recover failed lifecycle");
assert(jobs.jobs.length === 1 && jobs.jobs[0].id === "job-1", "Jobs retry lost the validated record");
assert(jobs.deliveryReadReceipt.kind === "jobs", "Jobs retry lost its bounded receipt");
assert(assets.assetsReadState === "ready" && assets.pageStates["/assets"] === "read_only", "Assets retry did not recover failed lifecycle");
assert(assets.assets.length === 1 && assets.assets[0].id === "asset-1", "Assets retry lost the validated record");
assert(assets.deliveryReadReceipt.kind === "assets", "Assets retry lost its bounded receipt");
process.stdout.write(JSON.stringify({ jobs: jobs.jobsReadState, assets: assets.assetsReadState }));
''',
        INTEGRATION,
    )
    assert result == {"jobs": "ready", "assets": "ready"}
    integration = INTEGRATION.read_text(encoding="utf-8")
    assert 'mergeDeliveryReadSuccess("jobs", route, items, receipt);' in integration
    assert 'mergeDeliveryReadSuccess("assets", route, items, receipt);' in integration


def test_jobs_polling_rejects_malformed_rows_and_keeps_the_last_verified_list() -> None:
    result = _run_node(
        EXTRACTOR
        + r'''
const integration = fs.readFileSync(process.argv[1], "utf8");
const runtime = [
  extractFunction(integration, "isSafeDeliveryReadRecord"),
  extractFunction(integration, "deliveryReadItemsOrThrow"),
  extractFunction(integration, "activeJob"),
  extractFunction(integration, "isJobPollingRoute"),
  extractFunction(integration, "jobPollRequestIsCurrent"),
  extractFunction(integration, "scheduleJobPolling")
].join("\n");
const verified = [{ id: "job-verified", status: "processing" }];
let state;
let jobPollTimer;
let jobPollEpoch;
let canonicalSessionEpoch;
let jobPollFailures;
let callback;
let apiImpl;
let merges;
const JOB_POLL_INTERVAL_MS = 1000;
const JOB_POLL_MAX_BACKOFF_MS = 10000;
const window = {
  location: { pathname: "/jobs" },
  setTimeout(handler) { callback = handler; return 1; },
  clearTimeout() {}
};
function base() { return state; }
function merge(next) { merges.push(next); state = { ...state, ...next }; }
async function api(path) { return apiImpl(path); }
function currentPortalPath() { return "/jobs"; }
function jobIdFromPath() { return ""; }
function exactJobRecord() { return {}; }
function ownedAssetsForJob() { return []; }
eval(runtime);

function reset() {
  state = { path: "/jobs", bridge: { available: true }, session: { authenticated: true }, jobs: verified };
  jobPollTimer = 0;
  jobPollEpoch = 0;
  canonicalSessionEpoch = 1;
  jobPollFailures = 0;
  callback = null;
  merges = [];
}

async function malformed(response) {
  reset();
  apiImpl = async () => response;
  scheduleJobPolling("/jobs", verified, 0);
  assert(typeof callback === "function", "Polling callback was not scheduled");
  await callback();
  return { ids: Array.isArray(state.jobs) ? state.jobs.map((item) => item.id) : "NON_ARRAY", merges: merges.length, failures: jobPollFailures, retryScheduled: typeof callback === "function" };
}

async function stale(reject) {
  reset();
  let resolveRequest;
  let rejectRequest;
  apiImpl = () => new Promise((resolve, rejectCall) => { resolveRequest = resolve; rejectRequest = rejectCall; });
  scheduleJobPolling("/jobs", verified, 0);
  const run = callback();
  jobPollEpoch += 1;
  if (reject) rejectRequest(new Error("late failure"));
  else resolveRequest({ data: { items: [{ id: "job-late", status: "completed" }] } });
  await run;
  return { ids: state.jobs.map((item) => item.id), merges: merges.length };
}

(async () => {
  const cases = {
    missing: await malformed({ data: {} }),
    nonArray: await malformed({ data: { items: {} } }),
    unsafeId: await malformed({ data: { items: [{ id: "unsafe id", status: "queued" }] } }),
    unsafeStatus: await malformed({ data: { items: [{ id: "job-1", status: "unsafe status" }] } }),
    staleSuccess: await stale(false),
    staleFailure: await stale(true)
  };
  for (const key of ["missing", "nonArray", "unsafeId", "unsafeStatus"]) {
    const item = cases[key];
    assert(Array.isArray(item.ids) && item.ids.join(",") === "job-verified", `${key} replaced the last verified list`);
    assert(item.merges === 0, `${key} merged malformed polling data`);
    assert(item.failures === 1, `${key} did not use the polling failure/backoff path`);
  }
  for (const key of ["staleSuccess", "staleFailure"]) {
    assert(cases[key].ids.join(",") === "job-verified", `${key} overwrote the last verified list`);
    assert(cases[key].merges === 0, `${key} performed a stale merge`);
  }
  process.stdout.write(JSON.stringify({ cases: Object.keys(cases) }));
})().catch((error) => { process.stderr.write(error.stack || String(error)); process.exit(1); });
''',
        INTEGRATION,
    )
    assert result["cases"] == [
        "missing",
        "nonArray",
        "unsafeId",
        "unsafeStatus",
        "staleSuccess",
        "staleFailure",
    ]


def test_real_canonical_fence_blocks_every_stale_success_and_failure_dimension() -> None:
    result = _run_node(
        EXTRACTOR
        + r'''
const integration = fs.readFileSync(process.argv[1], "utf8");
const runtime = [
  extractFunction(integration, "currentPortalPath"),
  extractFunction(integration, "canonicalRequestIsCurrent"),
  extractFunction(integration, "isSafeDeliveryReadRecord"),
  extractFunction(integration, "deliveryReadItemsOrThrow"),
  extractFunction(integration, "mergeDeliveryReadSuccess"),
  extractFunction(integration, "hydrateDeliveryList")
].join("\n");
let state;
let canonicalHydrationEpoch;
let canonicalSessionEpoch;
let merges;
let resolveRequest;
let rejectRequest;
let polling;
const window = { location: { pathname: "/jobs" } };
function base() { return state; }
function merge(next) { merges.push(next); state = { ...state, ...next }; }
async function api() { return new Promise((resolve, reject) => { resolveRequest = resolve; rejectRequest = reject; }); }
function scheduleJobPolling() { polling += 1; }
eval(runtime);

function reset() {
  canonicalHydrationEpoch = 7;
  canonicalSessionEpoch = 11;
  state = {
    path: "/jobs",
    bridge: { available: true },
    session: { authenticated: true },
    jobs: [{ id: "job-old", status: "processing" }],
    pageStates: { "/jobs": "read_only" }
  };
  merges = [];
  polling = 0;
  resolveRequest = null;
  rejectRequest = null;
}

function mutate(dimension) {
  if (dimension === "request") canonicalHydrationEpoch += 1;
  if (dimension === "session") canonicalSessionEpoch += 1;
  if (dimension === "route") state = { ...state, path: "/assets" };
  if (dimension === "bridge") state = { ...state, bridge: { available: false } };
  if (dimension === "auth") state = { ...state, session: { authenticated: false } };
}

async function staleCase(dimension, reject) {
  reset();
  const requestEpoch = canonicalHydrationEpoch;
  const sessionEpoch = canonicalSessionEpoch;
  const expectedPath = "/jobs";
  const isCurrent = () => canonicalRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath);
  const pending = hydrateDeliveryList("jobs", expectedPath, "Job Center", isCurrent);
  assert(merges.length === 1 && state.jobsReadState === "loading" && state.jobs.length === 0, `${dimension} did not enter loading before request`);
  mutate(dimension);
  if (reject) rejectRequest(new Error(`late-${dimension}`));
  else resolveRequest({ data: { items: [{ id: `job-${dimension}`, status: "completed" }] } });
  const value = await pending;
  return { value, merges: merges.length, readState: state.jobsReadState, jobs: state.jobs.length, polling };
}

(async () => {
  const receipts = {};
  for (const dimension of ["request", "session", "route", "bridge", "auth"]) {
    receipts[`${dimension}Success`] = await staleCase(dimension, false);
    receipts[`${dimension}Failure`] = await staleCase(dimension, true);
  }
  for (const [name, receipt] of Object.entries(receipts)) {
    assert(receipt.value === null, `${name} did not return inert null`);
    assert(receipt.merges === 1, `${name} performed a stale terminal merge`);
    assert(receipt.readState === "loading" && receipt.jobs === 0, `${name} changed current loading projection`);
    assert(receipt.polling === 0, `${name} scheduled stale polling`);
  }
  process.stdout.write(JSON.stringify({ dimensions: Object.keys(receipts) }));
})().catch((error) => { process.stderr.write(error.stack || String(error)); process.exit(1); });
''',
        INTEGRATION,
    )
    assert result["dimensions"] == [
        "requestSuccess",
        "requestFailure",
        "sessionSuccess",
        "sessionFailure",
        "routeSuccess",
        "routeFailure",
        "bridgeSuccess",
        "bridgeFailure",
        "authSuccess",
        "authFailure",
    ]
