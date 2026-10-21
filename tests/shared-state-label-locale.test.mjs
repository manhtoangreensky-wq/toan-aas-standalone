import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const portalSource = fs.readFileSync(path.join(repoRoot, 'static/portal/portal.js'), 'utf8');
const i18nSource = fs.readFileSync(path.join(repoRoot, 'static/portal/portal-i18n.js'), 'utf8');

const stateCodeStart = portalSource.indexOf('  const ALLOWED_STATES = new Set([');
const stateCodeEnd = portalSource.indexOf('  const PAYMENT_STATUS_LABELS = Object.freeze({', stateCodeStart);
assert.ok(stateCodeStart >= 0 && stateCodeEnd > stateCodeStart, 'state declarations must exist in portal.js');
const stateSnippet = portalSource.slice(stateCodeStart, stateCodeEnd);

function createHarness(locale) {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params, locale) : fallback;
  vm.runInContext([
    stateSnippet,
    'globalThis.ALLOWED_STATES = ALLOWED_STATES;',
    'globalThis.STATE_LABELS = STATE_LABELS;',
    'globalThis.STATE_I18N_KEYS = STATE_I18N_KEYS;',
    'globalThis.stateLabel = stateLabel;'
  ].join('\n'), ctx);
  return ctx;
}

const MANDATORY_LABELS = [
  { state: 'failed_no_charge', key: 'states.failedNoCharge', vi: 'Không hoàn tất · chưa trừ Xu', en: 'Failed · no Xu charged', zh: '未完成 · 未扣除 Xu' },
  { state: 'refunded', key: 'states.refunded', vi: 'Đã hoàn Xu', en: 'Xu refunded', zh: '已退还 Xu' },
  { state: 'in_review', key: 'states.inReview', vi: 'Đang chờ duyệt', en: 'Pending review', zh: '待审核' },
  { state: 'approved', key: 'states.approved', vi: 'Đã sẵn sàng', en: 'Approved', zh: '已批准' },
  { state: 'error', key: 'states.error', vi: 'Lỗi kết nối', en: 'Connection error', zh: '连接错误' },
  { state: 'new', key: 'states.new', vi: 'Yêu cầu mới', en: 'New request', zh: '新请求' },
  { state: 'waiting_user', key: 'states.waitingUser', vi: 'Chờ bạn phản hồi', en: 'Awaiting your reply', zh: '等待你的回复' },
  { state: 'waiting_provider', key: 'states.waitingProvider', vi: 'Chờ đối tác xác minh', en: 'Awaiting partner verification', zh: '等待合作方核实' },
  { state: 'refund_pending', key: 'states.refundPending', vi: 'Đang xem xét hoàn tiền', en: 'Refund under review', zh: '退款审核中' },
  { state: 'resolved', key: 'states.resolved', vi: 'Đã xử lý', en: 'Resolved', zh: '已解决' },
  { state: 'closed', key: 'states.closed', vi: 'Đã đóng', en: 'Closed', zh: '已关闭' },
  { state: 'unread', key: 'states.unread', vi: 'Chưa đọc', en: 'Unread', zh: '未读' },
  { state: 'read', key: 'states.read', vi: 'Đã đọc', en: 'Read', zh: '已读' },
  { state: 'dismissed', key: 'states.dismissed', vi: 'Đã bỏ qua', en: 'Dismissed', zh: '已忽略' },
  { state: 'backlog', key: 'states.backlog', vi: 'Việc chờ xử lý', en: 'Backlog', zh: '待办列表' }
];

test('VI catalogue covers all 35 allowed states with registered i18n keys', () => {
  const harness = createHarness('vi');
  const { ALLOWED_STATES, STATE_I18N_KEYS, stateLabel } = harness;
  const messages = harness.TOANAASI18n.messages.vi;
  assert.equal(ALLOWED_STATES.size, 35, 'ALLOWED_STATES must have exactly 35 states');
  for (const state of ALLOWED_STATES) {
    const key = STATE_I18N_KEYS[state];
    assert.ok(key, `state "${state}" must have a mapping in STATE_I18N_KEYS`);
    assert.ok(key.startsWith('states.'), `key "${key}" for state "${state}" must start with "states."`);
    assert.ok(messages[key], `VI catalogue must contain key "${key}" for state "${state}"`);
    const label = stateLabel(state);
    assert.ok(typeof label === 'string' && label.length > 0, `stateLabel("${state}") must return non-empty text`);
  }
});

