import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-motion.js', 'utf8');

function harness({ delayedApply = false, reduced = false, native = true, throws = false } = {}) {
  const callbacks = [], entries = [];
  let reducedMotion = reduced;
  const shell = { dataset: { portalSurface: 'customer', portalAppKind: 'customer' } };
  const makeMain = () => {
    const attrs = new Map(), listeners = new Map();
    return {
      dataset: { portalPresentationPhase: 'entry', portalMotionSkipEnter: 'false' },
      parentElement: shell,
      content: '',
      querySelector: () => null,
      setAttribute: (key, value) => { attrs.set(key, value); if (key === 'data-portal-motion') entries.push(value); },
      getAttribute: key => attrs.get(key) ?? null,
      removeAttribute: key => attrs.delete(key),
      addEventListener: (key, value) => listeners.set(key, value),
      removeEventListener: (key, value) => { if (listeners.get(key) === value) listeners.delete(key); }
    };
  };
  const window = { matchMedia: () => ({ matches: reducedMotion }), setTimeout: () => 1, clearTimeout: () => {} };
  const document = native ? {
    startViewTransition(apply) {
      if (throws) throw new Error('Native transition unavailable');
      if (!delayedApply) apply();
      let resolve;
      const updateCallbackDone = new Promise(done => { resolve = done; });
      callbacks.push(() => { if (delayedApply) apply(); resolve(); });
      return { updateCallbackDone, ready: Promise.resolve(), finished: Promise.resolve() };
    }
  } : {};
  vm.runInNewContext(source, { window, document });
  return { main: makeMain(), makeMain, shell, callbacks, entries, setReduced: value => { reducedMotion = value; }, motion: window.TOANAASPortalMotion };
}

// Break caught: a delayed native update or its completion re-enters or
// overwrites content rendered by a newer replacement of the same main.
for (const delayedApply of [false, true]) {
  for (const replacement of ['skip-route', 'hydration', 'reduced-route']) {
    test(`Superseded ${delayedApply ? 'native apply' : 'entry completion'} cannot change newer ${replacement}`, async () => {
      const h = harness({ delayedApply });
      const old = h.motion.replace(h.shell, h.main, () => { h.main.content = 'old'; });
      if (replacement === 'hydration') h.main.dataset.portalPresentationPhase = 'settled';
      else if (replacement === 'reduced-route') h.setReduced(true);
      else h.main.dataset.portalMotionSkipEnter = 'true';
      await h.motion.replace(h.shell, h.main, () => { h.main.content = 'new'; },
        replacement === 'skip-route' ? { animate: false } : undefined);
      const entriesBefore = h.entries.length;
      h.callbacks.shift()();
      await old;
      assert.equal(h.main.content, 'new');
      assert.equal(h.main.getAttribute('data-portal-motion'), null);
      assert.equal(h.entries.length, entriesBefore, 'Old completion must not start another entrance');
    });
  }
}

test('A current deferred native transition still renders and enters once', async () => {
  const h = harness({ delayedApply: true });
  const pending = h.motion.replace(h.shell, h.main, () => { h.main.content = 'current'; });
  assert.equal(h.main.content, '');
  h.callbacks.shift()();
  await pending;
  assert.equal(h.main.content, 'current');
  assert.deepEqual(h.entries, ['enter']);
});

test('Ownership is per main: replacing another main cannot discard the first transition', async () => {
  const h = harness({ delayedApply: true });
  const second = h.makeMain();
  const firstPending = h.motion.replace(h.shell, h.main, () => { h.main.content = 'first'; });
  const secondPending = h.motion.replace(h.shell, second, () => { second.content = 'second'; });
  h.callbacks[1]();
  await secondPending;
  h.callbacks[0]();
  await firstPending;
  assert.equal(h.main.content, 'first');
  assert.equal(second.content, 'second');
  assert.equal(h.main.getAttribute('data-portal-motion'), 'enter');
  assert.equal(second.getAttribute('data-portal-motion'), 'enter');
});

test('Latest native replacement survives an older callback arriving after it', async () => {
  const h = harness({ delayedApply: true });
  const old = h.motion.replace(h.shell, h.main, () => { h.main.content = 'old'; });
  const latest = h.motion.replace(h.shell, h.main, () => { h.main.content = 'latest'; });
  h.callbacks[1]();
  await latest;
  h.callbacks[0]();
  await old;
  assert.equal(h.main.content, 'latest');
  assert.deepEqual(h.entries, ['enter']);
});

for (const options of [{ native: false }, { throws: true }, { reduced: true }]) {
  test(`Fallback remains usable: ${JSON.stringify(options)}`, async () => {
    const h = harness(options);
    await h.motion.replace(h.shell, h.main, () => { h.main.content = 'rendered'; });
    assert.equal(h.main.content, 'rendered');
    assert.equal(h.main.getAttribute('data-portal-motion'), options.reduced ? null : 'enter');
  });
}
