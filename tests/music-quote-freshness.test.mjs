import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
function extract(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, `${name} must exist`);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
function runtime() {
  const ctx = {
    MUSIC_PRODUCT_ROUTES: ['/music/create', '/music/song'],
  };
  vm.createContext(ctx); vm.runInContext([
    extract('flowQuoteExpiry'), extract('flowHasFreshEstimate'), extract('voiceQuoteExpiryState'),
    extract('voiceQuoteAmount'), extract('musicQuoteHasEdits'), extract('musicQuoteState')
  ].join('\n'), ctx);
  return ctx;
}
const page = { fields: [{name:'brief',type:'text'}, {name:'tier',type:'select'}, {name:'duration_seconds',type:'number'}, {name:'lyrics',type:'textarea'}] };
const fresh = {input:{brief:'A',tier:'standard',duration_seconds:'30',lyrics:'L'}, phase:'estimate', status:'awaiting_confirm', estimateFingerprint:'fp', webQuoteReceipt:'A'.repeat(32), data:{estimate:{available:true,content:{estimated_xu:120},tier_required:false,scene_count_required:false}}};

test('Music accepts a real zero price but blocks unknown or invalid prices', () => {
  const ctx = runtime();
  assert.equal(ctx.musicQuoteState(page, {...fresh, data:{...fresh.data,estimate:{...fresh.data.estimate,content:{estimated_xu:0}}}}, fresh.input).confirmAllowed, true);
  for (const amount of [null, undefined, -1, '0', Infinity]) {
    const estimate = {...fresh.data.estimate, content: amount === null ? {} : {estimated_xu:amount}};
    assert.equal(ctx.musicQuoteState(page, {...fresh, data:{...fresh.data, estimate}}, fresh.input).confirmAllowed, false);
  }
});

test('Music detects changed declared fields and ignores unrelated values', () => {
  const ctx = runtime();
  assert.equal(ctx.musicQuoteHasEdits(page, fresh, {...fresh.input, lyrics:'L'}), false);
  assert.equal(ctx.musicQuoteHasEdits(page, fresh, {...fresh.input, tier:'premium'}), true);
  assert.equal(ctx.musicQuoteHasEdits(page, fresh, {...fresh.input, upload_ids:'new-file'}), false);
});

test('Music expiry and invalid freshness block confirmation without mutation', () => {
  const ctx = runtime();
  assert.equal(ctx.musicQuoteState(page, {...fresh, data:{...fresh.data, quote_expires_at:new Date(Date.now()-1).toISOString()}}, fresh.input).confirmAllowed, false);
  assert.equal(ctx.musicQuoteState(page, {...fresh, estimateFingerprint:''}, fresh.input).confirmAllowed, false);
});
