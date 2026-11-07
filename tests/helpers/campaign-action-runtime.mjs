import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const integration = fs.readFileSync(path.join(root, 'static/portal/integration.js'), 'utf8');
const i18n = fs.readFileSync(path.join(root, 'static/portal/portal-i18n.js'), 'utf8');

export const planId = '33333333-3333-4333-8333-333333333333';
export const detailRoute = `/campaigns/${planId}`;
export const actions = ['campaign-create', 'campaign-update', 'campaign-update-status'];

export function campaignItem(revision = 1, status = 'draft', id = planId) {
  return {
    id,
    title: 'CUSTOMER_TITLE',
    destination_url: 'https://example.invalid/customer',
    platform: 'website',
    objective: 'traffic',
    scheduled_for: '',
    approval_status: status,
    review_note: '',
    created_at: '2026-11-07T00:00:00+00:00',
    updated_at: '2026-11-07T00:00:00+00:00',
    revision
  };
}

export function campaignContext(pathname, label = 'A') {
  return {
    path: pathname,
    account: { id: label === 'A' ? '11111111-1111-4111-8111-111111111111' : '22222222-2222-4222-8222-222222222222' },
    session: { authenticated: true, csrfToken: `synthetic-campaign-${label}` },
    capabilities: Object.fromEntries(actions.map(action => [action, true])),
    bridge: { available: false },
    campaignPlans: [campaignItem()],
    campaignPlanDetail: pathname === detailRoute ? campaignItem() : {},
    campaignPlannerReadState: 'ready',
    pageStates: { [pathname]: 'ready' }
  };
}

