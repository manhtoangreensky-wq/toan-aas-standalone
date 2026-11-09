import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const css = fs.readFileSync('static/portal/portal-theme.css', 'utf8');
test('Voice Clone summary has the scoped mobile touch contract', () => {
  const start = css.indexOf('.portal-feature-workspace--voice-task .portal-voice-clone-steps > summary');
  assert.ok(start >= 0);
  const block = css.slice(start, css.indexOf('}', start) + 1);
  assert.match(block, /min-height:\s*44px/);
  assert.match(block, /padding-block:\s*10px/);
});
