import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild,publishReceipt} from './helpers/publishing-child-render.mjs';

const route='/content/publish-review';
const flags=['input_persisted','provider_called','bot_called','job_created','wallet_mutated','payment_started','asset_saved','media_output_created','publish_action_created','delivery_created','fact_checked','rights_verified'];
const context=receipt=>({capabilities:{'publish-review-pack-compose':true},publishReviewPackEnabled:true,publishReviewPackResult:receipt});
const normalizer=renderChild('en',route,context({})).normalizeReviewReceipt;
const plain=value=>JSON.parse(JSON.stringify(value));

test('a validated text-only receipt survives repeated normalization without losing proof or customer copy',()=>{
  const receipt=publishReceipt(),snapshot=plain(receipt);
  const once=normalizer(receipt),twice=normalizer(once);
  assert.deepEqual(plain(once),snapshot);
  assert.deepEqual(plain(twice),snapshot);
  assert.deepEqual(receipt,snapshot,'normalization must not mutate its input');
});

for(const locale of ['vi','en','zh']){
  test(`${locale}: the real page renders the validated customer receipt instead of silently dropping it`,()=>{
    const receipt=publishReceipt();
    receipt.package.caption='<img src=x onerror="window.__unsafe=1"> customer authored';
    const r=renderChild(locale,route,context(receipt));
    assert.ok(r.text.includes('CUSTOMER_TITLE'));
    assert.ok(r.text.includes('#CUSTOMER_TAG'));
    assert.match(r.html,/&lt;img src=x onerror=/);
    assert.doesNotMatch(r.html,/<img src=x|<video\b|<audio\b/);
    assert.equal(r.context.publishReviewPackResult.execution,'web_native_publish_review_text_only');
    for(const flag of flags)assert.equal(r.context.publishReviewPackResult[flag],false,flag);
  });
}

for(const flag of flags){
  test(`receipt proof rejects true or missing ${flag} even when its package is otherwise valid`,()=>{
    for(const mode of ['true','missing']){
      const receipt=publishReceipt();
      if(mode==='true')receipt[flag]=true;else delete receipt[flag];
      assert.deepEqual(plain(normalizer(receipt)),{});
      assert.ok(!renderChild('en',route,context(receipt)).text.includes('CUSTOMER_TITLE'));
    }
  });
}

test('receipt still rejects absent or incorrect execution proof and package-only objects',()=>{
  const receipt=publishReceipt();
  for(const value of [{package:receipt.package},{...receipt,execution:'provider_output'},{...receipt,execution:undefined}]){
    assert.deepEqual(plain(normalizer(value)),{});
    assert.ok(!renderChild('en',route,context(value)).text.includes('CUSTOMER_TITLE'));
  }
});

test('receipt rejects invalid or extra package fields without inventing a result',()=>{
  for(const packageOverride of [{extra:'not allowed'},{title:''},{hashtags:['not_a_hashtag']},{review_checklist:[]}]){
    const receipt=publishReceipt();Object.assign(receipt.package,packageOverride);
    assert.deepEqual(plain(normalizer(receipt)),{});
  }
});

for(const locale of ['vi','en','zh']){
  test(`${locale}: unknown checklist and instruction content is preserved, including prototype-like text`,()=>{
    const receipt=publishReceipt();
    receipt.package.review_checklist=['toString','__proto__','CUSTOMER_GUIDE_3','CUSTOMER_GUIDE_4'];
    receipt.package.copy_instruction='constructor';
    const r=renderChild(locale,route,context(receipt));
    for(const text of [...receipt.package.review_checklist,'constructor'])assert.ok(r.text.includes(text),text);
    assert.ok(!r.text.includes('[object Object]'));
  });
}
