import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8').replace(/\r\n/g, '\n');
const start = source.indexOf('  function renderStatusCard(');
const end = source.indexOf('\n  function renderSummary', start);
assert.ok(start >= 0 && end > start, 'renderStatusCard boundary must remain present');

function render() {
  const context = {
    safeText: value => String(value ?? ''),
    stateFor: () => 'guarded',
    statusMessage: () => ({ icon: '!', title: 'Cần kiểm tra', text: 'Không có thao tác giả.' }),
    portalStatusIcon: () => '!',
    document: {}
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nglobalThis.renderStatusCard = renderStatusCard;`, context);
  return context.renderStatusCard(
    { layout: 'feature', access: 'member', path: '/image/create' },
    { bridge: { available: false }, session: { authenticated: false } }
  );
}

test('customer status card does not repeat technical bridge/session/payment metadata', () => {
  const html = render();
  assert.match(html, /data-state="guarded"/);
  assert.doesNotMatch(html, /portal-state-meta|Bot integration|Signed session|provider\/payment call/);
});
