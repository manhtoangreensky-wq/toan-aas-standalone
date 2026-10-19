import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const catalogueStart = source.indexOf('const ADMIN_GENERIC_MESSAGES = {');
const zhStart = source.indexOf('    zh: {', catalogueStart);
const zhEnd = source.indexOf('  };', zhStart);
assert.ok(catalogueStart >= 0 && zhStart > catalogueStart && zhEnd > zhStart, 'Admin generic Chinese catalogue must remain present');
const zh = source.slice(zhStart, zhEnd);

test('Chinese Admin generic table chrome does not leak canonical jargon', () => {
  const keys = [
    'adminGeneric.guard.canonicalTitle',
    'adminGeneric.guard.requiredBody',
    'adminGeneric.refresh.guardedTitle',
    'adminGeneric.data.body',
    'adminGeneric.pricing.emptyBody',
    'adminGeneric.access.incidentReadOnlyBody',
    'adminGeneric.access.writeBody',
    'adminGeneric.access.readOnlyBody',
    'adminGeneric.jobs.column.canonicalCost',
    'adminGeneric.jobs.column.actions',
    'adminGeneric.providerFeature.emptyTitle',
    'adminGeneric.fallbackTable.emptyTitle'
  ];
  for (const key of keys) {
    const line = zh.split('\n').find((candidate) => candidate.includes(`"${key}"`));
    assert.ok(line, `missing Chinese Admin copy: ${key}`);
    assert.doesNotMatch(line, /\bcanonical\b/i, `Chinese Admin copy leaked canonical jargon: ${key}`);
  }
  const valueLines = zh.split('\n').filter((line) => /\"[^\"]+\"\s*:\s*\"/.test(line));
  const leaked = valueLines.filter((line) => line.replace(/^\s*\"[^\"]+\"\s*:\s*/, '').match(/\bcanonical\b/i));
  assert.deepEqual(leaked, [], 'Chinese Admin generic values must not contain canonical jargon');
});
