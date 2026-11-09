const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync('static/portal/portal-motion.js', 'utf8').replace(/\r\n/g, '\n');
const a = source.indexOf('    const getScrollPosition = () => (');
const b = source.indexOf('\n    const resetPointer', a);
const c = source.indexOf('    const syncHeader = () => {');
const d = source.indexOf('\n    const onScroll', c);
assert.ok(a > 0 && b > a && c > b && d > c);

function run(isWindowOwner, position) {
  const events = [];
  const attributes = new Map();
  const read = name => { events.push(`read:${name}`); return position; };
  const window = { innerHeight: 800, get scrollY() { return read('scrollY'); } };
  const owner = { get scrollTop() { return read('scrollTop'); }, clientHeight: 800, scrollHeight: 2000 };
  const root = { getAttribute: k => attributes.get(k), setAttribute: (k, v) => { events.push(`write:${k}`); attributes.set(k, v); } };
  const header = { setAttribute: (k, v) => { events.push(`write:${k}=${v}`); } };
  const layer = { getBoundingClientRect: () => { events.push('read:layerRect'); return { top: 100, height: 600 }; }, getAttribute: () => 'hero' };
  const context = vm.createContext({
    window, document: { documentElement: { scrollHeight: 2000 } },
    scrollOwner: isWindowOwner ? window : owner, isWindowOwner, isCurrentMount: () => true,
    scrollFrame: 1, root, header, hero: null, scrollLayers: [layer],
    clamp: (v, min, max) => Math.min(max, Math.max(min, Number(v) || 0)),
    setStyleProperty: (_el, key) => events.push(`write:${key}`),
  });
  vm.runInContext(source.slice(a, b) + source.slice(c, d) + '\nsyncHeader();', context);
  const firstWrite = events.findIndex(e => e.startsWith('write:'));
  return { events, lateReads: events.slice(firstWrite + 1).filter(e => e.startsWith('read:')) };
}

for (const windowOwner of [true, false]) {
  for (const position of [0, 20, 21, 300]) {
  test(`Landing ${windowOwner ? 'window' : 'workspace'} at ${position}px finishes reads before writes`, () => {
    const result = run(windowOwner, position);
    assert.deepEqual(result.lateReads, [], 'scroll position must not be re-read after inherited progress variables change');
    assert.equal(result.events.filter(e => e === `read:${windowOwner ? 'scrollY' : 'scrollTop'}`).length, 1);
    assert.ok(result.events.includes(`write:data-landing-motion-header=${position > 20 ? 'compact' : 'default'}`));
  });
  }
}
