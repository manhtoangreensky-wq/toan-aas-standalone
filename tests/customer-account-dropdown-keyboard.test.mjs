import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const start = source.indexOf('    window.addEventListener("keydown", (event) => {', source.indexOf('  function bindInteractions()'));
const end = source.indexOf('    window.addEventListener("resize", closeSidebarAboveMobileBreakpoint);', start);
assert.ok(start > 0 && end > start);
const keydownSource = source.slice(start, end);

function harness({ open = true, palette = false } = {}) {
  let handler, prevented = false, paletteClosed = 0;
  const dropdown = { hidden: !open };
  const trigger = { expanded: String(open), focused: false, setAttribute(name, value) { if (name === 'aria-expanded') this.expanded = value; }, focus(options) { this.focused = options?.preventScroll === true; } };
  const document = { addEventListener(type, callback) { if (type === 'keydown') handler = callback; }, querySelector(selector) { if (selector === '[data-portal-user-dropdown]') return dropdown; if (selector === '[data-portal-action="toggle-user-dropdown"]') return trigger; return null; } };
  const window = { addEventListener(type, callback) { if (type === 'keydown') handler = callback; } };
  vm.runInNewContext(keydownSource, { document, window, HTMLElement: class HTMLElement {}, isCommandPaletteOpen: () => palette, closeCommandPalette: () => { paletteClosed++; }, openCommandPalette() {} });
  return { dropdown, trigger, press(key) { handler({ key, target: {}, ctrlKey: false, metaKey: false, preventDefault() { prevented = true; } }); }, state: () => ({ prevented, paletteClosed }) };
}

test('Escape closes the account dropdown, resets expanded state and restores its trigger focus', () => {
  const h = harness(); h.press('Escape');
  assert.equal(h.dropdown.hidden, true);
  assert.equal(h.trigger.expanded, 'false');
  assert.equal(h.trigger.focused, true);
  assert.equal(h.state().prevented, true);
});

test('Other keys and a closed account dropdown leave account-menu state alone', () => {
  const h = harness(); h.press('Enter'); assert.equal(h.dropdown.hidden, false); assert.equal(h.trigger.focused, false);
  const closed = harness({ open: false }); closed.press('Escape'); assert.equal(closed.trigger.focused, false); assert.equal(closed.state().prevented, false);
});

test('An open command palette retains Escape priority', () => {
  const h = harness({ palette: true }); h.press('Escape');
  assert.equal(h.state().paletteClosed, 1); assert.equal(h.dropdown.hidden, false);
});
