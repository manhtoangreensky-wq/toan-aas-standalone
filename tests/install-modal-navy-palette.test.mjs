import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const css = fs.readFileSync('static/portal/portal.css', 'utf8');
const start = css.indexOf('/* Modal Install Guide */');
const end = css.indexOf('/* Modal Install Guide */', start + 1);
const modal = css.slice(start, end > start ? end : start + 6000);

test('install guide modal stays in the approved navy/teal palette', () => {
  assert.ok(start >= 0, 'install modal CSS section exists');
  assert.match(modal, /background:\s*rgba\(3, 20, 43, \.86\)/);
  assert.match(modal, /background:\s*#0f172a\s*!important/);
  assert.match(modal, /background:\s*rgba\(5, 31, 57, \.92\)\s*!important/);
  assert.doesNotMatch(modal, /background:\s*rgba\(0,\s*0,\s*0/);
});
