import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';
import {planId, savedDetailContext} from './helpers/saved-video-detail-context.mjs';

for (const locale of ['vi','en','zh']) {
  const context = savedDetailContext();
  const list = renderChild(locale, '/video-studio/new', context);
  const detail = renderChild(locale, '/video-studio/' + planId, context);
  test(locale + ': dynamic detail group name is localized for the shared navigation frame', () => {
    const label={vi:'Không gian kế hoạch video',en:'Video planning workspace',zh:'视频规划工作区'}[locale];
    assert.equal(detail.html.includes('<div class="portal-eyebrow">'+label+'</div>'),true,'Resolved dynamic page section must already use the active locale, not a raw English group');
  });
  test(locale + ': list prioritizes working create/library controls without intro or boundary cards', () => {
    assert.ok(list.html.includes('data-portal-action="video-plan-create"'));
    assert.ok(list.html.includes('/video-studio/' + planId));
    assert.equal(/class="portal-video-studio-intro"|portal-video-studio-boundary/.test(list.html),false,'No redundant intro/boundary panel');
  });
  test(locale + ': detail keeps editor/scenes/history but removes duplicated technical panels', () => {
    assert.ok(detail.html.includes('data-portal-action="video-plan-update"'));
    assert.ok(detail.html.includes('data-portal-action="video-scene-update"'));
    assert.ok(detail.html.includes('data-portal-action="video-plan-restore-version"'));
    assert.ok(detail.html.includes('CUSTOMER_OLD_BRIEF'));
    assert.equal(/portal-video-studio-boundary/.test(detail.html),false,'No repeated boundary panel');
  });
  for (const kind of ['image','reference']) test(locale + ':' + kind + ': finite generated tag decoration disappears, custom tags/raw fields remain', () => {
    const raw = savedDetailContext('draft',kind), snapshot=JSON.stringify(raw);
    const result = renderChild(locale,'/video-studio/'+planId,raw);
    const chips = [...result.html.matchAll(/<div class="portal-video-studio-tags">([\s\S]*?)<\/div>/g)].map(match=>match[1]).join(' ');
    assert.ok(chips.includes('CUSTOMER_TAG'));
    assert.doesNotMatch(chips, /image-motion-planner|reference-format-planner|style-cinematic|motion-hero_hold|music-none|direction-product_ad|platform-tiktok|goal-educate|tone-clear|>scene-1</);
    assert.ok(result.html.includes('name="tags"'));
    assert.ok(result.html.includes(kind==='image'?'image-motion-planner, style-cinematic':'reference-format-planner, direction-product_ad'));
    assert.equal(JSON.stringify(raw), snapshot);
    assert.equal(JSON.stringify(result.context.videoPlanDetail.plan.tags),JSON.stringify(raw.videoPlanDetail.plan.tags));
  });
  test(locale + ': ordinary/lookalike/prototype customer tags are not translated or hidden', () => {
    const tags=['style-cinematic','style-customer','__proto__','constructor','scene-99','CUSTOMER_TAG'];
    const result=renderChild(locale,'/video-studio/'+planId,savedDetailContext('draft','custom',tags));
    const chips=[...result.html.matchAll(/<div class="portal-video-studio-tags">([\s\S]*?)<\/div>/g)].map(match=>match[1]).join(' ');
    for(const tag of tags) assert.ok(chips.includes(tag),tag);
  });
  test(locale + ': ambiguous origin tags stay visible without guessing provenance', () => {
    const tags=['image-motion-planner','reference-format-planner','style-cinematic','CUSTOMER_TAG'];
    const result=renderChild(locale,'/video-studio/'+planId,savedDetailContext('draft','custom',tags));
    const chips=[...result.html.matchAll(/<div class="portal-video-studio-tags">([\s\S]*?)<\/div>/g)].map(match=>match[1]).join(' ');
    for(const tag of tags) assert.ok(chips.includes(tag),tag);
  });
  for (const state of ['readonly','approved','archived','guarded','missing','loading','failed']) test(locale+':'+state+': meaningful state and records remain',()=>{
    const result=renderChild(locale,'/video-studio/'+planId,savedDetailContext(state));
    assert.ok(result.html.length>200);
    if(['guarded','missing','loading','failed'].includes(state)) {
      assert.ok(result.html.includes('href="/video-studio"'));
      assert.equal(result.html.includes('data-portal-action="video-plan-update"'),false);
    } else {
      assert.ok(result.html.includes('CUSTOMER_TITLE'));
      const form=result.html.match(/<form\b[^>]*data-portal-action="video-plan-update"[\s\S]*?<\/form>/)?.[0]||'';
      assert.ok(form.includes('name="brief"'));
      const submit=form.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0]||'';
      assert.match(submit,/\bdisabled\b/);
    }
  });
}
