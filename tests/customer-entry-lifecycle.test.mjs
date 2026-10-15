import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-motion.js', 'utf8');
const theme = fs.readFileSync('static/portal/portal-theme.css', 'utf8');

function createMotionHarness(shellDataset) {
  const timers = [];
  const listeners = new Map();
  let now = 0;
  let nextTimerId = 0;
  const window = {
    matchMedia: () => ({ matches: false }),
    setTimeout(callback, delay) {
      const timer = { id: ++nextTimerId, due: now + delay, callback, canceled: false };
      timers.push(timer);
      return timer.id;
    },
    clearTimeout(id) {
      const timer = timers.find(candidate => candidate.id === id);
      if (timer) timer.canceled = true;
    }
  };
  const shell = { dataset: shellDataset, parentElement: null };
  const nestedContainer = { dataset: {}, parentElement: shell };
  const workspace = { dataset: {}, parentElement: nestedContainer };
  const attributes = new Map();
  const main = {
    parentElement: workspace,
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.has(name) ? attributes.get(name) : null; },
    removeAttribute(name) { attributes.delete(name); },
    addEventListener(name, handler) { listeners.set(name, handler); },
    removeEventListener(name, handler) {
      if (listeners.get(name) === handler) listeners.delete(name);
    }
  };
  const document = {};
  const context = vm.createContext({ window, document });
  vm.runInContext(source, context);

  function advance(milliseconds) {
    const target = now + milliseconds;
    while (true) {
      const due = timers.filter(timer => !timer.canceled && timer.due <= target)
        .sort((left, right) => left.due - right.due)[0];
      if (!due) break;
      due.canceled = true;
      now = due.due;
      due.callback();
    }
    now = target;
  }

  return { window, document, shell, main, timers, listeners, advance };
}

test('Customer entrance CSS remains 680ms and its safety fallback has margin', () => {
  assert.match(theme, /--portal-customer-motion-entrance:\s*680ms/);
  assert.ok(760 > 680, 'Fallback must outlast the CSS entrance');
});

for (const surface of [
  { label: 'portalAppKind', dataset: { portalAppKind: 'customer' } },
  { label: 'portalSurface', dataset: { portalSurface: 'customer' } }
]) {
  test(`Customer entrance survives its full 680ms animation when ${surface.label} is on an ancestor`, () => {
    const harness = createMotionHarness(surface.dataset);
    harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
    const fallback = harness.timers.find(timer => !timer.canceled);
    assert.equal(fallback?.due, 760, 'Safety timer must account for delayed animation activation');
    harness.advance(679);
    assert.equal(harness.main.getAttribute('data-portal-motion'), 'enter');
    harness.advance(1);
    const animationEnd = harness.listeners.get('animationend');
    assert.equal(typeof animationEnd, 'function');
    animationEnd({ target: harness.main });
    assert.equal(harness.main.getAttribute('data-portal-motion'), null);
  });
}

test('Customer entrance safety fallback clears the marker at 760ms without animationend', () => {
  const harness = createMotionHarness({ portalSurface: 'customer' });
  harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
  harness.advance(759);
  assert.equal(harness.main.getAttribute('data-portal-motion'), 'enter');
  harness.advance(1);
  assert.equal(harness.main.getAttribute('data-portal-motion'), null);
});

test('Non-customer entry keeps the existing 500ms safety fallback', () => {
  const harness = createMotionHarness({ portalAppKind: 'admin' });
  harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
  const fallback = harness.timers.find(timer => !timer.canceled);
  assert.equal(fallback?.due, 500);
  harness.advance(500);
  assert.equal(harness.main.getAttribute('data-portal-motion'), null);
});

test('Delayed customer animation is not canceled by the wall-clock safety timer', () => {
  const harness = createMotionHarness({ portalAppKind: 'customer' });
  const animation = { animationName: 'portal-customer-observable-enter', playState: 'running', currentTime: 550, effect: { getComputedTiming: () => ({ endTime: 680 }) } };
  harness.main.getAnimations = () => [animation];
  harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
  harness.advance(760);
  assert.equal(harness.main.getAttribute('data-portal-motion'), 'enter', '550ms of a 680ms CSS animation must remain visible');
  animation.currentTime = 680;
  harness.listeners.get('animationend')({ target: harness.main });
  assert.equal(harness.main.getAttribute('data-portal-motion'), null);
  harness.advance(1000);
  assert.equal(harness.listeners.size, 0, 'Completed entry must release its listener');
});

