import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const start = source.indexOf('  function bindCopilotListeners(container, context) {');
const end = source.indexOf('  function renderCopilotHtml(container, context) {', start);
assert.ok(start > 0 && end > start);
const bind = source.slice(start, end);

function run(open) {
  const list = { scrollHeight: 500, scrollTop: 0 };
  let reads = 0; let writes = 0;
  Object.defineProperty(list, 'scrollHeight', { get() { reads++; return 500; } });
  Object.defineProperty(list, 'scrollTop', { get() { return 0; }, set() { writes++; } });
  const container = { querySelector(selector) { return selector === '#portal-copilot-msgs-list' ? list : null; }, querySelectorAll() { return []; } };
  const runtime = vm.createContext({ container, copilotState: { open, messages: open ? [{}, {}] : [{}] }, document: { getElementById: () => null }, window: {}, setTimeout() {}, clearTimeout() {} });
  vm.runInContext(bind, runtime);
  vm.runInContext('bindCopilotListeners(container, {});', runtime);
  return { reads, writes };
}

test('Closed assistant does not read or write its hidden scroll list', () => {
  assert.deepEqual(run(false), { reads: 0, writes: 0 });
});

test('Open assistant retains the existing scroll-to-latest behavior', () => {
  assert.deepEqual(run(true), { reads: 1, writes: 1 });
});
