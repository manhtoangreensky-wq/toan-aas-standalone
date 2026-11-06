import assert from 'node:assert/strict';
import test from 'node:test';
import {actionContext,reviewActionRuntime} from './helpers/publish-review-action-runtime.mjs';
const copy=value=>JSON.parse(JSON.stringify(value));
const outcomes=['valid','guarded','guarded_error','transport_error'];
for(const transition of ['route','epoch','account','signedout','disabled','capability','csrf']){
  for(const outcome of outcomes){
    test(`a ${outcome} response cannot alter state, feedback or controls after ${transition} changes`,async()=>{
      const h=reviewActionRuntime(),task=h.run();assert.equal(h.pending.length,1);
      const current=copy(actionContext());let epoch=false;
      if(transition==='route')current.path='/account';
      if(transition==='epoch')epoch=true;
      if(transition==='account')Object.assign(current,actionContext('B'));
      if(transition==='signedout')current.session.authenticated=false;
      if(transition==='disabled')current.publishReviewPackEnabled=false;
      if(transition==='capability')current.capabilities['publish-review-pack-compose']=false;
      if(transition==='csrf')current.session.csrfToken='synthetic-rotated';
      h.replace(current,{epoch,disabled:true});const snapshot=copy(h.state);
      h.settle(0,outcome);await task;
      assert.deepEqual(copy(h.state),snapshot,'late response must not merge into the new context');
      assert.equal(h.toasts.length,0,'late response must not announce in the new context');
      assert.equal(h.button.disabled,true,'late cleanup must not unlock the new context');
    });
  }
}
for(const outcome of outcomes){
  test(`the older ${outcome} response cannot override a newer compose or clear its busy state`,async()=>{
    const h=reviewActionRuntime(),old=h.run(),latest=h.run();assert.equal(h.pending.length,2);
    const snapshot=copy(h.state);h.settle(0,outcome,'OLD');await old;
    assert.deepEqual(copy(h.state),snapshot);
    assert.equal(h.toasts.length,0);
    assert.equal(h.button.disabled,true);
    h.settle(1,'valid','NEW');await latest;
    assert.equal(h.state.publishReviewPackResult.package.title,'VALUE_NEW');
    assert.equal(h.button.disabled,false);
  });
}
test('current native compose still accepts a proved receipt without a Bot bridge',async()=>{
  const h=reviewActionRuntime(),task=h.run();assert.equal(h.pending.length,1);h.settle(0,'valid','CURRENT');await task;
  assert.equal(h.state.publishReviewPackResult.package.title,'VALUE_CURRENT');
  assert.equal(h.button.disabled,false);assert.equal(h.toasts.length,1);
  assert.equal(h.state.bridge.available,false);
});

for(const locale of ['vi','en','zh']){
  test(`${locale}: fixed success feedback follows the selected interface language`,async()=>{
    const h=reviewActionRuntime(locale),task=h.run();h.settle(0,'valid','CURRENT');await task;
    assert.equal(h.toasts.length,1);
    const text=h.toasts[0].textContent;
    assert.ok(text.length>0);
    if(locale==='vi')assert.match(text,/Đã tạo/);
    if(locale==='en')assert.match(text,/Review text created/);
    if(locale==='zh')assert.match(text,/已创建/);
    if(locale!=='vi')assert.doesNotMatch(text,/Đã tạo|Nội dung|Yêu cầu|Máy chủ/);
  });
}

for(const state of ['route','account','signedout','disabled','capability','csrf']){
  test(`a detached or unavailable ${state} context cannot start a compose request`,async()=>{
    const h=reviewActionRuntime(),current=copy(actionContext());
    if(state==='route')current.path='/account';
    if(state==='account')current.account={};
    if(state==='signedout')current.session.authenticated=false;
    if(state==='disabled')current.publishReviewPackEnabled=false;
    if(state==='capability')current.capabilities['publish-review-pack-compose']=false;
    if(state==='csrf')current.session.csrfToken='';
    h.replace(current,{epoch:false,disabled:true});const snapshot=copy(h.state),task=h.run(),calls=h.pending.length;
    if(calls)h.settle(0,'valid','IGNORED');await task;
    assert.equal(calls,0);assert.deepEqual(copy(h.state),snapshot);assert.equal(h.toasts.length,0);assert.equal(h.button.disabled,true);
  });
}
for(const kind of ['unsafe','wrong_execution']){
  test(`a current ${kind} receipt is still rejected instead of being displayed`,async()=>{
    const h=reviewActionRuntime(),snapshot=copy(h.state.publishReviewPackResult),task=h.run();
    h.settle(0,kind,'UNSAFE');await task;
    assert.deepEqual(copy(h.state.publishReviewPackResult),snapshot);assert.equal(h.toasts.length,1);assert.equal(h.button.disabled,false);
  });
}
