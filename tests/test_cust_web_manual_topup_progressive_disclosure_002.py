"""Tests CUST-WEB-MANUAL-TOPUP-PROGRESSIVE-DISCLOSURE-002.
Verifies progressive disclosure, two-step presentation state,
contrast token usage, isolated local handling, and i18n completeness.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS = ROOT / "static" / "portal" / "portal.js"
PORTAL_CSS = ROOT / "static" / "portal" / "portal.css"
PORTAL_I18N = ROOT / "static" / "portal" / "portal-i18n.js"
def _run_node_script(script_body: str) -> dict:
    node = shutil.which("node")
    assert node, "Node.js is required for Portal tests"
    wrapper = r'''
const fs = require("node:fs"), vm = require("node:vm");
const portalSource = fs.readFileSync(__PORTAL__, "utf8");
const i18nSource = fs.readFileSync(__I18N__, "utf8");

function classList() {
  const values = new Set();
  return {
    add: (...items) => items.forEach((i) => values.add(String(i))),
    remove: (...items) => items.forEach((i) => values.delete(String(i))),
    contains: (i) => values.has(String(i)),
    toggle: (i, force) => {
      const on = force === undefined ? !values.has(String(i)) : Boolean(force);
      if (on) values.add(String(i)); else values.delete(String(i));
      return on;
    }
  };
}

function element(id = "", tagName = "DIV") {
  const attrs = Object.create(null);
  const el = {
    id, tagName: tagName.toUpperCase(), hidden: false, disabled: false,
    innerHTML: "", textContent: "", value: "", parentElement: null,
    dataset: {}, style: {}, classList: classList(), children: [],
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : ""; },
    removeAttribute(k) { delete attrs[k]; },
    hasAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k); },
    querySelector() { return null; }, querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
    appendChild(c) { c.parentElement = this; this.children.push(c); return c; },
    prepend(c) { c.parentElement = this; this.children.unshift(c); return c; },
    remove() {}, focus() {}, reportValidity: () => true, checkValidity: () => true,
    matches(sel) {
      if (!sel) return false;
      const parts = sel.split(",").map((s) => s.trim());
      for (const part of parts) {
        if (part.startsWith(".")) {
          if (this.classList.contains(part.slice(1))) return true;
        } else if (part.startsWith("#")) {
          if (this.id === part.slice(1)) return true;
        } else if (part.startsWith("[")) {
          const m = part.match(/^\[([^=\]]+)(?:=(?:"|')?([^"'\]]+)(?:"|')?)?\]$/);
          if (m) {
            if (m[2] !== undefined) {
              if (this.getAttribute(m[1]) === m[2]) return true;
            } else if (this.hasAttribute(m[1])) return true;
          }
        } else if (this.tagName.toLowerCase() === part.toLowerCase()) {
          return true;
        }
      }
      return false;
    },
    closest(sel) {
      let cur = this;
      while (cur) {
        if (cur.matches && cur.matches(sel)) return cur;
        cur = cur.parentElement;
      }
      return null;
    },
    contains() { return false; },
    set elements(arr) { this._elements = arr; },
    get elements() { return this._elements || []; }
  };
  return el;
}

const listeners = Object.create(null);
const windowListeners = Object.create(null);
const sidebar = element("sidebar"), header = element("header"), main = element("main");
const shell = element("shell"), mobileNav = element("mobile"), palette = element("palette");
const body = element("body"), docEl = element("html");

const document = {
  body, documentElement: docEl, title: "", readyState: "loading", activeElement: null,
  createElement: (tag = "div") => element("", tag),
  addEventListener(t, h) { (listeners[t] ||= []).push(h); },
  removeEventListener() {}, querySelectorAll() { return []; },
  querySelector(sel) {
    if (sel.includes("data-portal-sidebar")) return sidebar;
    if (sel.includes("data-portal-header")) return header;
    if (sel.includes("data-portal-main")) return main;
    if (sel.includes("data-portal-shell")) return shell;
    if (sel.includes("data-portal-mobile-nav")) return mobileNav;
    if (sel.includes("data-portal-command-palette")) return palette;
    return null;
  },
  getElementById() { return null; }
};

const storage = () => ({ getItem: () => null, setItem() {}, removeItem() {} });
const dispatchedActions = [];
const window = {
  __TOAN_AAS_PORTAL__: {},
  location: { pathname: "/wallet/topup", search: "", href: "http://test/wallet/topup" },
  history: { pushState() {}, replaceState() {} }, innerWidth: 1440,
  addEventListener(t, h) { (windowListeners[t] ||= []).push(h); },
  removeEventListener() {},
  dispatchEvent(e) {
    if (e && e.type === "toanaas:portal-action") {
      dispatchedActions.push(e.detail || {});
    }
    return true;
  },
  matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
  setTimeout: () => 1, clearTimeout() {},
  requestAnimationFrame: (cb) => { cb(); return 1; }, cancelAnimationFrame() {},
  scrollTo() {}, localStorage: storage(), sessionStorage: storage(),
  TOANAASPortalMotion: { replace(_s, _m, render) { render(); } }
};

const context = {
  console, process, window, document, Blob,
  navigator: { standalone: false, userAgent: "node", clipboard: { writeText: async () => {} } },
  URL, URLSearchParams, Intl,
  setTimeout: window.setTimeout, clearTimeout: window.clearTimeout,
  requestAnimationFrame: window.requestAnimationFrame, cancelAnimationFrame: window.cancelAnimationFrame,
  CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init && init.detail; },
  Event: function Event(type) { this.type = type; },
  CSS: { escape: (v) => String(v) }
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(i18nSource + "\n" + portalSource, context, { filename: "portal-bundle.js" });

const method = (id, label) => ({ id, label, currency: "VND", mode: "transfer" });
const testPaymentOptions = {
  payos: { request_enabled: false, topup_catalog_available: false, topup_packages: [] },
  manual: {
    available: true, history_in_web: true, payment_code: "10000000", support_hotline: "0898360858",
    methods: [
      method("bank_acb", "ACB"), method("bank_acb_vietqr", "ACB VietQR"),
      method("momo_tuithantai", "MoMo"), method("zalopay_personal", "ZaloPay"),
      method("zalopay_merchant", "ZaloPay Merchant"), method("usdt_trc20", "USDT TRC20")
    ],
    payment_destinations: {
      bank_acb: {
        label: "ACB", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true,
        destination: { bank_code: "ACB", bank_name: "Asia Commercial Bank", account_number: "0387532320", account_owner: "TOAN AAS" }
      },
      bank_acb_vietqr: {
        label: "ACB VietQR", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true,
        qr_url: "/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr",
        destination: { bank_code: "ACB", bank_name: "Asia Commercial Bank", account_number: "0387532320", account_owner: "TOAN AAS" }
      },
      momo_tuithantai: {
        label: "MoMo", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true,
        qr_url: "/api/v1/payments/options/manual-methods/momo_tuithantai/qr",
        destination: { wallet_address: "0898360858" }
      },
      zalopay_personal: {
        label: "ZaloPay", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true,
        qr_url: "/api/v1/payments/options/manual-methods/zalopay_personal/qr",
        destination: { wallet_address: "0898360858" }
      },
      zalopay_merchant: {
        label: "ZaloPay Merchant", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true,
        qr_url: "/api/v1/payments/options/manual-methods/zalopay_merchant/qr",
        destination: { wallet_address: "0898360858" }
      },
      usdt_trc20: {
        label: "USDT TRC20", currency: "USD", mode: "transfer", display_ready: true, request_enabled: false,
        qr_url: "/api/v1/payments/options/manual-methods/usdt_trc20/qr",
        destination: { wallet_address: "TUqyVeoRhBtFvJmQzaKkqrTVRa1ULNj6o5", network: "TRC20" }
      },
      missing_dest: {
        label: "Missing Dest", currency: "VND", mode: "transfer", display_ready: true, request_enabled: true
      }
    }
  }
};

function mountPortal(extraTransient = {}) {
  const currentTransient = context.window.TOANAASPortal.transientFormDrafts
    ? (context.window.TOANAASPortal.transientFormDrafts.get("/wallet/topup") || {})
    : {};
  const merged = { topup_lane: "manual", ...currentTransient, ...extraTransient };
  if (context.window.TOANAASPortal.transientFormDrafts) {
    context.window.TOANAASPortal.transientFormDrafts.set("/wallet/topup", merged);
  }
  window.TOANAASPortal.mount({
    path: "/wallet/topup", interfaceLocale: "vi",
    session: { authenticated: true, account: { id: "web-account" } },
    capabilities: {}, wallet: null,
    paymentOptions: testPaymentOptions,
    manualTopupFlow: { status: "form", data: {} },
    manualTopupHistory: [{
      request_id: "MANUAL-1", status: "pending_admin_review", amount_vnd: 50000,
      method: "bank_acb_vietqr", reference: "HISTORY-REF-SENSITIVE",
      transfer_content: "HISTORY-TRANSFER-10000000"
    }],
    manualTopupReadState: "ready"
  }, { reason: "test" });
}

function confirmManualSelection(methodId, amountValue = "125000") {
  const form = element("confirm-form", "FORM");
  form.setAttribute("data-portal-form", "");
  form.setAttribute("data-portal-route", "/wallet/topup");
  form.setAttribute("data-portal-action", "manual-topup-confirm-selection");
  const amount = element("amount", "INPUT");
  amount.setAttribute("name", "amount_vnd"); amount.value = String(amountValue);
  const methodInput = element("method", "SELECT");
  methodInput.setAttribute("name", "method"); methodInput.value = String(methodId);
  form.appendChild(amount); form.appendChild(methodInput);
  form.elements = [amount, methodInput];
  form.querySelectorAll = () => [amount, methodInput];
  form.querySelector = (selector) => selector.includes("amount_vnd") ? amount : selector.includes("method") ? methodInput : null;
  const button = element("confirm", "BUTTON");
  button.setAttribute("type", "button");
  button.setAttribute("data-portal-action", "manual-topup-confirm-selection");
  button.setAttribute("data-portal-route", "/wallet/topup");
  form.appendChild(button);
  const clickHandler = (listeners.click || [])[0];
  clickHandler({ target: button, preventDefault() {} });
  return main.innerHTML;
}

__TEST_BODY__
'''.replace("__PORTAL__", json.dumps(str(PORTAL_JS))).replace("__I18N__", json.dumps(str(PORTAL_I18N)))

    full_script = wrapper.replace("__TEST_BODY__", script_body)
    proc = subprocess.run([node, "-e", full_script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"Node script failed (exit {proc.returncode}):\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    return json.loads(proc.stdout)


def test_1_renderer_initial_dom_progressive_disclosure():
    """Initial DOM must NOT reveal instructions, QR, code, reference, or final submit."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const html = main.innerHTML;
