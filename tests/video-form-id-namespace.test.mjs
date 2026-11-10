import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';
import {planId,savedDetailContext} from './helpers/saved-video-detail-context.mjs';

function multiScene(state) {
  const context=savedDetailContext(state), original=context.videoPlanDetail.scenes[0];
  context.videoPlanDetail.scenes=[1,2,3].map((index)=>({...original,
    id:`33333333-3333-4333-8333-33333333333${index}`,ordinal:index,title:'CUSTOMER_SCENE_'+index}));
  context.videoPlanDetail.plan.scene_count=3;
  return context;
}
const attributes=tag=>Object.fromEntries([...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map(match=>[match[1],match[2]]));
for(const locale of ['vi','en','zh']) {
  for(const state of ['draft','readonly','approved','archived']) {
    const raw=multiScene(state), snapshot=JSON.stringify(raw), r=renderChild(locale,'/video-studio/'+planId,raw);
    const tags=[...r.html.matchAll(/<[a-z][^>]*>/gi)].map(match=>({tag:match[0],attrs:attributes(match[0])}));
    const forms=[...r.html.matchAll(/<form\b[^>]*>[\s\S]*?<\/form>/g)].map(match=>match[0]);
    test(locale+':'+state+': document field/help IDs are unique across all five forms',()=>{
      const ids=tags.map(item=>item.attrs.id).filter(Boolean);
      const duplicates=ids.filter((id,index)=>ids.indexOf(id)!==index);
      assert.deepEqual([...new Set(duplicates)],[],'No repeated field/help ID');
      assert.equal(forms.length,5);
      assert.equal(JSON.stringify(raw),snapshot);
    });
    test(locale+':'+state+': every label/help reference belongs to exactly its own control',()=>{
      for(const form of forms) {
        const controls=[...form.matchAll(/<(?:input|select|textarea)\b[^>]*>/g)].map(match=>attributes(match[0]));
        for(const match of form.matchAll(/<label\b[^>]*>/g)) {
          const target=attributes(match[0]).for;
          assert.ok(target);
          assert.equal(tags.filter(item=>item.attrs.id===target).length,1,'Native document.getElementById cannot select a control from another form');
          assert.equal(controls.filter(control=>control.id===target).length,1,'Label target is in the same form');
        }
        for(const control of controls) for(const id of (control['aria-describedby']||'').split(/\s+/).filter(Boolean)) {
          assert.equal(tags.filter(item=>item.attrs.id===id).length,1,'Description ID unique');
          assert.equal([...form.matchAll(/\bid="([^"]*)"/g)].filter(match=>match[1]===id).length,1,'Description lives with its control');
        }
      }
    });
  }
  test(locale+': new-plan page retains one complete labelled creation form',()=>{
    const raw=savedDetailContext(),r=renderChild(locale,'/video-studio/new',raw);
    assert.equal([...r.html.matchAll(/<form\b/g)].length,1);
    assert.ok(r.html.includes('data-portal-action="video-plan-create"'));
    const controls=[...r.html.matchAll(/<(?:input|select|textarea)\b[^>]*>/g)].map(match=>attributes(match[0]));
    assert.equal(controls.length,10);
    for(const control of controls) assert.equal([...r.html.matchAll(/<label\b[^>]*>/g)].filter(match=>attributes(match[0]).for===control.id).length,1);
  });
}
