const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');

const source = fs.readFileSync('static/portal/portal-motion.js', 'utf8').replace(/\r\n/g, '\n');

function runtime({ reduced = false, observerEnabled = true } = {}) {
  const events = [];
  const timers = new Map();
  const frames = new Map();
  const mediaListeners = new Set();
  const observers = [];
  const windowListeners = new Map();
  let id = 0;
  const classes = name => {
    const values = new Set();
    return {
      add(...items) { events.push(`write:class:${name}`); items.forEach(item => values.add(item)); },
      remove(...items) { events.push(`write:class:${name}`); items.forEach(item => values.delete(item)); },
      contains: item => values.has(item), values,
    };
  };
  const targets = [
    { name: 'visible-a', top: 40, bottom: 240 },
    { name: 'pending-b', top: 900, bottom: 1100 },
    { name: 'visible-c', top: 300, bottom: 500 },
  ].map(({ name, top, bottom }) => {
    const listeners = new Map();
    const child = {
      classList: classes(`${name}-child`),
      style: {
        setProperty() { events.push(`write:style:${name}-child`); },
        removeProperty() { events.push(`write:style:${name}-child`); },
      },
    };
    return {
      name, child, listeners, classList: classes(name),
      getBoundingClientRect() { events.push(`read:rect:${name}`); return { top, bottom }; },
      closest() { return null; },
      querySelectorAll() { return [child]; },
      addEventListener(type, handler) { listeners.set(type, handler); },
      removeEventListener(type, handler) { if (listeners.get(type) === handler) listeners.delete(type); },
    };
  });
  const root = {
    querySelectorAll(selector) {
      if (selector.includes('[data-dashboard-start-guide]')) return [];
      return targets;
    },
  };
  const media = {
    get matches() { return reduced; },
    addEventListener(_type, fn) { mediaListeners.add(fn); },
    removeEventListener(_type, fn) { mediaListeners.delete(fn); },
  };
  const window = {
    innerHeight: 800, matchMedia: () => media,
    setTimeout(fn) { const key = ++id; timers.set(key, fn); return key; },
    clearTimeout(key) { timers.delete(key); },
    requestAnimationFrame(fn) { const key = ++id; frames.set(key, fn); return key; },
    cancelAnimationFrame(key) { frames.delete(key); },
    addEventListener(type, fn) { windowListeners.set(type, fn); },
    removeEventListener(type, fn) { if (windowListeners.get(type) === fn) windowListeners.delete(type); },
  };
  if (observerEnabled) {
    window.IntersectionObserver = class {
      constructor(callback) { this.callback = callback; this.observed = new Set(); this.disconnected = false; observers.push(this); }
      observe(target) { this.observed.add(target); }
      unobserve(target) { this.observed.delete(target); }
      disconnect() { this.disconnected = true; this.observed.clear(); }
    };
  }
  const context = vm.createContext({
    window,
    document: { documentElement: { get clientHeight() { events.push('read:viewport'); return 800; } } },
  });
  vm.runInContext(source, context, { filename: 'portal-motion.js' });
  return { api: window.TOANAASPortalMotion, root, targets, events, timers, frames, observers, mediaListeners, windowListeners,
    reduce() { reduced = true; [...mediaListeners].forEach(fn => fn({ matches: true })); },
  };
}

test('Mount snapshots three viewport memberships before mutating any target', () => {
  const app = runtime();
  app.api.mountWorkspace(app.root);
  const firstWrite = app.events.findIndex(event => event.startsWith('write:'));
  const lateReads = app.events.slice(firstWrite + 1).filter(event => event.startsWith('read:'));
  assert.deepEqual(lateReads, []);
  assert.equal(app.events.filter(event => event.startsWith('read:rect:')).length, 3);
  assert.equal(app.targets[0].classList.contains('is-pending'), false);
  assert.equal(app.targets[1].classList.contains('is-pending'), true);
  assert.equal(app.targets[2].classList.contains('is-pending'), false);
  assert.equal(app.observers[0].observed.size, 1);
  app.api.unmountWorkspace();
});

test('settleVisible false keeps all three pending without geometry reads', () => {
  const app = runtime();
  app.api.mountWorkspace(app.root, { settleVisible: false });
  assert.equal(app.events.filter(event => event.startsWith('read:')).length, 0);
  app.targets.forEach(target => assert.equal(target.classList.contains('is-pending'), true));
  assert.equal(app.observers[0].observed.size, 3);
  assert.equal(app.timers.size, 1);
  app.api.unmountWorkspace();
});

test('initial reduced motion does not read geometry or decorate targets', () => {
  const app = runtime({ reduced: true });
  app.api.mountWorkspace(app.root);
  assert.deepEqual(app.events, []);
  assert.equal(app.observers.length, 0);
  assert.equal(app.timers.size, 0);
});

for (const dynamicReduce of [false, true]) {
  test(`${dynamicReduce ? 'Dynamic reduction' : 'Unmount'} cleans resources and invalidates stale callbacks`, () => {
    const app = runtime();
    app.api.mountWorkspace(app.root);
    const observer = app.observers[0];
    const timer = [...app.timers.values()][0];
    const focus = app.targets[1].listeners.get('focusin');
    app.windowListeners.get('scroll')();
    assert.equal(app.frames.size, 1);
    const frame = [...app.frames.values()][0];
    if (dynamicReduce) app.reduce(); else app.api.unmountWorkspace();
    assert.equal(observer.disconnected, true);
    assert.equal(app.timers.size, 0);
    assert.equal(app.frames.size, 0);
    assert.equal(app.mediaListeners.size, 0);
    assert.equal(app.windowListeners.size, 0);
    app.targets.forEach(target => {
      assert.equal(target.listeners.size, 0);
      assert.equal(target.classList.values.size, 0);
      assert.equal(target.child.classList.values.size, 0);
    });
    app.events.length = 0;
    observer.callback([{ target: app.targets[1], isIntersecting: true }]);
    timer(); frame(); focus({ currentTarget: app.targets[1] });
    assert.deepEqual(app.events, []);
  });
}

test('Missing observer still reveals pending targets immediately', () => {
  const app = runtime({ observerEnabled: false });
  app.api.mountWorkspace(app.root, { settleVisible: false });
  app.targets.forEach(target => {
    assert.equal(target.classList.contains('is-pending'), false);
    assert.equal(target.classList.contains('is-visible'), true);
  });
  app.api.unmountWorkspace();
});