export function campaignActionRuntime(action, options = {}) {
  assert(actions.includes(action));
  const pathname = options.uiPath || (action === 'campaign-create' ? '/campaigns/new' : detailRoute);
  let state = campaignContext(pathname);
  let button;
  let form;
  const pending = [];
  const listeners = new Map();
  const toasts = [];
  const toastEvents = [];
  const networkLog = [];
  const reads = [];
  const assignments = [];
  const clears = [];
  const received = new Map();
  const noop = () => {};
  const node = (attributes = {}) => ({
    attributes: { ...attributes }, disabled: false, textContent: '', className: '',
    setAttribute(key, value) { this.attributes[key] = String(value); },
    getAttribute(key) { return this.attributes[key] ?? null; },
    removeAttribute(key) { delete this.attributes[key]; },
    remove() { const index = toasts.indexOf(this); if (index >= 0) toasts.splice(index, 1); }
  });
  function resetControls(disabled = false) {
    const controlRoute = options.eventRoute || state.path;
    button = node({ 'data-portal-action': action, 'data-portal-route': controlRoute });
    button.disabled = disabled;
    form = node({ 'data-portal-action': action, 'data-portal-route': controlRoute });
    form.querySelector = () => button;
  }
  resetControls();
  const region = { appendChild(value) { toasts.push(value); toastEvents.push({ text: value.textContent, role: value.getAttribute('role') }); }, querySelectorAll() { return toasts; } };
  const document = {
    readyState: 'loading', visibilityState: 'visible', addEventListener: noop,
    createElement: () => node(),
    querySelector: selector => selector === '[data-portal-toast]' ? region : null,
    querySelectorAll: selector => selector === '[data-portal-action]' ? [button] : selector === '[data-portal-form]' ? [form] : [],
    documentElement: { lang: 'vi', setAttribute: noop, getAttribute: () => null },
    body: { classList: { add: noop, remove: noop, toggle: noop } }
  };
  const window = {
    document, navigator: { language: 'vi' },
    location: { pathname, search: '', origin: 'https://unit.invalid', href: `https://unit.invalid${pathname}`, assign: value => { assignments.push(value); window.location.pathname = String(value).split('?')[0]; } },
    addEventListener: (name, handler) => listeners.set(name, handler), dispatchEvent: noop,
    setTimeout: noop, clearTimeout: noop, setInterval: noop, clearInterval: noop,
    localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    sessionStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    matchMedia: () => ({ matches: false, addEventListener: noop }), crypto: globalThis.crypto
  };
  Object.defineProperty(window, '__TOAN_AAS_PORTAL__', { get: () => state, set: value => { state = value; }, configurable: true });
  window.TOANAASPortal = { mount: noop, clearTransientFormDraft: route => clears.push(route) };

  const fetch = (url, options = {}) => {
    const parsed = new URL(url, 'https://unit.invalid');
    const method = options.method || 'GET';
    networkLog.push({ path: parsed.pathname, method, body: options.body ? JSON.parse(options.body) : undefined });
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.match(parsed.pathname, /^\/api\/v1\/campaigns(?:\/[0-9a-f-]{36}(?:\/(?:status|schedule-intents))?)?$/);
    if (method === 'GET') {
      assert.equal(options.body, undefined);
      const id = parsed.pathname.split('/')[4];
      const schedule = parsed.pathname.endsWith('/schedule-intents');
      const payload = { ok: true, status: 'read_only', error_code: null, message: '', data: schedule ? {
        execution: 'web_native_in_app_record_intent_only', data_origin: 'signed_account_campaign_plan_only',
        source_content_copied: false, scheduled_for_is_inert: true, bot_called: false, bridge_called: false,
        provider_called: false, publish_action_created: false, wallet_mutated: false, payment_processed: false,
        job_created: false, notification_sent: false, delivery: 'in_app_record_only', schedule_intents: []
      } : { item: received.get(id) || campaignItem(1, 'draft', id) } };
      if (!config.deferReads) return Promise.resolve({ ok: true, status: 200, json: async () => payload });
      let resolve;
      const promise = new Promise(done => { resolve = done; });
      reads.push({ resolve, payload, path: parsed.pathname });
      return promise;
    }
    const entry = {};
    entry.promise = new Promise((resolve, reject) => { entry.resolve = resolve; entry.reject = reject; });
    pending.push({ ...entry, path: parsed.pathname, method, body: JSON.parse(options.body || '{}') });
    return entry.promise;
  };
  const config = options;
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Headers, FormData, Blob,
    AbortController, Intl, console, fetch, crypto: globalThis.crypto,
    setTimeout: window.setTimeout, clearTimeout: window.clearTimeout
  });
  vm.runInContext(i18n, sandbox);
  window.TOANAASI18n.setLocale('vi', { emit: false });
  const anchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(integration.split(anchor).length, 2);
  const injected = '  window.__campaignActionTest={advanceSession:()=>{campaignSessionEpoch+=1;}};\n';
  vm.runInContext(integration.replace(anchor, injected + anchor), sandbox);
  assert.ok(listeners.has('toanaas:portal-action'));

  const fields = action === 'campaign-create'
    ? { title: 'Kế hoạch khách hàng', destination_url: 'https://example.invalid/customer', platform: 'website', objective: 'traffic', scheduled_for: '' }
    : action === 'campaign-update'
      ? { plan_id: planId, title: 'Kế hoạch khách hàng', destination_url: 'https://example.invalid/customer', platform: 'website', objective: 'traffic', scheduled_for: '' }
      : { plan_id: planId, approval_status: 'review', review_note: 'Rà soát nội bộ' };

  function settle(index, kind = 'valid', nativeEnvelope = null) {
    const entry = pending[index];
    assert.ok(entry, 'write must reach fake fetch');
    if (kind === 'transport_error') { entry.reject(new Error('network unavailable')); return; }
    const statusWrite = entry.path.endsWith('/status');
    const create = entry.path === '/api/v1/campaigns';
    const id = create ? planId : entry.path.split('/')[4];
    const status = statusWrite ? entry.body.approval_status : 'draft';
    const previous = received.get(id) || campaignItem(1, 'draft', id);
    const item = { ...previous, revision: create ? 1 : previous.revision + 1, approval_status: status,
      ...(!statusWrite ? entry.body : { review_note: entry.body.review_note }) };
    delete item.idempotency_key;
    received.set(id, item);
    const payload = nativeEnvelope || (kind === 'guarded'
      ? { ok: false, status: 'guarded', message: 'Không tìm thấy kế hoạch thuộc tài khoản hiện tại.' }
      : { ok: true, status, error_code: null, message: create
        ? 'Đã lưu bản nháp kế hoạch trên Web. Chưa có nội dung nào được xuất bản hoặc gửi sang Bot.'
        : statusWrite ? `Đã cập nhật kế hoạch thành ${status}. Đây vẫn chỉ là trạng thái nội bộ trên Web.`
          : 'Đã cập nhật chi tiết kế hoạch trên Web. Không có nội dung nào được publish hoặc gửi sang Bot.', data: { item } });
    if (nativeEnvelope?.data?.item) received.set(nativeEnvelope.data.item.id, nativeEnvelope.data.item);
    entry.resolve({ ok: payload.ok, status: kind === 'guarded' ? 404 : 200, json: async () => payload });
  }

  return {
    pending, toasts, toastEvents, fields, networkLog, reads, assignments, clears,
    run: (override = fields, dispatchedAction = action) => listeners.get('toanaas:portal-action')({ detail: { action: dispatchedAction, route: config.eventRoute || state.path, fields: { ...override } } }),
    settle,
    settleReads(kind = 'valid') {
      for (const read of reads) {
        if (read.settled) continue;
        read.settled = true;
        const failure = kind === 'error';
        read.resolve({ ok: !failure, status: failure ? 404 : 200, json: async () => failure ? { ok: false, status: 'guarded', message: 'read unavailable', data: {} } : read.payload });
      }
    },
    get state() { return state; },
    get button() { return button; },
    replace(next, { epoch = true, disabled = true } = {}) {
      state = next;
      window.location.pathname = next.path;
      resetControls(disabled);
      if (epoch) window.__campaignActionTest.advanceSession();
    }
  };
}
