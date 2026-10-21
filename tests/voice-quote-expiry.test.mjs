import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, name);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}

function runtime(route = '/voice/tts') {
  let now = Date.parse('2026-10-20T10:00:00Z');
  let nextTimer = 0;
  const timers = new Map();
  const input = { script: 'Lời thoại thử nghiệm', default_voice_gender: 'female', speed: '1.0', volume_percent: '0' };
  const flow = { phase: 'estimate', status: 'awaiting_confirm', input: { ...input },
    estimateFingerprint: 'qa-original', webQuoteReceipt: 'Q'.repeat(48),
    data: { estimate: { available: true, quote_expires_at: new Date(now + 1000).toISOString() } } };
  const bootstrap = { path: route, featureFlows: { [route]: flow } };
  const confirm = { hidden: false, disabled: true };
  const note = { hidden: true, textContent: '' };
  const form = { getAttribute: () => route, closest: () => ({ querySelectorAll: () => [confirm] }), querySelector: () => note };
  const page = { path: route, fields: Object.keys(input).map((name) => ({ name })) };
  const ctx = {
    Date: { now: () => now, parse: Date.parse },
    normalizePath: (path) => path,
    getBootstrap: () => bootstrap,
    resolvePage: () => page,
    collectFormFields: () => input,
    voiceUiText: (key, fallback) => fallback,
    document: { querySelector: () => form },
    window: { __TOAN_AAS_PORTAL__: bootstrap,
      setTimeout: (callback, delay) => { const id = ++nextTimer; timers.set(id, { callback, delay }); return id; },
      clearTimeout: (id) => timers.delete(id) },
  };
  vm.createContext(ctx);
  vm.runInContext('let voiceQuoteExpiryTimer = null; let voiceQuoteExpiryKey = "";\n' + [
    'flowQuoteExpiry', 'flowHasFreshEstimate', 'voiceQuoteExpiryState', 'voiceQuoteHasEdits',
    'synchronizeVoiceQuoteFreshness', 'clearVoiceQuoteExpiryTimer', 'scheduleVoiceQuoteExpiry',
  ].map(fn).join('\n'), ctx);
  return { ctx, timers, input, flow, bootstrap, form, page, confirm, note,
    setNow: (value) => { now = value; }, now: () => now,
    fire: () => { const [id, timer] = [...timers][0]; timers.delete(id); timer.callback(); } };
}

test('Voice expiry distinguishes future, boundary and elapsed canonical timestamps', () => {
  const r = runtime();
  const expiry = Date.parse(r.flow.data.estimate.quote_expires_at);
  assert.equal(r.ctx.voiceQuoteExpiryState(r.flow, expiry - 1).expired, false);
  assert.equal(r.ctx.voiceQuoteExpiryState(r.flow, expiry).expired, true);
  assert.equal(r.ctx.voiceQuoteExpiryState(r.flow, expiry + 1).expired, true);
});

test('Missing or malformed expiry retains the existing no-deadline policy', () => {
  const r = runtime();
  for (const value of [undefined, 'not-a-date']) {
    r.flow.data.estimate.quote_expires_at = value;
    assert.deepEqual({ ...r.ctx.voiceQuoteExpiryState(r.flow) }, { expiry: null, hasExpiry: false, expired: false });
    r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
    assert.equal(r.timers.size, 0);
    assert.equal(r.confirm.hidden, false);
  }
});

test('Idle expiry updates existing controls without replacing the form or its values', () => {
  const r = runtime();
  const original = { ...r.input };
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
  assert.equal(r.timers.size, 1);
  assert.equal([...r.timers.values()][0].delay, 1020);
  r.setNow(r.now() + 1020);
  r.fire();
  assert.equal(r.timers.size, 0);
  assert.equal(r.confirm.hidden, true);
  assert.equal(r.confirm.disabled, true);
  assert.equal(r.note.hidden, false);
  assert.equal(r.note.textContent, 'Báo giá đã hết hạn. Xem báo giá mới trước khi xác nhận.');
  assert.deepEqual(r.input, original);
});

test('Post-expiry input and exact reversion keep the expiry note and cannot restore confirm', () => {
  const r = runtime();
  r.setNow(r.now() + 2000);
  r.input.script = 'Nội dung mới';
  r.ctx.synchronizeVoiceQuoteFreshness(r.form);
  r.input.script = r.flow.input.script;
  r.ctx.synchronizeVoiceQuoteFreshness(r.form);
  assert.equal(r.confirm.hidden, true);
  assert.equal(r.note.hidden, false);
  assert.match(r.note.textContent, /Báo giá đã hết hạn/);
  assert.equal(r.input.volume_percent, '0');
});

test('Re-render replaces the timer and leaving Voice cancels it', () => {
  const r = runtime();
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
  const first = [...r.timers.keys()][0];
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
  assert.equal(r.timers.size, 1);
  assert.equal(r.timers.has(first), false);
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, { path: '/music/create' });
  assert.equal(r.timers.size, 0);
});

test('Timer callback ignores a route that is no longer current', () => {
  const r = runtime();
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
  r.bootstrap.path = '/music/create';
  r.setNow(r.now() + 2000);
  r.fire();
  assert.equal(r.confirm.hidden, false);
  assert.equal(r.note.hidden, true);
});

test('A new canonical future expiry replaces the old timer deadline', () => {
  const r = runtime();
  r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
  r.flow.data.estimate.quote_expires_at = new Date(r.now() + 5000).toISOString();
  r.setNow(r.now() + 1020);
  r.fire();
  assert.equal(r.timers.size, 1);
  assert.equal([...r.timers.values()][0].delay, 4000);
  assert.equal(r.confirm.hidden, false);
  assert.equal(r.note.hidden, true);
});

test('Each Voice route uses the same bounded in-place expiry lifecycle', () => {
  for (const route of ['/voice/tts', '/voice/saved', '/voice/stt', '/voice/clone']) {
    const r = runtime(route);
    r.ctx.scheduleVoiceQuoteExpiry(r.bootstrap, r.page);
    assert.equal(r.timers.size, 1, route);
    r.setNow(r.now() + 2000);
    r.fire();
    assert.equal(r.confirm.hidden, true, route);
    assert.equal(r.note.hidden, false, route);
  }
});
