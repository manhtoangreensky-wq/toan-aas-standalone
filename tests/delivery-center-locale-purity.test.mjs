import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const viStart = source.indexOf('Object.assign(DELIVERY_CENTER_MESSAGES.vi, {');
const enStart = source.indexOf('Object.assign(DELIVERY_CENTER_MESSAGES.en, {', viStart);
assert.ok(viStart >= 0 && enStart > viStart, 'Delivery Center Vietnamese catalogue must remain present');
const vi = source.slice(viStart, enStart);
const values = [...vi.matchAll(/^\s*"deliveryCenter\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);
assert.ok(values.length > 100, 'Delivery Center Vietnamese catalogue should cover the full fixed chrome');

test('Vietnamese Delivery Center fixed chrome does not mix generic English terms', () => {
  const visibleCopy = values.join(' | ');
  assert.doesNotMatch(
    visibleCopy,
    /\b(?:job|output|delivery|web|asset|vault|workflow|canonical|queue|runtime|retry|refund|download|engine|browser|provider|metadata|preview|contract|ownership|record|planning|estimate|polling|adapter|lifecycle|ticket|ledger|file|detail)\b/i,
    'generic English leaked into the Vietnamese Delivery Center catalogue',
  );
  for (const allowed of ['Core Bridge', 'Bot', 'URL', 'ID', 'API', 'OTP', 'CVV', 'TXID', 'QR', 'CSRF', 'P0']) {
    assert.equal(typeof allowed, 'string');
  }
});
