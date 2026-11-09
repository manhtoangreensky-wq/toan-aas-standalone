import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8').replace(/\r\n/g, '\n');
const stateStart = source.indexOf('  let lastNormalizedRoute = null;');
const mountStart = source.indexOf('  function mountPortal(override) {', stateStart);
const bodyStart = mountStart + '  function mountPortal(override) {'.length;
const prefixEnd = source.indexOf('    if (override', bodyStart);
const tailStart = source.indexOf('    if (replaceResult && typeof replaceResult.then', mountStart);
const tailEnd = source.indexOf('\n  }\n\n  let copilotState', tailStart);
const focusStart = source.indexOf('  function focusSnapshot() {');
const focusEnd = source.indexOf('  function bindInteractions() {', focusStart);
assert.ok(stateStart > 0 && mountStart > stateStart && prefixEnd > bodyStart);
assert.ok(tailStart > prefixEnd && tailEnd > tailStart && focusEnd > focusStart);

function harness() {
  const nodes = new Map();
  const document = {
    activeElement: null,
    getElementById: id => nodes.get(id) || null,
    querySelector: selector => [...nodes.values()].find(n => selector === `[name="${n.name}"]`) || null,
    querySelectorAll: () => []
  };
  const context = vm.createContext({ document, window: {} });
  const code = source.slice(focusStart, focusEnd) + source.slice(stateStart, mountStart)
    + `\nfunction runMount(focus, replaceResult) {${source.slice(bodyStart, prefixEnd)}${source.slice(tailStart, tailEnd)}\n}`
    + '\nwindow.testFocus = { runMount, focusSnapshot };';
  vm.runInContext(code, context, { filename: 'portal.js' });
  const api = context.window.testFocus;
  function input(id, name = id) {
    const node = {
      id, name, selectionStart: 2, selectionEnd: 5, calls: [], selections: [],
      matches: selector => selector === 'input, textarea, select',
      closest: () => null,
      focus(options) { this.calls.push(options); document.activeElement = this; },
      setSelectionRange(start, end) { this.selections.push([start, end]); }
    };
    nodes.set(id, node);
    return node;
  }
  function deferred() {
    const result = { then(ok, fail) { result.ok = ok; result.fail = fail; } };
    return result;
  }
  return { document, nodes, input, deferred, mount: api.runMount, snapshot: api.focusSnapshot };
}

for (const completion of ['ok', 'fail']) {
  for (const newer of ['pending', 'synchronous']) {
    test(`Old ${completion} continuation cannot focus a newer ${newer} mount`, () => {
      const h = harness();
      const oldTitle = h.input('portal-field-title', 'title');
      h.document.activeElement = oldTitle;
      const pendingA = h.deferred();
      h.mount(h.snapshot(), pendingA);
      const newTitle = h.input('portal-field-title', 'title');
      const newDescription = h.input('portal-field-description', 'description');
      h.document.activeElement = newDescription;
      h.mount(h.snapshot(), newer === 'pending' ? h.deferred() : null);
      pendingA[completion]();
      assert.equal(h.document.activeElement, newDescription);
      assert.equal(newTitle.calls.length, 0, 'A matching current ID must not accept an old snapshot');
      assert.equal(oldTitle.calls.length, 0);
    });
  }
}

for (const completion of ['ok', 'fail']) {
  test(`Current ${completion} completion preserves selection and preventScroll`, () => {
    const h = harness();
    const old = h.input('portal-field-title', 'title');
    h.document.activeElement = old;
    const pending = h.deferred();
    h.mount(h.snapshot(), pending);
    const current = h.input('portal-field-title', 'title');
    pending[completion]();
    assert.equal(h.document.activeElement, current);
    assert.equal(current.calls.length, 1);
    assert.equal(current.calls[0].preventScroll, true);
    assert.deepEqual(current.selections, [[2, 5]]);
  });
}

test('Synchronous fallback still restores the current field once', () => {
  const h = harness();
  const input = h.input('portal-field-title');
  h.document.activeElement = input;
  h.mount(h.snapshot(), undefined);
  assert.equal(h.document.activeElement, input);
  assert.equal(input.calls.length, 1);
  assert.equal(input.calls[0].preventScroll, true);
});

test('A newer null snapshot invalidates old focus without focusing another field', () => {
  const h = harness();
  const old = h.input('portal-field-title');
  h.document.activeElement = old;
  const pending = h.deferred();
  h.mount(h.snapshot(), pending);
  const current = h.input('portal-field-description');
  h.document.activeElement = current;
  h.mount(null, null);
  pending.ok();
  assert.equal(h.document.activeElement, current);
  assert.equal(old.calls.length, 0);
  assert.equal(current.calls.length, 0);
});
