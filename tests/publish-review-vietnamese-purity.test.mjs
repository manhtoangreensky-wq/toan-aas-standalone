import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild,publishReceipt} from './helpers/publishing-child-render.mjs';

const viForeign=/\b(?:Web|Portal|request|Prompt|brief|Hashtag|Content Brief|Content Studio|Project|Workboard|CSRF|REF|off|Core Bridge|URL|Bot)\b/i;
for(const locale of ['vi','en','zh']){
  for(const state of ['empty','valid','rejected']){
    test(`${locale}: Publish Review ${state} fixed labels and hints use the selected language`,()=>{
      const receipt=state==='empty'?{}:publishReceipt();
      if(state==='rejected')receipt.provider_called=true;
      const r=renderChild(locale,'/content/publish-review',{capabilities:{'publish-review-pack-compose':true},publishReviewPackEnabled:true,publishReviewPackResult:receipt});
      const visible=r.text+' '+r.attributes;
      if(locale==='vi')assert.doesNotMatch(visible,viForeign);
      if(locale==='en')assert.doesNotMatch(visible,/[À-ỹĐđ]/);
      if(locale==='zh')assert.doesNotMatch(visible,/\bREF\b|\b(?:Content Brief|Content Studio|Project|Workboard|Web|Portal|URL|Bot|CSRF|brief)\b/);
      assert.match(r.html,/data-portal-action="publish-review-pack-compose"/);
      assert.match(r.html,/data-portal-no-transient/);
      assert.doesNotMatch(r.html,/<video\b|<audio\b|output_url|download_url/);
      if(state==='valid'){
        for(const text of ['CUSTOMER_TITLE','CUSTOMER_CAPTION','#CUSTOMER_TAG','CUSTOMER_CTA','CUSTOMER_PROMPT','CUSTOMER_COPY'])assert.ok(r.text.includes(text),text);
        for(const route of ['/content-studio','/workboard'])assert.ok(r.html.includes('href="'+route+'"'));
      }else assert.ok(!r.text.includes('CUSTOMER_TITLE'),'invalid or empty receipt must not render a package');
    });
  }
}

test('the review form never pre-fills invented English hashtags as customer input',()=>{
  for(const locale of ['vi','en','zh']){
    const r=renderChild(locale,'/content/publish-review',{capabilities:{'publish-review-pack-compose':true},publishReviewPackEnabled:true});
    const textarea=r.html.match(/<textarea\b[^>]*name="hashtags"[^>]*>([\s\S]*?)<\/textarea>/);
    assert.ok(textarea);
    assert.equal(textarea[1],'');
  }
});
