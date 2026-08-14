"""Executable Portal contracts for private Support Desk reply receipts.

The Node harness executes the real ``handleAction`` from ``integration.js``.
It only controls the browser transport and signed GET responses, which keeps
the test about real retry and hydration sequencing rather than a duplicate
JavaScript implementation in Python.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "static" / "portal" / "integration.js"
PORTAL = ROOT / "static" / "portal" / "portal.js"


# One independent contract violation per response: the real Node/vm handler,
# rather than a Python copy of its validator, must fail closed on each one.
MALFORMED_200_RECEIPT_SCENARIOS = (
    "malformed_extra_envelope",
    "malformed_missing_ok",
    "malformed_wrong_type_ok",
    "malformed_substituted_ok",
    "malformed_missing_status",
    "malformed_wrong_type_status",
    "malformed_substituted_status",
    "malformed_missing_message",
    "malformed_wrong_type_message",
    "malformed_substituted_message",
    "malformed_missing_data",
    "malformed_wrong_type_data",
    "malformed_substituted_data",
    "malformed_non_object_data",
    "malformed_array_data",
    "malformed_extra_data",
    "malformed_missing_receipt",
    "malformed_missing_error_code",
    "malformed_wrong_type_error_code",
    "malformed_substituted_error_code",
    "malformed_extra_receipt",
    "malformed_missing_case_id",
    "malformed_wrong_type_case_id",
    "malformed_invalid_case_id",
    "malformed_missing_revision",
    "malformed_wrong_type_revision",
    "malformed_invalid_revision",
    "malformed_wrong_revision",
    "malformed_missing_state",
    "malformed_wrong_type_state",
    "malformed_invalid_state",
    "malformed_unexpected_state",
    "malformed_missing_visibility",
    "malformed_wrong_type_visibility",
    "malformed_invalid_visibility",
    "malformed_wrong_visibility",
    "malformed_missing_action",
    "malformed_wrong_type_action",
    "malformed_invalid_action",
    "malformed_wrong_action",
    "malformed_missing_created_at",
    "malformed_wrong_type_created_at",
    "malformed_invalid_timestamp",
    "malformed_missing_delivery",
    "malformed_wrong_type_delivery",
    "malformed_invalid_delivery",
    "malformed_top_level_null",
    "malformed_top_level_array",
    "malformed_top_level_string",
)


def _run_node_to_temporary_output(arguments: list[str], *, timeout: int) -> tuple[int, str]:
    """Avoid inherited console-pipe defects in the Windows desktop runner."""
    descriptor, raw_path = tempfile.mkstemp(prefix="support-reply-receipt-node-", suffix=".log")
    os.close(descriptor)
    output_path = Path(raw_path)
    try:
        with output_path.open("w", encoding="utf-8") as output:
            result = subprocess.run(
                arguments,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
                text=True,
                timeout=timeout,
            )
        return result.returncode, output_path.read_text(encoding="utf-8")
    except OSError as exc:
        pytest.skip(f"Node subprocess is unavailable in this test runner: {exc}")
    finally:
        output_path.unlink(missing_ok=True)


def _run_reply_action_matrix() -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to execute the real Support reply handlers")

    script = r'''
const fs = require("fs");
const vm = require("vm");
const sourcePath = process.argv[1];
const portalSourcePath = process.argv[2];
let source = fs.readFileSync(sourcePath, "utf8");
const portalSource = fs.readFileSync(portalSourcePath, "utf8");
const discardMarker = "if (entry && submissions.get(scope) === entry) submissions.delete(scope);";
if (!source.includes(discardMarker)) throw new Error("Support submission discard marker was not found");
source = source.replace(discardMarker, `if (entry && submissions.get(scope) === entry) {
  globalThis.__supportReceiptDiscardEvents.push({
    scope,
    customer_detail: JSON.parse(JSON.stringify(base().supportCaseDetail || {})),
    admin_detail: JSON.parse(JSON.stringify(base().supportAdminCaseDetail || {}))
  });
  submissions.delete(scope);
}`);
const closing = "}());";
const position = source.lastIndexOf(closing);
if (position < 0) throw new Error("Portal integration closure was not found");
source = source.slice(0, position)
  + "\nglobalThis.__supportReceiptHarness = {"
  + " handleAction,"
  + " projection: typeof supportReplyReceiptProjection === 'function' ? supportReplyReceiptProjection : null,"
  + " hydrate,"
  + " synchronizePortalHistoryNavigation,"
  + " submission: (scope) => { const entry = submissions.get(scope); return entry && { key: entry.key, inFlight: entry.inFlight }; },"
  + " state: () => base()"
  + "};\n"
  + source.slice(position);

const noop = () => {};
const document = {
  readyState: "loading",
  visibilityState: "visible",
  addEventListener: noop,
  removeEventListener: noop,
  querySelector: () => null,
  querySelectorAll: () => [],
  getElementById: () => null,
  createElement: () => ({ style: {}, dataset: {}, setAttribute: noop, removeAttribute: noop, appendChild: noop, remove: noop }),
  body: { appendChild: noop },
  documentElement: { dataset: {} }
};
const window = {
  addEventListener: noop,
  removeEventListener: noop,
  dispatchEvent: noop,
  clearTimeout: noop,
  clearInterval: noop,
  setTimeout: () => 0,
  setInterval: () => 0,
  location: { pathname: "/", search: "" },
  history: { pushState: noop, replaceState: noop },
  crypto: { getRandomValues: (bytes) => { for (let index = 0; index < bytes.length; index += 1) bytes[index] = index + 1; return bytes; } },
  document,
  navigator: {},
  caches: null,
  isSecureContext: true
};
class Element {}
class HTMLInputElement extends Element {}
class HTMLSelectElement extends Element {}
class HTMLButtonElement extends Element {}
class HTMLFormElement extends Element {}
class Headers {
  constructor(initial) { this.values = new Map(Object.entries(initial || {})); }
  set(key, value) { this.values.set(String(key), String(value)); }
}
const context = {
  window, document, console, URL, URLSearchParams, Headers,
  crypto: window.crypto, HTMLElement: Element, HTMLInputElement, HTMLSelectElement, HTMLButtonElement, HTMLFormElement,
  Event: class Event {}, CustomEvent: class CustomEvent {}, FormData: class FormData {},
  setTimeout: window.setTimeout, clearTimeout: window.clearTimeout,
  setInterval: window.setInterval, clearInterval: window.clearInterval,
  TextEncoder, TextDecoder
};
vm.createContext(context);
context.__supportReceiptDiscardEvents = [];

let active = null;
let sentKey = "";
let fetchCalls = [];
const CASE_ID = "8a0d55e2-2287-4387-8bd1-3774a56f023f";
const OTHER_CASE_ID = "9b0d55e2-2287-4387-8bd1-3774a56f023f";
const WHEN = "2026-08-14T12:00:00+00:00";

function response(status, payload) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

function safeCase(id, revision, state) {
  return {
    id, category: "image_error", priority: "normal", state, revision,
    subject: "Case title remains in the authoritative GET only",
    excerpt: "",
    detail: "The current owner-scoped case has its own private detail.",
    created_at: WHEN, updated_at: WHEN, last_public_message_at: WHEN,
    resolved_at: null, closed_at: null
  };
}

function customerDetail(id, revision, state) {
  return {
    ok: true, status: "read_only", message: "", error_code: null,
    data: {
      delivery: "web_view_only", case: safeCase(id, revision, state),
      messages: [{ id, author_role: "customer", visibility: "public", body: "Authoritative message from GET only.", created_at: WHEN }],
      events: [], attachments: [], resolution_feedback: null
    }
  };
}

function adminDetail(id, revision, state) {
  return {
    ok: true, status: "read_only", message: "", error_code: null,
    data: {
      delivery: "web_view_only", case: safeCase(id, revision, state),
      messages: [], events: [], attachments: [], care_history: []
    }
  };
}

function customerReplyInitialState() {
  if (active && !active.admin && active.kind === "customer_waiting_user_reply") return "waiting_user";
  if (active && !active.admin && active.kind === "customer_resolved_reply") return "resolved";
  return "new";
}

function preservedInternalState(kind) {
  if (kind === "valid_internal_reviewing") return "reviewing";
  if (kind === "valid_internal_waiting_user") return "waiting_user";
  return "";
}

function internalReplyWithoutNextState(kind) {
  return Boolean(preservedInternalState(kind) || [
    "missing_internal_detail", "stale_internal_detail_case",
    "stale_internal_detail_revision", "invalid_internal_detail_state"
  ].includes(kind));
}

function replyReceipt(admin) {
  const preservedState = preservedInternalState(active && active.kind);
  const internal = Boolean(admin && active && (active.kind === "valid_internal" || internalReplyWithoutNextState(active.kind)));
  const unexpectedState = Boolean(active && active.kind === "malformed_unexpected_state");
  const customerState = ["customer_waiting_user_reply", "customer_resolved_reply"].includes(active && active.kind) ? "reviewing" : "new";
  return {
    case_id: CASE_ID,
    revision: 2,
    state: unexpectedState ? (admin ? "new" : "waiting_user") : (admin ? (internal ? (preservedState || "new") : "waiting_user") : customerState),
    visibility: internal ? "internal" : "public",
    action: admin ? "operator_reply" : "customer_reply",
    created_at: WHEN,
    delivery: "web_view_only"
  };
}

function malformedReplyEnvelope(admin, kind) {
  const receipt = replyReceipt(admin);
  const envelope = { ok: true, status: "completed", message: "accepted", error_code: null, data: { receipt } };
  if (kind === "malformed_extra_envelope") { envelope.extra = true; return envelope; }
  if (kind === "malformed_missing_ok") { delete envelope.ok; return envelope; }
  if (kind === "malformed_wrong_type_ok") { envelope.ok = "true"; return envelope; }
  if (kind === "malformed_substituted_ok") { envelope.ok = false; return envelope; }
  if (kind === "malformed_missing_status") { delete envelope.status; return envelope; }
  if (kind === "malformed_wrong_type_status") { envelope.status = 200; return envelope; }
  if (kind === "malformed_substituted_status") { envelope.status = "guarded"; return envelope; }
  if (kind === "malformed_missing_message") { delete envelope.message; return envelope; }
  if (kind === "malformed_wrong_type_message") { envelope.message = {}; return envelope; }
  if (kind === "malformed_substituted_message") { envelope.message = "rejected"; return envelope; }
  if (kind === "malformed_missing_data") { delete envelope.data; return envelope; }
  if (kind === "malformed_wrong_type_data") { envelope.data = "receipt"; return envelope; }
  if (kind === "malformed_substituted_data") { envelope.data = {}; return envelope; }
  if (kind === "malformed_non_object_data") { envelope.data = null; return envelope; }
  if (kind === "malformed_array_data") { envelope.data = [receipt]; return envelope; }
  if (kind === "malformed_extra_data") return { ok: true, status: "completed", message: "accepted", error_code: null, data: { receipt, extra: true } };
  if (kind === "malformed_missing_receipt") { envelope.data = {}; return envelope; }
  if (kind === "malformed_missing_error_code") { delete envelope.error_code; return envelope; }
  if (kind === "malformed_wrong_type_error_code") { envelope.error_code = {}; return envelope; }
  if (kind === "malformed_substituted_error_code") { envelope.error_code = "REJECTED"; return envelope; }
  if (kind === "malformed_extra_receipt") receipt.extra = true;
  if (kind === "malformed_missing_case_id") delete receipt.case_id;
  if (kind === "malformed_wrong_type_case_id") receipt.case_id = 17;
  if (kind === "malformed_invalid_case_id") receipt.case_id = "not-a-case-id";
  if (kind === "malformed_wrong_action") receipt.action = admin ? "customer_reply" : "operator_reply";
  if (kind === "malformed_missing_action") delete receipt.action;
  if (kind === "malformed_wrong_type_action") receipt.action = 17;
  if (kind === "malformed_invalid_action") receipt.action = "case_comment";
  if (kind === "malformed_wrong_visibility") receipt.visibility = "internal";
  if (kind === "malformed_missing_visibility") delete receipt.visibility;
  if (kind === "malformed_wrong_type_visibility") receipt.visibility = 17;
  if (kind === "malformed_invalid_visibility") receipt.visibility = "private";
  if (kind === "malformed_missing_revision") delete receipt.revision;
  if (kind === "malformed_wrong_type_revision") receipt.revision = "2";
  if (kind === "malformed_wrong_revision") receipt.revision = 3;
  if (kind === "malformed_invalid_revision") receipt.revision = 0;
  if (kind === "malformed_missing_state") delete receipt.state;
  if (kind === "malformed_wrong_type_state") receipt.state = 17;
  if (kind === "malformed_invalid_timestamp") receipt.created_at = "not-an-rfc3339-time";
  if (kind === "malformed_missing_created_at") delete receipt.created_at;
  if (kind === "malformed_wrong_type_created_at") receipt.created_at = 17;
  if (kind === "malformed_invalid_state") receipt.state = "provider_delivery";
  if (kind === "malformed_missing_delivery") delete receipt.delivery;
  if (kind === "malformed_wrong_type_delivery") receipt.delivery = 17;
  if (kind === "malformed_invalid_delivery") receipt.delivery = "telegram";
  return envelope;
}

context.fetch = async (url, options) => {
  const path = String(url).replace(/^.*\/api\/v1/, "");
  const method = String(options && options.method || "GET").toUpperCase();
  fetchCalls.push({ path, method });
  const admin = Boolean(active && active.admin);
  if (active && (active.kind === "route_lifecycle" || active.kind === "session_lifecycle")) {
    if (path === "/catalog") return response(200, { ok: true, data: { features: [], menu_capabilities: [] } });
    if (path === "/core/status") return response(200, { ok: true, data: { flags: {} } });
    if (path === "/auth/me") return response(200, { ok: true, data: {} });
    if (path === "/auth/providers") return response(200, { ok: true, data: { providers: {} } });
    if (path === "/auth/telegram/connection/status") return response(200, { ok: true, data: {} });
  }
  if (path.endsWith("/reply")) {
    const body = JSON.parse(String(options && options.body || "{}"));
    sentKey = String(body.idempotency_key || "");
    if (active.kind === "network") throw new Error("network interrupted before a response");
    if (active.kind === "server_5xx") return response(503, { ok: false, status: "failed", message: "server unavailable", data: {}, error_code: "SERVER_UNAVAILABLE" });
    if (active.kind === "guarded") return response(200, { ok: false, status: "guarded", message: "reply guarded", data: {}, error_code: "WEB_SUPPORT_GUARDED" });
    if (active.kind === "malformed_top_level_null") return response(200, null);
    if (active.kind === "malformed_top_level_array") return response(200, []);
    if (active.kind === "malformed_top_level_string") return response(200, "accepted");
    if (active.kind.startsWith("malformed_")) return response(200, malformedReplyEnvelope(admin, active.kind));
    return response(200, { ok: true, status: "completed", message: "accepted", error_code: null, data: { receipt: replyReceipt(admin) } });
  }

  if (admin && path === "/support/admin/summary") {
    return response(200, { ok: true, status: "read_only", message: "", error_code: null, data: { operator_role: "operator" } });
  }
  if (admin && path.startsWith("/support/admin/cases/")) {
    if (active.kind === "hydrate_malformed") return response(200, { ok: true, status: "read_only", message: "", error_code: null, data: {} });
    if (active.kind === "route_stale") { window.location.pathname = "/admin/support/" + OTHER_CASE_ID; window.__TOAN_AAS_PORTAL__.path = window.location.pathname; }
    if (active.kind === "session_stale") window.__TOAN_AAS_PORTAL__.session = { authenticated: false, csrfToken: "" };
    const id = active.kind === "case_mismatch" ? OTHER_CASE_ID : CASE_ID;
    const revision = active.kind === "revision_mismatch" ? 3 : 2;
    const state = active.kind === "state_mismatch" ? "reviewing" : replyReceipt(true).state;
    return response(200, adminDetail(id, revision, state));
  }
  if (admin && path === "/support/admin/care/queues") {
    return response(503, { ok: false, status: "guarded", message: "", error_code: "GUARDED", data: {} });
  }
  if (!admin && path.startsWith("/support/cases/") && path.endsWith("/triage")) {
    return response(503, { ok: false, status: "guarded", message: "", error_code: "GUARDED", data: {} });
  }
  if (!admin && path.startsWith("/support/cases/")) {
    if (active.kind === "hydrate_malformed") return response(200, { ok: true, status: "read_only", message: "", error_code: null, data: {} });
    if (active.kind === "route_stale") { window.location.pathname = "/tickets/" + OTHER_CASE_ID; window.__TOAN_AAS_PORTAL__.path = window.location.pathname; }
    if (active.kind === "session_stale") window.__TOAN_AAS_PORTAL__.session = { authenticated: false, csrfToken: "" };
    const id = active.kind === "case_mismatch" ? OTHER_CASE_ID : CASE_ID;
    const revision = active.kind === "revision_mismatch" ? 3 : 2;
    const state = active.kind === "state_mismatch" ? "reviewing" : replyReceipt(false).state;
    return response(200, customerDetail(id, revision, state));
  }
  throw new Error("unexpected fetch path " + path);
};

vm.runInContext(source, context, { filename: sourcePath });
const harness = context.__supportReceiptHarness;
if (!harness || typeof harness.handleAction !== "function") throw new Error("Support receipt harness was not captured");
const renderStart = portalSource.indexOf("function renderSupportReplyReceipt");
let renderSupportReplyReceipt = () => "";
if (renderStart >= 0) {
  const renderEnd = portalSource.indexOf("\n  function ", renderStart + 1);
  if (renderEnd < 0) throw new Error("Support receipt renderer end was not captured");
  renderSupportReplyReceipt = new Function("safeText", `${portalSource.slice(renderStart, renderEnd)}\nreturn renderSupportReplyReceipt;`)(
    (value) => String(value === undefined || value === null ? "" : value).replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character])
  );
}

async function run(kind, admin, reuseState) {
  active = { kind, admin };
  sentKey = "";
  fetchCalls = [];
  context.__supportReceiptDiscardEvents = [];
  const route = admin ? "/admin/support/" + CASE_ID : "/tickets/" + CASE_ID;
  const capability = admin ? "support-admin-case-reply" : "support-case-reply";
  const receiptField = admin ? "supportAdminReplyReceipt" : "supportCustomerReplyReceipt";
  const preservedState = admin ? preservedInternalState(kind) : "";
  const internalWithoutNextState = Boolean(admin && internalReplyWithoutNextState(kind));
  const internal = Boolean(admin && (kind === "valid_internal" || internalWithoutNextState));
  const customerTransition = !admin && ["customer_waiting_user_reply", "customer_resolved_reply"].includes(kind);
  if (!reuseState) {
    window.location.pathname = route;
    window.__TOAN_AAS_PORTAL__ = {
      path: route,
      session: { authenticated: true, csrfToken: "csrf" },
      supportDeskEnabled: true,
      capabilities: { [capability]: true },
      assetVaultEnabled: false,
      supportCaseDetail: customerTransition ? customerDetail(CASE_ID, 1, customerReplyInitialState()).data : {},
      supportAdminCaseDetail: preservedState
        ? adminDetail(CASE_ID, 1, preservedState).data
        : (kind === "stale_internal_detail_case"
          ? adminDetail(OTHER_CASE_ID, 1, "reviewing").data
          : (kind === "stale_internal_detail_revision"
            ? adminDetail(CASE_ID, 2, "reviewing").data
            : (kind === "invalid_internal_detail_state"
              ? adminDetail(CASE_ID, 1, "provider_delivery").data
              : {}))), pageStates: {}
    };
  }
  const scope = admin ? `support:admin:case:${CASE_ID}:reply` : `support:case:${CASE_ID}:reply`;
  await harness.handleAction({ detail: {
    action: admin ? "support-admin-case-reply" : "support-case-reply",
    route,
    supportCaseId: CASE_ID,
    supportCaseRevision: 1,
    fields: admin
      ? { body: "A safe operator reply.", visibility: internal ? "internal" : "public", next_state: internalWithoutNextState ? "" : (internal ? "new" : "waiting_user") }
      : { body: "A safe customer reply." }
  } });
  const entry = harness.submission(scope);
  const state = harness.state();
  const expected = { caseId: CASE_ID, revision: 1, action: admin ? "operator_reply" : "customer_reply", visibility: internal ? "internal" : "public", state: admin ? (internal ? (preservedState || "new") : "waiting_user") : "new" };
  const defaultCustomerNewExpected = { caseId: CASE_ID, revision: 1, action: "customer_reply", visibility: "public" };
  const validEnvelope = { ok: true, status: "completed", message: "accepted", error_code: null, data: { receipt: replyReceipt(admin) } };
  const malformedEnvelope = { ok: true, status: "completed", message: "accepted", error_code: null, data: { receipt: { ...replyReceipt(admin), body: "not allowed" } } };
  return {
    kind, admin, sent_key: sentKey,
    retained_key: entry && entry.key || "",
    in_flight: Boolean(entry && entry.inFlight === true),
    receipt: state[receiptField] || {},
    current_detail: state[admin ? "supportAdminCaseDetail" : "supportCaseDetail"] || {},
    path: window.location.pathname,
    session_authenticated: Boolean(state.session && state.session.authenticated === true),
    fetch_calls: fetchCalls,
    discard_events: context.__supportReceiptDiscardEvents,
    projection_available: typeof harness.projection === "function",
    valid_projection: typeof harness.projection === "function" ? harness.projection(validEnvelope, expected) : null,
    default_customer_new_projection: typeof harness.projection === "function" && !admin ? harness.projection(validEnvelope, defaultCustomerNewExpected) : null,
    malformed_projection: typeof harness.projection === "function" ? harness.projection(malformedEnvelope, expected) : null
  };
}

async function flushLifecycle() {
  for (let index = 0; index < 8; index += 1) await Promise.resolve();
}

async function runResetProof(admin, lifecycle) {
  await run("valid", admin, false);
  const receiptField = admin ? "supportAdminReplyReceipt" : "supportCustomerReplyReceipt";
  const before = harness.state()[receiptField] || {};
  active = { kind: lifecycle, admin };
  fetchCalls = [];
  if (lifecycle === "route_lifecycle") {
    window.location.pathname = admin ? "/admin/support/" + OTHER_CASE_ID : "/tickets/" + OTHER_CASE_ID;
    harness.synchronizePortalHistoryNavigation();
    await flushLifecycle();
  } else if (lifecycle === "session_lifecycle") {
    await harness.hydrate();
  } else {
    throw new Error("unknown lifecycle proof " + lifecycle);
  }
  const after = harness.state()[receiptField] || {};
  const detailField = admin ? "supportAdminCaseDetail" : "supportCaseDetail";
  const currentDetail = harness.state()[detailField] || {};
  return {
    admin, lifecycle,
    had_receipt: Object.keys(before).length > 0,
    receipt_after_lifecycle: after,
    renderer_output: renderSupportReplyReceipt(after, currentDetail.case || {}, admin),
    lifecycle_fetch_calls: fetchCalls,
    current_path: String(harness.state().path || window.location.pathname || "")
  };
}

(async () => {
  const scenarios = ["network", "malformed_extra_envelope", "malformed_missing_ok", "malformed_wrong_type_ok", "malformed_substituted_ok", "malformed_missing_status", "malformed_wrong_type_status", "malformed_substituted_status", "malformed_missing_message", "malformed_wrong_type_message", "malformed_substituted_message", "malformed_missing_data", "malformed_wrong_type_data", "malformed_substituted_data", "malformed_non_object_data", "malformed_array_data", "malformed_extra_data", "malformed_missing_receipt", "malformed_missing_error_code", "malformed_wrong_type_error_code", "malformed_substituted_error_code", "malformed_extra_receipt", "malformed_missing_case_id", "malformed_wrong_type_case_id", "malformed_invalid_case_id", "malformed_missing_revision", "malformed_wrong_type_revision", "malformed_invalid_revision", "malformed_wrong_revision", "malformed_missing_state", "malformed_wrong_type_state", "malformed_invalid_state", "malformed_unexpected_state", "malformed_missing_visibility", "malformed_wrong_type_visibility", "malformed_invalid_visibility", "malformed_wrong_visibility", "malformed_missing_action", "malformed_wrong_type_action", "malformed_invalid_action", "malformed_wrong_action", "malformed_missing_created_at", "malformed_wrong_type_created_at", "malformed_invalid_timestamp", "malformed_missing_delivery", "malformed_wrong_type_delivery", "malformed_invalid_delivery", "malformed_top_level_null", "malformed_top_level_array", "malformed_top_level_string", "server_5xx", "guarded", "hydrate_malformed", "route_stale", "session_stale", "case_mismatch", "revision_mismatch", "state_mismatch", "valid"];
  const results = [];
  for (const admin of [false, true]) {
    for (const kind of scenarios) results.push(await run(kind, admin));
  }
  results.push(await run("customer_waiting_user_reply", false));
  results.push(await run("customer_resolved_reply", false));
  results.push(await run("valid_internal", true));
  results.push(await run("valid_internal_reviewing", true));
  results.push(await run("valid_internal_waiting_user", true));
  for (const kind of ["missing_internal_detail", "stale_internal_detail_case", "stale_internal_detail_revision", "invalid_internal_detail_state"]) {
    results.push(await run(kind, true));
  }
  const resets = [];
  for (const admin of [false, true]) {
    for (const lifecycle of ["route_lifecycle", "session_lifecycle"]) resets.push(await runResetProof(admin, lifecycle));
  }
  results.push({ reset_proofs: resets });
  process.stdout.write(JSON.stringify(results));
})().catch((error) => { console.error(error && error.stack || error); process.exit(1); });
'''
    returncode, output = _run_node_to_temporary_output([node, "-e", script, str(INTEGRATION), str(PORTAL)], timeout=60)
    assert returncode == 0, output
    return json.loads(output)


def test_reply_handlers_keep_the_retry_key_until_an_exact_current_hydrated_receipt() -> None:
    matrix = _run_reply_action_matrix()
    expected_retry = {
        "network",
        *MALFORMED_200_RECEIPT_SCENARIOS,
        "server_5xx",
        "guarded",
        "hydrate_malformed",
        "route_stale",
        "session_stale",
        "case_mismatch",
        "revision_mismatch",
        "state_mismatch",
    }
    diagnostics = []
    for admin in (False, True):
        surface = "operator" if admin else "customer"
        by_kind = {str(item["kind"]): item for item in matrix if "kind" in item and bool(item.get("admin")) is admin}
        for kind in expected_retry:
            item = by_kind[kind]
            if not item["sent_key"] or item["retained_key"] != item["sent_key"] or item["in_flight"]:
                diagnostics.append({"surface": surface, "kind": kind, "expected": "same retry key retained", "actual": item})
            if item["receipt"]:
                diagnostics.append({"surface": surface, "kind": kind, "expected": "no receipt memory", "actual_receipt": item["receipt"]})
            if item["discard_events"] or item["current_detail"]:
                diagnostics.append({"surface": surface, "kind": kind, "expected": "no receipt commit", "actual_discard_events": item["discard_events"], "actual_detail": item["current_detail"]})

        valid = by_kind["valid"]
        expected_receipt = {
            "case_id": "8a0d55e2-2287-4387-8bd1-3774a56f023f",
            "revision": 2,
            "state": "waiting_user" if admin else "new",
            "visibility": "public",
            "action": "operator_reply" if admin else "customer_reply",
            "created_at": "2026-08-14T12:00:00+00:00",
            "delivery": "web_view_only",
        }
        detail_path = (
            "/support/admin/cases/8a0d55e2-2287-4387-8bd1-3774a56f023f"
            if admin
            else "/support/cases/8a0d55e2-2287-4387-8bd1-3774a56f023f"
        )
        if valid["retained_key"] or valid["in_flight"] or not valid["sent_key"]:
            diagnostics.append({"surface": surface, "kind": "valid", "expected": "submission cleared only after current hydrate", "actual": valid})
        if valid["receipt"] != expected_receipt:
            diagnostics.append({"surface": surface, "kind": "valid", "expected": expected_receipt, "actual_receipt": valid["receipt"]})
        detail_get_indexes = [
            index for index, call in enumerate(valid["fetch_calls"])
            if call == {"path": detail_path, "method": "GET"}
        ]
        reply_post_indexes = [
            index for index, call in enumerate(valid["fetch_calls"])
            if call["path"].endswith("/reply") and call["method"] == "POST"
        ]
        if not detail_get_indexes or not reply_post_indexes or min(detail_get_indexes) <= min(reply_post_indexes):
            diagnostics.append({"surface": surface, "kind": "valid", "expected": "authoritative detail GET after reply receipt", "actual_fetch_calls": valid["fetch_calls"]})
        if not valid["projection_available"] or valid["valid_projection"] != expected_receipt or valid["malformed_projection"] is not None:
            diagnostics.append({"surface": surface, "kind": "projection", "expected": "strict exact receipt validator", "actual": valid})
        if not admin and valid["default_customer_new_projection"] != expected_receipt:
            diagnostics.append({"surface": surface, "kind": "default_customer_new_projection", "expected": expected_receipt, "actual": valid["default_customer_new_projection"]})

        state_mismatch = by_kind["state_mismatch"]
        mismatch_detail_get = any(call == {"path": detail_path, "method": "GET"} for call in state_mismatch["fetch_calls"])
        if not mismatch_detail_get:
            diagnostics.append({"surface": surface, "kind": "state_mismatch", "expected": "authoritative detail GET with mismatched state", "actual_fetch_calls": state_mismatch["fetch_calls"]})

    internal = next(item for item in matrix if bool(item["admin"]) and item["kind"] == "valid_internal")
    expected_internal_receipt = {
        "case_id": "8a0d55e2-2287-4387-8bd1-3774a56f023f",
        "revision": 2,
        "state": "new",
        "visibility": "internal",
        "action": "operator_reply",
        "created_at": "2026-08-14T12:00:00+00:00",
        "delivery": "web_view_only",
    }
    internal_detail_path = "/support/admin/cases/8a0d55e2-2287-4387-8bd1-3774a56f023f"
    if internal["retained_key"] or internal["in_flight"] or internal["receipt"] != expected_internal_receipt:
        diagnostics.append({"surface": "operator", "kind": "valid_internal", "expected": expected_internal_receipt, "actual": internal})
    if not any(call == {"path": internal_detail_path, "method": "GET"} for call in internal["fetch_calls"]):
        diagnostics.append({"surface": "operator", "kind": "valid_internal", "expected": "authoritative internal detail GET", "actual_fetch_calls": internal["fetch_calls"]})

    reset_proofs = next(item["reset_proofs"] for item in matrix if "reset_proofs" in item)
    for proof in reset_proofs:
        if not proof["had_receipt"] or proof["receipt_after_lifecycle"] or proof["renderer_output"] != "":
            diagnostics.append({"surface": "operator" if proof["admin"] else "customer", "kind": f"receipt_reset_{proof['lifecycle']}", "expected": "same-VM route/session lifecycle clears the receipt before any renderer can receive it", "actual": proof})
        if proof["lifecycle"] == "route_lifecycle" and proof["current_path"] == ("/admin/support/8a0d55e2-2287-4387-8bd1-3774a56f023f" if proof["admin"] else "/tickets/8a0d55e2-2287-4387-8bd1-3774a56f023f"):
            diagnostics.append({"surface": "operator" if proof["admin"] else "customer", "kind": "receipt_reset_route_lifecycle", "expected": "real history lifecycle adopts the new route", "actual": proof})
        if proof["lifecycle"] == "session_lifecycle" and not proof["lifecycle_fetch_calls"]:
            diagnostics.append({"surface": "operator" if proof["admin"] else "customer", "kind": "receipt_reset_session_lifecycle", "expected": "real bootstrap lifecycle performs its signed session reads", "actual": proof})
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def test_customer_reply_receipt_matches_waiting_user_and_resolved_transitions() -> None:
    matrix = _run_reply_action_matrix()
    diagnostics = []
    for kind, prior_state in (
        ("customer_waiting_user_reply", "waiting_user"),
        ("customer_resolved_reply", "resolved"),
    ):
        item = next(candidate for candidate in matrix if candidate.get("admin") is False and candidate.get("kind") == kind)
        receipt = item.get("receipt") or {}
        current_case = (item.get("current_detail") or {}).get("case") or {}
        events = item.get("discard_events") or []
        if (
            not item.get("sent_key")
            or item.get("retained_key")
            or item.get("in_flight")
            or receipt.get("state") != "reviewing"
            or receipt.get("revision") != 2
            or current_case.get("state") != "reviewing"
            or current_case.get("revision") != 2
            or len(events) != 1
            or events[0].get("customer_detail") != item.get("current_detail")
        ):
            diagnostics.append({
                "kind": kind,
                "prior_state": prior_state,
                "expected": "valid reviewing receipt rehydrates and clears the retry key",
                "actual": item,
            })
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def test_internal_admin_reply_without_next_state_preserves_authoritative_state() -> None:
    matrix = _run_reply_action_matrix()
    diagnostics = []
    for kind, state in (("valid_internal_reviewing", "reviewing"), ("valid_internal_waiting_user", "waiting_user")):
        item = next(candidate for candidate in matrix if candidate.get("admin") is True and candidate.get("kind") == kind)
        expected_receipt = {
            "case_id": "8a0d55e2-2287-4387-8bd1-3774a56f023f",
            "revision": 2,
            "state": state,
            "visibility": "internal",
            "action": "operator_reply",
            "created_at": "2026-08-14T12:00:00+00:00",
            "delivery": "web_view_only",
        }
        current_case = item.get("current_detail", {}).get("case", {})
        if (
            not item.get("sent_key")
            or item.get("retained_key")
            or item.get("in_flight") is not False
            or item.get("receipt") != expected_receipt
            or current_case.get("revision") != 2
            or current_case.get("state") != state
            or len(item.get("discard_events", [])) != 1
            or item["discard_events"][0].get("admin_detail") != item.get("current_detail")
        ):
            diagnostics.append({"kind": kind, "expected_state": state, "actual": item})
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def test_internal_admin_reply_without_next_state_fails_closed_on_invalid_current_detail() -> None:
    matrix = _run_reply_action_matrix()
    diagnostics = []
    for kind in (
        "missing_internal_detail",
        "stale_internal_detail_case",
        "stale_internal_detail_revision",
        "invalid_internal_detail_state",
    ):
        item = next(candidate for candidate in matrix if candidate.get("admin") is True and candidate.get("kind") == kind)
        reply_calls = [call for call in item.get("fetch_calls", []) if call.get("path", "").endswith("/reply")]
        if (
            item.get("sent_key")
            or item.get("retained_key")
            or item.get("in_flight")
            or item.get("receipt")
            or item.get("discard_events")
            or reply_calls
        ):
            diagnostics.append({"kind": kind, "expected": "reject before reply POST or retry-key acquisition", "actual": item})
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def test_reply_handlers_reject_each_malformed_200_receipt_envelope_without_discarding_retry() -> None:
    matrix = _run_reply_action_matrix()
    diagnostics = []
    for admin in (False, True):
        surface = "operator" if admin else "customer"
        by_kind = {str(item["kind"]): item for item in matrix if "kind" in item and bool(item.get("admin")) is admin}
        for kind in MALFORMED_200_RECEIPT_SCENARIOS:
            item = by_kind[kind]
            if not item["sent_key"] or item["retained_key"] != item["sent_key"] or item["in_flight"]:
                diagnostics.append({"surface": surface, "kind": kind, "expected": "same retry key retained", "actual": item})
            if item["receipt"] or item["discard_events"] or item["current_detail"]:
                diagnostics.append({"surface": surface, "kind": kind, "expected": "no receipt memory or commit", "actual": item})
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def test_reply_handlers_commit_current_authoritative_detail_before_discarding_retry_key() -> None:
    matrix = _run_reply_action_matrix()
    scenarios = (
        (False, "valid", "supportCaseDetail", "customer_detail", "new"),
        (True, "valid", "supportAdminCaseDetail", "admin_detail", "waiting_user"),
        (True, "valid_internal", "supportAdminCaseDetail", "admin_detail", "new"),
    )
    diagnostics = []
    for admin, kind, detail_field, discard_field, expected_state in scenarios:
        item = next(candidate for candidate in matrix if bool(candidate.get("admin")) is admin and candidate.get("kind") == kind)
        events = item["discard_events"]
        if len(events) != 1:
            diagnostics.append({"kind": kind, "expected": "one retry-key discard event", "actual_events": events})
            continue
        authoritative_detail = events[0][discard_field]
        current_case = authoritative_detail.get("case", {})
        if (
            events[0]["scope"] != (f"support:admin:case:8a0d55e2-2287-4387-8bd1-3774a56f023f:reply" if admin else f"support:case:8a0d55e2-2287-4387-8bd1-3774a56f023f:reply")
            or current_case.get("id") != "8a0d55e2-2287-4387-8bd1-3774a56f023f"
            or current_case.get("revision") != 2
            or current_case.get("state") != expected_state
            or authoritative_detail != item["current_detail"]
            or not authoritative_detail.get("messages") == ([] if admin else [{"id": "8a0d55e2-2287-4387-8bd1-3774a56f023f", "author_role": "customer", "visibility": "public", "body": "Authoritative message from GET only.", "created_at": "2026-08-14T12:00:00+00:00"}])
        ):
            diagnostics.append({"kind": kind, "detail_field": detail_field, "expected": "current authoritative detail at retry-key discard", "actual_event": events[0]})
    assert not diagnostics, json.dumps(diagnostics, ensure_ascii=False, indent=2)


def _render_support_reply_receipt(receipt: dict, case_item: dict, admin: bool) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to execute the Support receipt renderer")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function renderSupportReplyReceipt");
if (start < 0) throw new Error("renderSupportReplyReceipt is missing");
const end = source.indexOf("\n  function ", start + 1);
if (end < 0) throw new Error("renderSupportReplyReceipt end is missing");
function safeText(value) { return String(value === undefined || value === null ? "" : value).replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]); }
eval(source.slice(start, end));
process.stdout.write(JSON.stringify({ html: renderSupportReplyReceipt(JSON.parse(process.argv[2]), JSON.parse(process.argv[3]), process.argv[4] === "true") }));
'''
    returncode, output = _run_node_to_temporary_output(
        [node, "-e", script, str(PORTAL), json.dumps(receipt), json.dumps(case_item), str(admin).lower()],
        timeout=30,
    )
    assert returncode == 0, output
    return str(json.loads(output)["html"])


def test_reply_receipt_renderer_is_content_free_aria_live_and_fenced_to_current_case_revision() -> None:
    case_id = "8a0d55e2-2287-4387-8bd1-3774a56f023f"
    receipt = {
        "case_id": case_id,
        "revision": 2,
        "state": "waiting_user",
        "visibility": "public",
        "action": "customer_reply",
        "created_at": "2026-08-14T12:00:00+00:00",
        "delivery": "web_view_only",
        # A renderer must never trust or interpolate an unexpected reply body.
        "body": "RECEIPT-BODY-MUST-NOT-RENDER",
    }
    current_case = {
        "id": case_id,
        "revision": 2,
        "subject": "CASE-SUBJECT-MUST-NOT-RENDER",
        "detail": "CASE-DETAIL-MUST-NOT-RENDER",
        "customer": {"email": "CUSTOMER-EMAIL-MUST-NOT-RENDER"},
    }
    html = _render_support_reply_receipt(receipt, current_case, False)
    assert 'data-support-reply-receipt' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html
    assert "revision 2" in html
    for forbidden in ("RECEIPT-BODY-MUST-NOT-RENDER", "CASE-SUBJECT-MUST-NOT-RENDER", "CASE-DETAIL-MUST-NOT-RENDER", "CUSTOMER-EMAIL-MUST-NOT-RENDER"):
        assert forbidden not in html

    assert _render_support_reply_receipt(receipt, {**current_case, "id": "9b0d55e2-2287-4387-8bd1-3774a56f023f"}, False) == ""
    assert _render_support_reply_receipt(receipt, {**current_case, "revision": 3}, False) == ""

    internal_receipt = {**receipt, "action": "operator_reply", "visibility": "internal", "state": "new"}
    admin_html = _render_support_reply_receipt(internal_receipt, current_case, True)
    assert 'data-support-reply-receipt' in admin_html
    assert 'role="status"' in admin_html
    assert "internal" in admin_html.lower()
    for forbidden in ("RECEIPT-BODY-MUST-NOT-RENDER", "CASE-SUBJECT-MUST-NOT-RENDER", "CASE-DETAIL-MUST-NOT-RENDER", "CUSTOMER-EMAIL-MUST-NOT-RENDER"):
        assert forbidden not in admin_html