test('VI renders exact 15 mandatory state labels from catalogue', () => {
  const harness = createHarness('vi');
  const { stateLabel, STATE_LABELS } = harness;
  for (const item of MANDATORY_LABELS) {
    assert.equal(stateLabel(item.state), item.vi, `VI stateLabel("${item.state}") must match spec`);
  }
  assert.equal(STATE_LABELS.backlog, 'Việc chờ xử lý', 'STATE_LABELS.backlog fallback must match spec');
});

test('EN catalogue covers all 35 allowed states without Vietnamese fallback', () => {
  const harness = createHarness('en');
  const { ALLOWED_STATES, STATE_I18N_KEYS, stateLabel } = harness;
  const messages = harness.TOANAASI18n.messages.en;
  assert.equal(ALLOWED_STATES.size, 35, 'ALLOWED_STATES must have exactly 35 states');
  for (const state of ALLOWED_STATES) {
    const key = STATE_I18N_KEYS[state];
    assert.ok(key, `state "${state}" must have a mapping in STATE_I18N_KEYS`);
    assert.ok(messages[key], `EN catalogue must contain key "${key}" for state "${state}"`);
    const label = stateLabel(state);
    assert.ok(typeof label === 'string' && label.length > 0, `stateLabel("${state}") must return non-empty text`);
    assert.equal(label, messages[key], `EN stateLabel("${state}") must match EN catalogue`);
  }
});

test('EN renders exact 15 mandatory state labels from catalogue', () => {
  const harness = createHarness('en');
  const { stateLabel } = harness;
  for (const item of MANDATORY_LABELS) {
    assert.equal(stateLabel(item.state), item.en, `EN stateLabel("${item.state}") must match spec`);
  }
});

test('ZH catalogue covers all 35 allowed states with matching key set', () => {
  const harness = createHarness('zh');
  const { ALLOWED_STATES, STATE_I18N_KEYS, stateLabel } = harness;
  const messages = harness.TOANAASI18n.messages;
  assert.equal(ALLOWED_STATES.size, 35, 'ALLOWED_STATES must have exactly 35 states');
  const viStateKeys = Object.keys(messages.vi).filter((k) => k.startsWith('states.')).sort();
  const enStateKeys = Object.keys(messages.en).filter((k) => k.startsWith('states.')).sort();
  const zhStateKeys = Object.keys(messages.zh).filter((k) => k.startsWith('states.')).sort();
  assert.deepEqual(enStateKeys, viStateKeys, 'EN and VI states.* keysets must match');
  assert.deepEqual(zhStateKeys, viStateKeys, 'ZH and VI states.* keysets must match');
  for (const state of ALLOWED_STATES) {
    const key = STATE_I18N_KEYS[state];
    assert.ok(key, `state "${state}" must have a mapping in STATE_I18N_KEYS`);
    assert.ok(messages.zh[key], `ZH catalogue must contain key "${key}" for state "${state}"`);
    const label = stateLabel(state);
    assert.ok(typeof label === 'string' && label.length > 0, `stateLabel("${state}") must return non-empty text`);
    assert.equal(label, messages.zh[key], `ZH stateLabel("${state}") must match ZH catalogue`);
  }
});

test('ZH renders exact 15 mandatory state labels from catalogue', () => {
  const harness = createHarness('zh');
  const { stateLabel } = harness;
  for (const item of MANDATORY_LABELS) {
    assert.equal(stateLabel(item.state), item.zh, `ZH stateLabel("${item.state}") must match spec`);
  }
});

test('Unknown states and read_only alias handle safety and normalization across all locales', () => {
  for (const locale of ['vi', 'en', 'zh']) {
    const harness = createHarness(locale);
    const { stateLabel } = harness;
    assert.equal(stateLabel('read_only'), stateLabel('ready'), `read_only must alias ready in locale ${locale}`);
    const guardedLabel = stateLabel('guarded');
    assert.ok(guardedLabel && guardedLabel.length > 0, `guarded label must be non-empty in locale ${locale}`);
    for (const invalid of ['unknown', 'invalid_status', '<script>alert(1)</script>', 'DROP TABLE', '', null, undefined, false, 123]) {
      const rendered = stateLabel(invalid);
      assert.equal(rendered, guardedLabel, `invalid state "${String(invalid)}" must normalize to guarded in locale ${locale}`);
      assert.doesNotMatch(rendered, /<script>|DROP TABLE|invalid/, 'unknown inputs must never be rendered unescaped');
    }
  }
});
