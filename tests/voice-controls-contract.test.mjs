import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const voiceFieldStart = source.indexOf('    voice: [');
const voiceFieldEnd = source.indexOf('    voiceClone:', voiceFieldStart);
assert.ok(voiceFieldStart >= 0 && voiceFieldEnd > voiceFieldStart, 'voice field definitions must remain discoverable');
const voiceFieldSource = source.slice(voiceFieldStart, voiceFieldEnd);
const start = source.indexOf('  function renderFields(');
const end = source.indexOf('  function statusMessage(', start);
assert.ok(start >= 0 && end > start, 'renderFields must remain discoverable');

const escape = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

const context = {
  uiText: (_key, fallback) => fallback,
  safeText: escape,
  pdfVaultItems: () => [],
  imageVaultItems: () => [],
  vaultBytes: () => '0 B'
};
vm.createContext(context);
vm.runInContext(`const safeText = ${escape.toString()};\n${source.slice(start, end)}`, context);

const voiceControls = [
  {
    name: 'speed',
    label: 'Tốc độ đọc',
    type: 'number',
    defaultValue: '1.0',
    min: 0.1,
    max: 2,
    step: 0.05,
    presets: [
      { value: '0.85', label: 'Chậm' },
      { value: '1.0', label: 'Chuẩn' },
      { value: '1.2', label: 'Nhanh' }
    ]
  },
  {
    name: 'volume_percent',
    label: 'Âm lượng (%)',
    type: 'number',
    defaultValue: '100',
    min: 0,
    max: 200,
    step: 10,
    range: { ariaLabel: 'Thanh âm lượng' }
  }
];

test('Voice controls expose numeric speed with presets and a single payload field', () => {
  const html = context.renderFields(voiceControls, true, {}, {});
  assert.match(html, /<input[^>]*name="speed"(?=[^>]*type="number")(?=[^>]*min="0\.1")(?=[^>]*max="2")(?=[^>]*step="0\.05")(?=[^>]*value="1\.0")[^>]*>/);
  assert.match(html, /data-portal-field-preset="speed"/);
  assert.match(html, /data-portal-field-preset="speed"[\s\S]*value="0\.85"/);
  assert.equal((html.match(/name="speed"/g) || []).length, 1, 'preset control must not duplicate the submitted speed field');
});

test('Voice volume exposes a 0–200 range synced to one numeric payload field', () => {
  const html = context.renderFields(voiceControls, true, {}, {});
  assert.match(html, /<input[^>]*type="range"[^>]*data-portal-range-sync="volume_percent"(?=[^>]*min="0")(?=[^>]*max="200")(?=[^>]*step="10")(?=[^>]*value="100")[^>]*>/);
  assert.match(html, /<input[^>]*name="volume_percent"(?=[^>]*type="number")(?=[^>]*min="0")(?=[^>]*max="200")(?=[^>]*step="10")(?=[^>]*value="100")[^>]*>/);
  assert.equal((html.match(/name="volume_percent"/g) || []).length, 1, 'range control must not create a second submitted field');
});

test('Voice speed and volume controls use the reviewed locale catalogue and no legacy symbolic speed values', () => {
  assert.match(voiceFieldSource, /labelKey: "field\.speed\.label"/);
  assert.match(voiceFieldSource, /helpKey: "field\.speed\.help"/);
  assert.match(voiceFieldSource, /labelKey: "field\.volume_percent\.label"/);
  assert.match(voiceFieldSource, /helpKey: "field\.volume_percent\.help"/);
  assert.match(voiceFieldSource, /labelKey: "option\.speed\.0\.85"/);
  assert.match(voiceFieldSource, /labelKey: "option\.speed\.1\.0"/);
  assert.match(voiceFieldSource, /labelKey: "option\.speed\.1\.2"/);
  assert.doesNotMatch(voiceFieldSource, /options: \["1\.0", "0\.85", "1\.2", "normal", "slow", "fast"\]/);
});
