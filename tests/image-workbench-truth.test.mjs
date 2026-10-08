import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = readFileSync(path.join(repo, 'static/portal/portal.js'), 'utf8');
const start = source.indexOf('  function renderInteractiveFeatureWorkbench(');
const end = source.indexOf('\n  function renderWorkspace(', start);
assert.ok(start >= 0 && end > start, 'The production feature-workbench renderer is available');
const render = new Function(`${source.slice(start, end)}\nreturn renderInteractiveFeatureWorkbench;`)();

// These checks catch the actual demo panel being reintroduced ahead of the
// authoritative form: it claims output/readiness and only executes alerts.
for (const route of ['/image/create', '/image/new']) {
  test(`${route} does not offer invented image creation or downloads before a server result`, () => {
    const html = render({ path: route, featureFamily: 'image' }, { capabilities: {}, bridge: { available: false }, wallet: null });
    assert.equal(/onclick\s*=|AI Generated Image|Tác Phẩm AI Sẵn Sàng|Tải Ảnh 4K/i.test(html), false, 'A fake completion/download control is visible');
  });

  test(`${route} does not advertise unverified readiness, price or output specifications`, () => {
    const html = render({ path: route, featureFamily: 'image' }, { capabilities: {}, bridge: { available: false }, wallet: null });
    assert.equal(/Engine Sẵn Sàng|data-status="ready"|-5 Xu|4096 x 4096|300 DPI|Render RTX 4090|1\.4s/i.test(html), false, 'Unverified availability, price or specifications are visible');
  });
}
