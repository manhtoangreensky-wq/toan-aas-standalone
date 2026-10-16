import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const accountStart = source.indexOf('const ACCOUNT_CENTER_MESSAGES = {');
const viStart = source.indexOf('    vi: {', accountStart);
const enStart = source.indexOf('    en: {', viStart);
assert.ok(accountStart >= 0 && viStart > accountStart && enStart > viStart, 'Account Center catalogue must remain present');
const vi = source.slice(viStart, enStart);
const values = [...vi.matchAll(/^\s*"accountCenter\.activity\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);
const metadata = [...vi.matchAll(/^\s*"page\.accountActivity\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);
assert.equal(values.length, 20, 'Account activity must keep the complete fixed catalogue');
assert.equal(metadata.length, 2, 'Account activity page metadata must remain complete');

test('Vietnamese account activity fixed chrome does not mix generic English terms', () => {
  const visibleCopy = values.concat(metadata).join(' | ');
  assert.doesNotMatch(
    visibleCopy,
    /\b(?:job|output|delivery|web|asset|vault|workflow|canonical|queue|runtime|retry|refund|download|engine|browser|provider|metadata|preview|contract|ownership|record|planning|estimate|polling|adapter|lifecycle|ticket|ledger|file|detail|signed|sanitize|audit|history|wallet|credential|target|request|portal|server)\b/i,
    'generic English leaked into the Vietnamese account activity catalogue',
  );
});
