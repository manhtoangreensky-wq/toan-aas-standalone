import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const portalJs = fs.readFileSync("static/portal/portal.js", "utf8");
const integrationJs = fs.readFileSync("static/portal/integration.js", "utf8");

function extractFunction(src, fnName) {
  const pattern = new RegExp(`(?:async\\s+)?function\\s+${fnName}\\s*\\(`);
  const match = src.match(pattern);
  if (!match) throw new Error(`Function ${fnName} not found in source`);
  const startIdx = match.index;
  const openBrace = src.indexOf("{", startIdx);
  let depth = 1;
  let i = openBrace + 1;
  while (depth > 0 && i < src.length) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") depth--;
    i++;
  }
  return src.slice(startIdx, i);
}

function extractActionBlock(src, actionName) {
  const startPattern = `if (action === "${actionName}")`;
  const startIdx = src.indexOf(startPattern);
  if (startIdx === -1) throw new Error(`Action block ${actionName} not found`);
  const openBrace = src.indexOf("{", startIdx);
  let depth = 1;
  let i = openBrace + 1;
  while (depth > 0 && i < src.length) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") depth--;
    i++;
  }
  return src.slice(startIdx, i);
}

const manualTopupMethodHasCanonicalQrCode = extractFunction(portalJs, "manualTopupMethodHasCanonicalQr");
const renderManualTopupGuideCode = extractFunction(portalJs, "renderManualTopupGuide");
const hydratePaymentOptionsCode = extractFunction(integrationJs, "hydratePaymentOptions");