test('A customer animation held by a View Transition receives time to start', () => {
  const harness = createMotionHarness({ portalSurface: 'customer' });
  const animation = { animationName: 'portal-customer-observable-enter', playState: 'running', currentTime: 0, effect: { getComputedTiming: () => ({ endTime: 680 }) } };
  harness.main.getAnimations = () => [animation];
  harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
  harness.advance(760);
  assert.equal(harness.main.getAttribute('data-portal-motion'), 'enter');
  animation.currentTime = 680;
  harness.listeners.get('animationend')({ target: harness.main });
  assert.equal(harness.main.getAttribute('data-portal-motion'), null);
});

test('A stalled customer animation cannot retain the entrance marker indefinitely', () => {
  const harness = createMotionHarness({ portalSurface: 'customer' });
  harness.main.getAnimations = () => [{ animationName: 'portal-customer-observable-enter', playState: 'running', currentTime: 100, effect: { getComputedTiming: () => ({ endTime: 680 }) } }];
  harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
  harness.advance(760);
  assert.equal(harness.main.getAttribute('data-portal-motion'), 'enter');
  harness.advance(760);
  assert.equal(harness.main.getAttribute('data-portal-motion'), null);
  assert.equal(harness.listeners.size, 0);
});

test('Unrelated and paused animations do not extend the customer safety fallback', () => {
  for (const animation of [
    { animationName: 'unrelated-spinner', playState: 'running', currentTime: 0, effect: { getComputedTiming: () => ({ endTime: Infinity }) } },
    { animationName: 'portal-customer-observable-enter', playState: 'paused', currentTime: 10, effect: { getComputedTiming: () => ({ endTime: 680 }) } },
  ]) {
    const harness = createMotionHarness({ portalAppKind: 'customer' });
    harness.main.getAnimations = () => [animation];
    harness.window.TOANAASPortalMotion.enter(harness.main, 'enter');
    harness.advance(760);
    assert.equal(harness.main.getAttribute('data-portal-motion'), null);
  }
});

test('A completed CSS timeline receives a frame to deliver its queued animationend', () => {
  const h = createMotionHarness({ portalAppKind: 'customer' });
  h.main.getAnimations = () => [{ animationName: 'portal-customer-observable-enter', playState: 'finished', currentTime: 950, effect: { getComputedTiming: () => ({ endTime: 680 }) } }];
  h.window.TOANAASPortalMotion.enter(h.main, 'enter');
  h.advance(760);
  assert.equal(h.main.getAttribute('data-portal-motion'), 'enter', 'Do not cancel a finished animation before its queued end event');
  h.listeners.get('animationend')({ target: h.main });
  assert.equal(h.main.getAttribute('data-portal-motion'), null);
  h.advance(200);
  assert.equal(h.listeners.size, 0);
});

test('First customer render uses its entrance without snapshotting the boot screen', async () => {
  const h = createMotionHarness({ portalAppKind: 'customer', portalSurface: 'customer' });
  h.main.dataset = { portalPresentationPhase: 'entry' };
  h.main.querySelector = selector => selector === '.portal-boot' ? {} : null;
  let snapshots = 0, renders = 0;
  h.document.startViewTransition = apply => { snapshots++; apply(); return { ready: Promise.resolve(), finished: Promise.resolve(), updateCallbackDone: Promise.resolve() }; };
  await h.window.TOANAASPortalMotion.replace(h.shell, h.main, () => { renders++; });
  assert.equal(renders, 1);
  assert.equal(snapshots, 0, 'Initial content must not wait for a native boot-screen snapshot');
  assert.equal(h.main.getAttribute('data-portal-motion'), 'enter');
});

test('Existing customer content and Admin retain the native transition path', async () => {
  for (const [surface, boot] of [['customer', false], ['admin', true]]) {
    const h = createMotionHarness({ portalAppKind: surface, portalSurface: surface });
    h.main.dataset = { portalPresentationPhase: 'entry' };
    h.main.querySelector = () => boot ? {} : null;
    let snapshots = 0, renders = 0;
    h.document.startViewTransition = apply => { snapshots++; apply(); return { ready: Promise.resolve(), finished: Promise.resolve(), updateCallbackDone: Promise.resolve() }; };
    await h.window.TOANAASPortalMotion.replace(h.shell, h.main, () => { renders++; });
    assert.equal(snapshots, 1);
    assert.equal(renders, 1);
  }
});
