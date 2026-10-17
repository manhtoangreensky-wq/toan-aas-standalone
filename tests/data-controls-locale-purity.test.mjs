import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const portalSource = fs.readFileSync('static/portal/portal.js', 'utf8');
const viStart = source.indexOf('Object.assign(DATA_CONTROLS_MESSAGES.vi, {');
const enStart = source.indexOf('Object.assign(DATA_CONTROLS_MESSAGES.en, {', viStart);
assert.ok(viStart >= 0 && enStart > viStart, 'Data Controls Vietnamese catalogue must remain present');
const vi = source.slice(viStart, enStart);
const values = [...vi.matchAll(/^\s*"(?:accountCenter\.dataControls|page\.dataControls)\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);
assert.equal(values.length, 99, 'Data Controls must keep the complete fixed catalogue');

test('Vietnamese Data Controls fixed chrome does not mix generic English terms', () => {
  const visibleCopy = values.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(
    visibleCopy,
    /\b(?:data control center|data controls|signed|web|export|projection|portal|authoring|policy|provider|job|asset vault|file|metadata|memory center|prompt library|workboard|template|event|reference|review|identity|record|inventory|category|payment|output|support evidence|attachment|browser|password|session|token|account|canonical|human|server-side|owner|check|confirmation|idempotency|revision|audit|bridge|wallet|external|notification|response|boundary|raw|release|ticket)\b/i,
    'generic English leaked into the Vietnamese Data Controls catalogue',
  );
});

test('Data Controls renderer fallbacks stay Vietnamese when a catalogue key is missing', () => {
  const renderStart = portalSource.indexOf('function renderAccountDataControls(');
  const renderEnd = portalSource.indexOf('const GOVERNANCE_DOCUMENT_LABELS', renderStart);
  assert.ok(renderStart >= 0 && renderEnd > renderStart, 'Data Controls renderer must remain present');
  const renderer = portalSource.slice(renderStart, renderEnd);
  const fallbacks = [...renderer.matchAll(/copy\("[^"]+",\s*"([^"\\]*(?:\\.[^"\\]*)*)"/g)].map((match) => match[1]);
  assert.ok(fallbacks.length >= 40, 'Data Controls renderer must keep explicit safe fallbacks');
  const visibleCopy = fallbacks.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(
    visibleCopy,
    /\b(?:data control center|data controls|signed|web|export|projection|portal|authoring|policy|provider|job|asset vault|file|metadata|memory center|prompt library|workboard|template|event|reference|review|identity|record|inventory|category|payment|output|support evidence|attachment|browser|password|session|token|account|canonical|human|server-side|owner|check|confirmation|idempotency|revision|audit|bridge|wallet|external|notification|response|boundary|raw|release|ticket|bounded)\b/i,
    'generic English leaked into Data Controls renderer fallbacks',
  );
});
