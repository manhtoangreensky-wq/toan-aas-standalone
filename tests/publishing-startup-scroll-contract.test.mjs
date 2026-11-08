import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');

test('non-hydration startup resets scroll without synchronously reading scrollTop', () => {
  assert.match(source, /if \(workspace && "scrollTop" in workspace\) workspace\.scrollTop = 0;/);
  assert.doesNotMatch(source, /typeof workspace\.scrollTop === "number"/);
  const renderStart = source.indexOf('    function renderShell() {');
  const renderEnd = source.indexOf('      syncAdminDataViewRows(main);', renderStart);
  const render = source.slice(renderStart, renderEnd);
  assert.match(render, /if \(!isHydration\) \{/);
  assert.ok(render.includes('"scrollTop" in workspace'));
});