const leaks = [];
if (html.includes("portal-manual-topup-info")) leaks.push("portal-manual-topup-info");
if (html.includes("portal-manual-payment-methods")) leaks.push("portal-manual-payment-methods");
if (html.includes("data-manual-payment-method")) leaks.push("data-manual-payment-method");
if (/<img[^>]+qr/i.test(html) || html.includes('api/v1/payments/options/manual-methods')) leaks.push("qr_image_or_url");
if (/name=["']reference["']/.test(html)) leaks.push("reference_input");
if (html.includes('data-portal-action="manual-topup-create"')) leaks.push("manual-topup-create");
if (html.includes("HISTORY-REF-SENSITIVE")) leaks.push("history_reference");
if (html.includes("HISTORY-TRANSFER-10000000")) leaks.push("history_transfer_content");
const required = [];
if (!html.includes('name="amount_vnd"')) required.push("name=amount_vnd");
if (!html.includes('name="method"')) required.push("name=method");
if (!html.includes('manual-topup-confirm-selection')) required.push("manual-topup-confirm-selection");
process.stdout.write(JSON.stringify({
  ok: leaks.length === 0 && required.length === 0,
  leaks,
  required,
  has_history: html.includes("MANUAL-1")
}));
'''
    res = _run_node_script(script)
    assert not res["leaks"], f"Initial DOM leaked hidden elements: {res['leaks']}"
    assert not res["required"], f"Initial DOM missing required choose controls: {res['required']}"
    assert res["has_history"] is True, "Production manual history must remain visible"
    assert res["ok"] is True


def test_2_confirm_selection_is_local_handler_rejecting_invalid_inputs():
    """Confirm selection is handled locally in portal.js, does NOT emit ACTION_EVENT or API calls."""
    script = r'''
mountPortal({ topup_lane: "manual" });
// 1. Invalid amount: 0
confirmManualSelection("bank_acb_vietqr", 0);
const postZeroAmountHtml = main.innerHTML;
const zeroOpened = postZeroAmountHtml.includes("portal-manual-payment-method") || postZeroAmountHtml.includes("api/v1/payments/options/manual-methods");
// 2. Invalid amount: negative
confirmManualSelection("bank_acb_vietqr", -50000);
const postNegAmountHtml = main.innerHTML;
const negOpened = postNegAmountHtml.includes("portal-manual-payment-method");
// 3. Missing method
confirmManualSelection("", 100000);
const postEmptyMethodHtml = main.innerHTML;
const emptyMethodOpened = postEmptyMethodHtml.includes("portal-manual-payment-method");
// 4. Request-enabled method without a canonical signed QR
confirmManualSelection("bank_acb", 100000);
const postUnavailableMethodHtml = main.innerHTML;
const unavailOpened = postUnavailableMethodHtml.includes("portal-manual-payment-method");
// 5. Missing destination
confirmManualSelection("missing_dest", 100000);
const postMissingDestHtml = main.innerHTML;
const missingDestOpened = postMissingDestHtml.includes("portal-manual-payment-method");
process.stdout.write(JSON.stringify({
  action_event_count: dispatchedActions.length,
  zeroOpened,
  negOpened,
  emptyMethodOpened,
  unavailOpened,
  missingDestOpened
}));
'''
    res = _run_node_script(script)
    assert res["action_event_count"] == 0, f"Confirm selection must not dispatch ACTION_EVENT, saw: {res['action_event_count']}"
    assert res["zeroOpened"] is False, "Zero amount must not open instructions"
    assert res["negOpened"] is False, "Negative amount must not open instructions"
    assert res["emptyMethodOpened"] is False, "Empty method must not open instructions"
    assert res["unavailOpened"] is False, "Disabled/unavailable method must not open instructions"
    assert res["missingDestOpened"] is False, "Method with missing destination must not open instructions"


def test_3_confirmed_valid_state_renders_single_instruction_signed_qr_and_reconciliation():
    """Confirmed valid state renders only the selected method instruction card + QR + code/hotline + reference + final submit."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const html = confirmManualSelection("bank_acb_vietqr");
const hasSelectedMethod = html.includes('data-manual-payment-method="bank_acb_vietqr"');
const otherMethodLeaked = ["bank_acb", "momo_tuithantai", "zalopay_personal", "zalopay_merchant"]
  .some((id) => html.includes(`data-manual-payment-method="${id}"`));
const hasExactQrUrl = html.includes('/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr');
const hasPaymentCode = html.includes("10000000");
const hasHotline = html.includes("0898360858");
const hasReferenceField = /name=["']reference["']/.test(html);
const hasFinalSubmit = html.includes('data-portal-action="manual-topup-create"');
const hasChangeAction = html.includes('manual-topup-change-selection');
const hasHiddenConfirmedAmount = html.includes('value="125000"');
const hasHiddenConfirmedMethod = html.includes('value="bank_acb_vietqr"');
const hasConfirmedHistoryDetails = html.includes("HISTORY-REF-SENSITIVE") && html.includes("HISTORY-TRANSFER-10000000");

process.stdout.write(JSON.stringify({
  hasSelectedMethod,
  otherMethodLeaked,
  hasExactQrUrl,
  hasPaymentCode,
  hasHotline,
  hasReferenceField,
  hasFinalSubmit,
  hasChangeAction,
  hasHiddenConfirmedAmount,
  hasHiddenConfirmedMethod,
  hasConfirmedHistoryDetails,
  action_event_count: dispatchedActions.length
}));
'''
    res = _run_node_script(script)
    assert res["hasSelectedMethod"] is True, "Confirmed state must render selected method instruction card"
    assert res["otherMethodLeaked"] is False, "Confirmed state must NOT leak unselected method cards"
    assert res["hasExactQrUrl"] is True, "Confirmed state must render exact same-origin signed QR URL"
    assert res["hasPaymentCode"] is True, "Confirmed state must display payment code"
    assert res["hasHotline"] is True, "Confirmed state must display hotline"
    assert res["hasReferenceField"] is True, "Confirmed state must display reference input"
    assert res["hasFinalSubmit"] is True, "Confirmed state must provide final manual-topup-create submit"
    assert res["hasChangeAction"] is True, "Confirmed state must provide change/back action"
    assert res["hasHiddenConfirmedAmount"] is True, "Confirmed form must carry confirmed amount"
    assert res["hasHiddenConfirmedMethod"] is True, "Confirmed form must carry confirmed method"
    assert res["hasConfirmedHistoryDetails"] is True, "History transfer details may render only after explicit confirmation"
    assert res["action_event_count"] == 0, "Confirmation must not emit ACTION_EVENT"


def test_4_change_selection_purges_stale_qr_and_forces_reconfirm():
    """Change/back action removes old QR and instruction from DOM, returning to choose state."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const clickHandler = (listeners.click || [])[0];
const confirmedHtml = confirmManualSelection("bank_acb_vietqr");
const hadQr = confirmedHtml.includes("bank_acb_vietqr/qr");
// Leaving and returning to the manual lane must revoke the confirmation.
const payosBtn = element("payos", "BUTTON");
payosBtn.setAttribute("data-portal-topup-lane", "payos");
clickHandler({ target: payosBtn, preventDefault() {} });
const manualBtn = element("manual", "BUTTON");
manualBtn.setAttribute("data-portal-topup-lane", "manual");
clickHandler({ target: manualBtn, preventDefault() {} });
mountPortal();
const laneReturnHtml = main.innerHTML;
const laneReturnPurged = !laneReturnHtml.includes("bank_acb_vietqr/qr") && !laneReturnHtml.includes('data-portal-action="manual-topup-create"');
// Step 2: click change/back action
const changeBtn = element("change-btn", "BUTTON");
changeBtn.setAttribute("type", "button");
changeBtn.setAttribute("data-portal-action", "manual-topup-change-selection");
changeBtn.setAttribute("data-portal-route", "/wallet/topup");
clickHandler({ target: changeBtn, preventDefault() {} });
const revertedHtml = main.innerHTML;
const oldQrPurged = !revertedHtml.includes("bank_acb_vietqr/qr");
const oldMethodCardPurged = !revertedHtml.includes("data-manual-payment-method");
const oldReferencePurged = !revertedHtml.includes('name="reference"');
const backToConfirmAction = revertedHtml.includes("manual-topup-confirm-selection");
const finalSubmitAbsent = !revertedHtml.includes('data-portal-action="manual-topup-create"');
const unavailableOptionDisabled = revertedHtml.includes('value="momo_tuithantai"') && revertedHtml.includes("disabled");
process.stdout.write(JSON.stringify({
  hadQr,
  laneReturnPurged,
  oldQrPurged,
  oldMethodCardPurged,
  oldReferencePurged,
  backToConfirmAction,
  finalSubmitAbsent,
  unavailableOptionDisabled
}));
'''
    res = _run_node_script(script)
    assert res["hadQr"] is True, "Precondition: QR was present in confirmed state"
    assert res["laneReturnPurged"] is True, "PayOS → Manual must require a fresh explicit confirmation"
    assert res["oldQrPurged"] is True, "Old QR must be purged from DOM on change"
    assert res["oldMethodCardPurged"] is True, "Old method card must be purged from DOM on change"
    assert res["oldReferencePurged"] is True, "Reference input must be removed from DOM on change"
    assert res["backToConfirmAction"] is True, "Change must return to choose form with confirm button"
    assert res["finalSubmitAbsent"] is True, "Final submit button must be absent until reconfirmation"
    assert res["unavailableOptionDisabled"] is True, "Unavailable method options must have disabled attribute"


def test_5_css_manual_topup_uses_aura_semantic_tokens_and_explicit_contrast():
    """Manual CSS must use only Aura semantic tokens, explicit color-scheme, option surfaces, and no forbidden legacy aliases."""
    css = PORTAL_CSS.read_text(encoding="utf-8")

    theme_css = (PORTAL_CSS.parent / "portal-theme.css").read_text(encoding="utf-8")
    manual_start = css.find("/* Manual top-up")
    assert manual_start != -1, "Manual top-up CSS section comment must exist"
    manual_css = css[manual_start:]

    forbidden = ["--portal-text-primary", "--portal-text-secondary", "--portal-surface-card", "--portal-light-placeholder", "--portal-surface-subtle"]
    found_forbidden = [var for var in forbidden if var in manual_css]
    assert not found_forbidden, f"Forbidden legacy aliases found in manual CSS block: {found_forbidden}"

    required_tokens = [
        "--portal-input-surface",
        "--portal-ink",
        "--portal-muted",
        "--portal-border",
        "--portal-surface-soft",
    ]
    missing_tokens = [tok for tok in required_tokens if tok not in manual_css]
    assert not missing_tokens, f"Missing required Aura semantic tokens in manual CSS: {missing_tokens}"

    assert "color-scheme: light" in manual_css, "Manual CSS must declare explicit color-scheme: light"
    assert 'html[data-portal-theme="dark"]' in manual_css, "Manual CSS must scope dark theme rules under html[data-portal-theme='dark']"
    assert "color-scheme: dark" in manual_css, "Dark theme manual scope must declare color-scheme: dark"

    assert re.search(r"\.portal-manual-topup-form\s+option", manual_css), "Manual CSS must style native option elements"

    currency_rule = re.search(r"\.portal-manual-payment-method-copy\s*>\s*span\s*\{(?P<body>.*?)\n\}", manual_css, re.S)
    controls_rule = re.search(r"\.portal-manual-topup-form input,\s*\n\.portal-manual-topup-form select\s*\{(?P<body>.*?)\n\}", manual_css, re.S)
    assert currency_rule and "color: var(--portal-muted)" in currency_rule.group("body")
    assert controls_rule and "border: 1px solid var(--portal-muted)" in controls_rule.group("body")

    light_tokens = dict(re.findall(r"(--portal-[a-zA-Z0-9-]+)\s*:\s*([^;]+);", theme_css[:theme_css.index(':root[data-portal-theme="dark"]')]))

    def token(name: str) -> str:
        value = light_tokens[name].strip()
        seen = {name}
        while match := re.fullmatch(r"var\((--portal-[a-zA-Z0-9-]+)\)", value):
            name = match.group(1)
            assert name not in seen
            seen.add(name)
            value = light_tokens[name].strip()
        return value

    def ratio(first: str, second: str) -> float:
        def luminance(value: str) -> float:
            rgb = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [item / 12.92 if item <= 0.04045 else ((item + 0.055) / 1.055) ** 2.4 for item in rgb]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        low, high = sorted((luminance(first), luminance(second)))
        return (high + 0.05) / (low + 0.05)

    assert ratio(token("--portal-muted"), token("--portal-surface-soft")) >= 4.5
    assert ratio(token("--portal-muted"), token("--portal-input-surface")) >= 3.0

    # Disabled control rules
    assert "--portal-control-disabled-" in manual_css, "Disabled manual controls must use --portal-control-disabled- tokens"
    assert re.search(r":disabled[^{]*{[^}]*opacity:\s*1", manual_css), "Disabled option/control text must use opacity 1 (no opacity reduction)"

    # all var(--portal-*) names referenced in manual block are declared in portal-theme.css
    used_vars = set(re.findall(r"var\((--portal-[^)]+)\)", manual_css))
    declared_vars = set(re.findall(r"(--portal-[a-zA-Z0-9-]+)\s*:", theme_css))
    undeclared = used_vars - declared_vars
    assert not undeclared, f"Undeclared variables used in manual CSS: {undeclared}"

    # Focus outline
    assert "--portal-focus" in manual_css, "Focus outline must use --portal-focus token"

    # Mobile responsive controls
    assert re.search(r"font-size:\s*(?:16px|1rem)", manual_css), "Mobile input font-size must be at least 16px to prevent iOS auto-zoom"
    assert "min-height: 44px" in manual_css or "min-height: 48px" in manual_css, "Interactive controls must satisfy min-height >= 44px"


def test_6_manual_topup_i18n_keysets_exact_and_contain_progressive_disclosure_labels():
    """VI/EN/ZH keysets must be strictly equal and contain progressive disclosure step labels."""
    i18n = PORTAL_I18N.read_text(encoding="utf-8")

    def _get_section(start: str, end: str) -> str:
        left = i18n.index(start)
        right = i18n.index(end, left)
        return i18n[left:right]

    vi_sec = _get_section("Object.assign(MANUAL_TOPUP_MESSAGES.vi, {", "Object.assign(MANUAL_TOPUP_MESSAGES.en, {")
    en_sec = _get_section("Object.assign(MANUAL_TOPUP_MESSAGES.en, {", "Object.assign(MANUAL_TOPUP_MESSAGES.zh, {")
    zh_sec = _get_section("Object.assign(MANUAL_TOPUP_MESSAGES.zh, {", "Object.keys(MESSAGES).forEach")

    vi_keys = set(re.findall(r'"(manualTopup\.[^"]+)"\s*:', vi_sec))
    en_keys = set(re.findall(r'"(manualTopup\.[^"]+)"\s*:', en_sec))
    zh_keys = set(re.findall(r'"(manualTopup\.[^"]+)"\s*:', zh_sec))

    assert vi_keys == en_keys == zh_keys, (
        f"Keyset mismatch: vi-en={vi_keys ^ en_keys}, vi-zh={vi_keys ^ zh_keys}"
    )

    required_new_keys = {
        "manualTopup.confirmSelection",
        "manualTopup.changeSelection",
        "manualTopup.instructionTitle",
        "manualTopup.selectMethodRequired",
    }
    missing = required_new_keys - vi_keys
    assert not missing, f"Missing progressive disclosure keys in MANUAL_TOPUP_MESSAGES: {missing}"

    # Diacritics and localization verification
    assert re.search(r"[À-ỹ]", vi_sec), "Vietnamese messages must contain Vietnamese diacritics"
    assert not re.search(r"[\u4e00-\u9fff]", en_sec), "English messages must not contain Chinese characters"
    assert re.search(r"[\u4e00-\u9fff]", zh_sec), "Chinese messages must contain Chinese characters"

def test_7_descendant_clicks_in_form_do_not_prevent_default_or_trigger_confirm():
    """Descendant clicks on input/label/select must not prevent default or trigger local confirm."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const clickHandler = (listeners.click || [])[0];

const form = element("choose-form", "FORM");
form.setAttribute("data-portal-action", "manual-topup-confirm-selection");

const input = element("descendant-input", "INPUT");
const label = element("descendant-label", "LABEL");
const select = element("descendant-select", "SELECT");
form.appendChild(input);
form.appendChild(label);
form.appendChild(select);

let prevented = 0;
const mkEvent = (target) => ({ target, preventDefault() { prevented++; } });

clickHandler(mkEvent(input));
clickHandler(mkEvent(label));
clickHandler(mkEvent(select));

const cta = element("cta", "BUTTON");
cta.setAttribute("data-portal-action", "manual-topup-confirm-selection");
clickHandler(mkEvent(cta));

process.stdout.write(JSON.stringify({
    prevented,
    action_event_count: dispatchedActions.length
}));
'''
    res = _run_node_script(script)
    assert res["prevented"] == 1, "Only the CTA click should preventDefault, descendant clicks must not."
    assert res["action_event_count"] == 0, "No action events should be fired"


def test_8_submit_confirmed_form_fires_action_event_and_calls_api_exactly_once():
    """Submit confirmed form fires ACTION_EVENT exactly once, and integration handler calls expected POST."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const submitHandler = (listeners.submit || [])[0];

const form = element("create-form", "FORM");
form.setAttribute("data-portal-form", "");
form.setAttribute("data-portal-action", "manual-topup-create");
form.setAttribute("data-portal-route", "/wallet/topup");

const amount = element("amount", "INPUT"); amount.name = "amount_vnd"; amount.setAttribute("name", "amount_vnd"); amount.value = "125000";
const methodInput = element("method", "INPUT"); methodInput.name = "method"; methodInput.setAttribute("name", "method"); methodInput.value = "bank_acb_vietqr";
const reference = element("reference", "INPUT"); reference.name = "reference"; reference.setAttribute("name", "reference"); reference.value = "TX-125";

form.appendChild(amount); form.appendChild(methodInput); form.appendChild(reference);
form.elements = [amount, methodInput, reference];
form.querySelectorAll = () => [amount, methodInput, reference];

let prevented = 0;
submitHandler({ target: form, preventDefault() { prevented++; } });

process.stdout.write(JSON.stringify({
    prevented,
    actions: dispatchedActions
}));
'''
    res = _run_node_script(script)
    assert res["prevented"] == 1, "Submit must prevent default"
    assert len(res["actions"]) == 1, "Must emit exactly one action event"
    action = res["actions"][0]
    assert action["action"] == "manual-topup-create"
    assert action["route"] == "/wallet/topup"
    assert action["fields"]["amount_vnd"] == "125000"
    assert action["fields"]["method"] == "bank_acb_vietqr"
    assert action["fields"]["reference"] == "TX-125"

    integration_js = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    start = integration_js.index('if (action === "manual-topup-create")')
    end = integration_js.index('if (action === "finance-planning-view")', start)
    handler = integration_js[start:end]
    assert handler.count('api("/payments/manual", {') == 1
    assert 'method: "POST"' in handler
    assert 'body: JSON.stringify({ amount_vnd: amount, method, reference, idempotency_key: submission.key })' in handler
    for forbidden in ('/payments/create', 'safePayosCheckout', 'schedulePaymentPolling', 'window.open', 'provider'):
        assert forbidden not in handler
    cleanup_start = integration_js.index("function clearSessionScopedTransientDrafts()")
    cleanup_end = integration_js.index("function toast(message, type)", cleanup_start)
    cleanup = integration_js[cleanup_start:cleanup_end]
    constants = re.findall(r"clearTransientFormDraft\(([^)]+)\)", cleanup)
    script = "const drafts=new Map([[\"/wallet/topup\",{manual_selection_confirmed:true,reference:\"A\"}],[\"/public\",{keep:true}]]);" + "const window={TOANAASPortal:{clearTransientFormDraft:(route)=>drafts.delete(route)}};" + "\n".join(f'const {name}="/{index}";' for index, name in enumerate(constants) if name != '"/wallet/topup"') + cleanup + ";clearSessionScopedTransientDrafts();process.stdout.write(JSON.stringify({wallet:drafts.has(\"/wallet/topup\"),public:drafts.has(\"/public\")}));"
    result = subprocess.run([shutil.which("node"), "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"wallet": False, "public": True}


def test_9_instruction_css_matches_the_markup_instead_of_dead_component_classes():
    """The single instruction card must be styled by selectors its renderer actually emits."""
    portal = PORTAL_JS.read_text(encoding="utf-8")
    css = PORTAL_CSS.read_text(encoding="utf-8")
    manual_css = css[css.index("/* Manual top-up"):]
    guide = portal[portal.index("function renderManualTopupGuide(context)"):portal.index("function renderPaymentRequestForm(page, context)")]

    for marker in ('class="portal-manual-payment-method-copy"', '<figure><img src=', '<figcaption>'):
        assert marker in guide
    for selector in (
        ".portal-manual-payment-method-copy",
        ".portal-manual-payment-method-copy > span",
        ".portal-manual-payment-method dl",
        ".portal-manual-payment-method dt",
        ".portal-manual-payment-method dd",
        ".portal-manual-payment-method figure",
        ".portal-manual-payment-method img",
    ):
        assert selector in manual_css
    for dead in (
        ".portal-manual-payment-method-head",
        ".portal-manual-payment-method-body",
        ".portal-manual-payment-method-qr",
        ".portal-manual-payment-method-badge",
    ):
        assert dead not in manual_css
    desktop = re.search(r"\.portal-manual-payment-method\s*\{(?P<body>.*?)\n\}", manual_css, re.S)
    assert desktop
    assert "grid-template-columns: minmax(0, 1fr) minmax(132px, 180px)" in desktop.group("body")


def test_10_confirmed_instruction_focus_stays_visible_below_the_sticky_header():
    """Local confirm moves focus without allowing the sticky header to cover the heading."""
    portal = PORTAL_JS.read_text(encoding="utf-8")
    css = PORTAL_CSS.read_text(encoding="utf-8")
    confirm = portal[
        portal.index("function handleManualTopupConfirmSelection"):
        portal.index("function handleManualTopupChangeSelection")
    ]
    assert "window.requestAnimationFrame(() => window.requestAnimationFrame(focusConfirmedInstructions))" in confirm and "heading.focus({ preventScroll: true });" in confirm
    assert 'heading.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "auto" });' in confirm
    assert 'behavior: "smooth"' not in confirm
    heading_rule = re.search(
        r"\.portal-manual-payment-methods\s*>\s*h3\s*\{(?P<body>.*?)\n\}",
        css[css.index("/* Manual top-up"):],
        re.S,
    )
    assert heading_rule
    match = re.search(r"scroll-margin-top:\s*(\d+)px", heading_rule.group("body"))
    assert match and int(match.group(1)) >= 80


def test_11_destination_only_usdt_is_visible_disabled_and_cannot_confirm():
    """Binance/USDT is discoverable but never gains VND request authority from destination metadata."""
    script = r'''
mountPortal({ topup_lane: "manual" });
const initial = main.innerHTML;
const usdtOption = initial.match(/<option value="usdt_trc20"[^>]*>[^<]*<\/option>/);
const after = confirmManualSelection("usdt_trc20");

process.stdout.write(JSON.stringify({
  option: usdtOption ? usdtOption[0] : "",
  instruction: after.includes('data-manual-payment-method="usdt_trc20"'),
  qr: after.includes('/manual-methods/usdt_trc20/qr'),
  finalSubmit: after.includes('data-portal-action="manual-topup-create"'),
  actionEvents: dispatchedActions.length
}));
'''
    result = _run_node_script(script)
    assert 'value="usdt_trc20"' in result["option"]
    assert "disabled" in result["option"]
    assert "USDT TRC20 / Binance" in result["option"]
    assert "Chưa hỗ trợ đối soát VND" in result["option"]
    assert "Chưa được cấu hình" not in result["option"]
    assert result["instruction"] is False
    assert result["qr"] is False
    assert result["finalSubmit"] is False
    assert result["actionEvents"] == 0


def test_12_only_request_enabled_vnd_methods_with_canonical_qr_can_confirm():
    """Every enabled VND method renders exactly its one signed QR; a QR-less method fails closed."""
    script = r'''
const enabled = ["bank_acb_vietqr", "momo_tuithantai", "zalopay_personal", "zalopay_merchant"];

function choose(methodId) {
  window.TOANAASPortal.clearTransientFormDraft("/wallet/topup");
  mountPortal({ topup_lane: "manual" });
  return confirmManualSelection(methodId);
}

const rows = enabled.map((methodId) => {
  const html = choose(methodId);
  const qr = `/api/v1/payments/options/manual-methods/${methodId}/qr`;
  return {
    methodId,
    cardCount: (html.match(/data-manual-payment-method=/g) || []).length,
    selectedCardCount: (html.match(new RegExp(`data-manual-payment-method="${methodId}"`, "g")) || []).length,
    matchingQrCount: html.split(qr).length - 1,
    otherCardCount: enabled.filter((id) => id !== methodId && html.includes(`data-manual-payment-method="${id}"`)).length,
    finalSubmit: html.includes('data-portal-action="manual-topup-create"')
  };
});

window.TOANAASPortal.clearTransientFormDraft("/wallet/topup");
mountPortal({ topup_lane: "manual" });
const initial = main.innerHTML;
const bankOption = initial.match(/<option value="bank_acb"[^>]*>[^<]*<\/option>/);
const blocked = choose("bank_acb");
process.stdout.write(JSON.stringify({
  rows,
  bankOption: bankOption ? bankOption[0] : "",
  blockedQr: blocked.includes("/manual-methods/bank_acb/qr"),
  blockedFinalSubmit: blocked.includes('data-portal-action="manual-topup-create"'),
  actionEvents: dispatchedActions.length
}));
'''
    result = _run_node_script(script)
    assert len(result["rows"]) == 4
    for row in result["rows"]:
        assert row == {
            "methodId": row["methodId"],
            "cardCount": 1,
            "selectedCardCount": 1,
            "matchingQrCount": 1,
            "otherCardCount": 0,
            "finalSubmit": True,
        }
    assert 'value="bank_acb"' in result["bankOption"]
    assert "disabled" in result["bankOption"]
    assert result["blockedQr"] is False
    assert result["blockedFinalSubmit"] is False
    assert result["actionEvents"] == 0