function createPortalVm(initialTransient = {}) {
  let transient = { ...initialTransient };
  const sandbox = {
    transientFormValues: () => transient,
    setTransient: (next) => { transient = { ...next }; },
    safeText: (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"),
    manualTopupText: (k, fb) => fb,
    uiText: (k, fb) => fb,
    manualTopupStatusLabel: (s) => s || "",
    adminNumber: (n, s) => String(n) + (s || ""),
    renderManualTopupRecord: () => "",
    canonicalCatalogCode: (s) => (typeof s === "string" ? s.trim() : ""),
    canonicalShortText: (s, l) => (typeof s === "string" ? s.slice(0, l) : "")
  };
  const context = vm.createContext(sandbox);
  vm.runInContext(manualTopupMethodHasCanonicalQrCode, context);
  vm.runInContext(renderManualTopupGuideCode, context);
  return context;
}

test("Case 1: options-state failed renders reload metadata action, not history-only action", () => {
  const portalContext = createPortalVm({ topup_lane: "manual" });
  const appState = {
    paymentOptionsReadState: "failed",
    paymentOptions: {},
    manualTopupReadState: "ready",
    manualTopupHistory: [],
    manualTopupFlow: { status: "form" }
  };
  const html = portalContext.renderManualTopupGuide(appState);
  assert.match(html, /data-manual-topup-state="failed"/);
  assert.match(html, /data-portal-action="payment-options-refresh"/);
  assert.doesNotMatch(html, /data-portal-action="manual-topup-refresh"/);
  assert.match(html, /Tải lại phương thức/);
});

test("Case 2: history failed + options ready/unavailable gives configured/unavailable message, never claims failure to load methods from history state", () => {
  const portalContext = createPortalVm({ topup_lane: "manual" });
  const appState = {
    paymentOptionsReadState: "ready",
    paymentOptions: {
      manual: {
        available: false,
        history_in_web: true,
        methods: []
      }
    },
    manualTopupReadState: "failed",
    manualTopupHistory: [],
    manualTopupFlow: { status: "form" }
  };
  const html = portalContext.renderManualTopupGuide(appState);
  assert.match(html, /data-manual-topup-state="guarded"/);
  assert.match(html, /Nạp thủ công chưa sẵn sàng/);
  assert.doesNotMatch(html, /Chưa lấy được phương thức nạp/);
  assert.doesNotMatch(html, /Chưa lấy được dữ liệu nạp tiền/);
  assert.doesNotMatch(html, /data-portal-action="manual-topup-refresh"/);
});

test("Case 3: metadata hydration: loading->ready for GETsuccess, loading->failed clearing stale options for GETerror, stale-response cannot overwrite new state", async () => {
  const mergedStates = [];
  let currentPath = "/wallet/topup";
  let apiHandler = async () => ({ data: { manual: { methods: [{ id: "bank_acb" }] } } });

  const sandbox = {
    paymentOptionsHydrationEpoch: 0,
    paymentOptionsSessionEpoch: 1,
    currentPortalPath: () => currentPath,
    merge: (obj) => { mergedStates.push(JSON.parse(JSON.stringify(obj))); },
    api: (url) => apiHandler(url),
    safeManualPaymentOptions: (m) => m || {},
    paymentOptionsRequestIsCurrent: (req, sess, path) =>
      req === sandbox.paymentOptionsHydrationEpoch &&
      sess === sandbox.paymentOptionsSessionEpoch &&
      currentPath === path
  };

  const context = vm.createContext(sandbox);
  vm.runInContext(hydratePaymentOptionsCode, context);

  // Subcase 3a: GET success loading -> ready
  await context.hydratePaymentOptions();
  assert.strictEqual(mergedStates.length, 2);
  assert.strictEqual(mergedStates[0].paymentOptionsReadState, "loading");
  assert.deepStrictEqual(mergedStates[0].paymentOptions, {});
  assert.strictEqual(mergedStates[1].paymentOptionsReadState, "ready");
  assert.deepStrictEqual(mergedStates[1].paymentOptions.manual.methods, [{ id: "bank_acb" }]);

  // Subcase 3b: GET error loading -> failed clearing stale options
  mergedStates.length = 0;
  apiHandler = async () => { throw new Error("network down"); };
  await context.hydratePaymentOptions();
  assert.strictEqual(mergedStates.length, 2);
  assert.strictEqual(mergedStates[0].paymentOptionsReadState, "loading");
  assert.deepStrictEqual(mergedStates[0].paymentOptions, {});
  assert.strictEqual(mergedStates[1].paymentOptionsReadState, "failed");
  assert.deepStrictEqual(mergedStates[1].paymentOptions, {});

  // Subcase 3c: Stale-response cannot overwrite new state
  mergedStates.length = 0;
  let finishLateRequest;
  const latePromise = new Promise((resolve) => { finishLateRequest = resolve; });
  apiHandler = async () => latePromise;
  const inflight = context.hydratePaymentOptions();
  currentPath = "/account"; // route diverted before response returns
  finishLateRequest({ data: { manual: { methods: [{ id: "stale" }] } } });
  await inflight;
  assert.strictEqual(mergedStates.length, 1);
  assert.strictEqual(mergedStates[0].paymentOptionsReadState, "loading");
  assert.deepStrictEqual(mergedStates[0].paymentOptions, {});
});

test("Case 4: dedicated action payment-options-refresh issues only hydratePaymentOptions, never hydrateManualTopupHistory/POST and honors route guard", async () => {
  const actionBlock = extractActionBlock(integrationJs, "payment-options-refresh");
  let hydratePaymentOptionsCalls = 0;
  let hydrateManualTopupHistoryCalls = 0;
  let postCalls = 0;
  const busyCalls = [];
  let currentPath = "/wallet/topup";

  const sandbox = {
    manualTopupText: (k, fb) => fb,
    currentPortalPath: () => currentPath,
    setActionBusy: (act, rt, busy) => { busyCalls.push({ act, rt, busy }); },
    hydratePaymentOptions: async () => { hydratePaymentOptionsCalls++; },
    hydrateManualTopupHistory: async () => { hydrateManualTopupHistoryCalls++; },
    api: async (url, opts) => {
      if (opts && opts.method === "POST") postCalls++;
    }
  };

  const context = vm.createContext(sandbox);
  vm.runInContext(`async function dispatchAction(action, route) {\n${actionBlock}\n}`, context);

  // Route guard failure (route mismatch)
  await assert.rejects(
    async () => { await context.dispatchAction("payment-options-refresh", "/account"); },
    /Chưa thể xử lý/
  );

  // Route guard failure (path mismatch)
  currentPath = "/account";
  await assert.rejects(
    async () => { await context.dispatchAction("payment-options-refresh", "/wallet/topup"); },
    /Chưa thể xử lý/
  );
  currentPath = "/wallet/topup";

  // Successful action dispatch
  await context.dispatchAction("payment-options-refresh", "/wallet/topup");
  assert.strictEqual(hydratePaymentOptionsCalls, 1);
  assert.strictEqual(hydrateManualTopupHistoryCalls, 0);
  assert.strictEqual(postCalls, 0);
  assert.deepStrictEqual(busyCalls, [
    { act: "payment-options-refresh", rt: "/wallet/topup", busy: true },
    { act: "payment-options-refresh", rt: "/wallet/topup", busy: false }
  ]);
});

test("Case 5: ACB variants: bothready prefersVietQR; VietQRblocked/bankready usesbank; onlybank; previously selected readybank remainsbank; missing/unavailable remains disabled", () => {
  const portalContext = createPortalVm({ topup_lane: "manual" });
  const acbVietQr = { id: "bank_acb_vietqr", label: "ACB VietQR", currency: "VND" };
  const acbBank = { id: "bank_acb", label: "ACB Ngân hàng", currency: "VND" };
  const otherMethod = { id: "usdt_trc20", label: "USDT TRC20", currency: "VND" };

  const readyVietQrDest = { request_enabled: true, qr_url: "/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr" };
  const blockedVietQrDest = { request_enabled: false, qr_url: "/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr" };
  const readyBankDest = { request_enabled: true, qr_url: "/api/v1/payments/options/manual-methods/bank_acb/qr" };
  const blockedBankDest = { request_enabled: false, qr_url: "/api/v1/payments/options/manual-methods/bank_acb/qr" };
  const readyOtherDest = { request_enabled: true, qr_url: "/api/v1/payments/options/manual-methods/usdt_trc20/qr" };

  function render(methods, destinations, selected = "") {
    portalContext.setTransient({ topup_lane: "manual", method: selected });
    return portalContext.renderManualTopupGuide({
      paymentOptionsReadState: "ready",
      paymentOptions: {
        manual: {
          available: true,
          history_in_web: true,
          methods,
          payment_destinations: destinations
        }
      },
      manualTopupReadState: "ready",
      manualTopupFlow: { status: "form" },
      manualTopupHistory: []
    });
  }

  // 1. bothready prefersVietQR
  const htmlBoth = render([acbVietQr, acbBank], { bank_acb_vietqr: readyVietQrDest, bank_acb: readyBankDest });
  assert.match(htmlBoth, /value="bank_acb_vietqr"/);
  assert.doesNotMatch(htmlBoth, /value="bank_acb"/);

  // 2. VietQRblocked/bankready usesbank
  const htmlBlockedVietQr = render([acbVietQr, acbBank], { bank_acb_vietqr: blockedVietQrDest, bank_acb: readyBankDest });
  assert.match(htmlBlockedVietQr, /value="bank_acb"/);
  assert.doesNotMatch(htmlBlockedVietQr, /value="bank_acb_vietqr"/);

  // 3. onlybank
  const htmlOnlyBank = render([acbBank], { bank_acb: readyBankDest });
  assert.match(htmlOnlyBank, /value="bank_acb"/);
  assert.doesNotMatch(htmlOnlyBank, /value="bank_acb_vietqr"/);

  // 4. previously selected readybank remainsbank
  const htmlSelectedBank = render([acbVietQr, acbBank], { bank_acb_vietqr: readyVietQrDest, bank_acb: readyBankDest }, "bank_acb");
  assert.match(htmlSelectedBank, /value="bank_acb"[^>]*selected/);
  assert.doesNotMatch(htmlSelectedBank, /value="bank_acb_vietqr"/);

  // 5. missing/unavailable remains disabled
  const htmlBothBlocked = render([acbVietQr, acbBank, otherMethod], { bank_acb_vietqr: blockedVietQrDest, bank_acb: blockedBankDest, usdt_trc20: readyOtherDest });
  assert.match(htmlBothBlocked, /value="bank_acb_vietqr"[^>]*disabled/);
  assert.doesNotMatch(htmlBothBlocked, /value="bank_acb"/);
});
