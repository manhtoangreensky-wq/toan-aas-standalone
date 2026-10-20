import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
test('account avatar presets are inline and do not depend on remote image providers', () => {
  assert.doesNotMatch(source, /https:\/\/api\.dicebear\.com\//);
  assert.match(source, /function avatarPresetDataUri\(/);
  assert.match(source, /data:image\/svg\+xml/);
  assert.match(source, /data-portal-action="select-avatar-preset"/);
});
