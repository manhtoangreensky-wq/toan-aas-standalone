import assert from 'node:assert/strict';import test from 'node:test';
import './reference-feedback-layout-lifecycle.test.mjs';
import {createReferenceRuntime,original,resultFor,route} from './helpers/reference-format-currentness-runtime.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
for(const scenario of ['route-away','new-session','unsigned','clear-refresh'])for(const outcome of ['success','error'])test(`compose ${scenario} late ${outcome} never paints or reports into newer UI`,async()=>{
 const r=createReferenceRuntime(),task=r.action('compose');assert.equal(r.requests.length,1);
 if(scenario==='route-away')r.navigate('/studio');if(scenario==='new-session')r.newSession();if(scenario==='unsigned')r.unsigned();if(scenario==='clear-refresh')r.clear();
 r.replaceControls(true);const before=r.snapshot(),messages=r.toasts.length,mounts=r.mounts.length;
 if(outcome==='success')r.success(0,original().result);else r.fail(0);
 await task;assert.equal(r.snapshot(),before,'Late response must not change newer private state');assert.equal(r.toasts.length,messages,'No stale success/error');assert.equal(r.mounts.length,mounts);assert.equal(r.compose.disabled,true,'Old finally does not unlock newer controls');
});
test('current compose uses actual API, validates complete envelope and keeps current explicit result',async()=>{
 const r=createReferenceRuntime(),task=r.action('compose');assert.equal(r.requests.length,1);assert.equal(r.requests[0].options.headers.get('X-CSRF-Token'),'synthetic-reference-session-a');
 assert.equal(r.requests[0].options.credentials,'same-origin');r.success(0,original().result);await task;
 assert.equal(r.state.referenceFormatPlannerResult.planner.topic,original().source.topic);assert.equal(r.compose.disabled,false);assert.equal(r.toasts.length,1);
});
test('current compose error keeps previously accepted result/source and newer typed fields available for recovery',async()=>{
 const r=createReferenceRuntime(),before=r.snapshot();r.edit({topic:'CUSTOMER_NEW_TOPIC'});const task=r.action('compose');r.fail(0);await task;
 assert.equal(r.snapshot(),before,'A failed recompose never erases the previous valid plan');assert.equal(r.fields.topic,'CUSTOMER_NEW_TOPIC');assert.equal(r.compose.disabled,false);assert.equal(r.toasts.length,1);assert.notEqual(r.state.pageStates[route],'processing');
});
test('newer compose result owns the page when older request completes last',async()=>{
 const r=createReferenceRuntime(),a=r.action('compose');r.edit({topic:'CUSTOMER_TOPIC_B'});const b=r.action('compose');assert.equal(r.requests.length,2);
 r.success(1,resultFor(r.fields,'OWNED_RESULT_B'));await b;const before=r.snapshot(),messages=r.toasts.length;
 r.success(0,original().result);await a;assert.equal(r.snapshot(),before);assert.equal(r.toasts.length,messages);assert.equal(r.state.referenceFormatPlannerResult.planner.title,'OWNED_RESULT_B');
});
test('older compose completion cannot unlock a newer pending compose',async()=>{
 const r=createReferenceRuntime(),a=r.action('compose');r.edit({topic:'CUSTOMER_TOPIC_B'});const b=r.action('compose');assert.equal(r.requests.length,2);r.success(0,original().result);await a;
 const stillBusy=r.compose.disabled;r.success(1,resultFor(r.fields));await b;assert.equal(stillBusy,true);assert.equal(r.compose.disabled,false);
});
test('actual form edit before response keeps current draft and never accepts the captured older input as current',async()=>{
 const r=createReferenceRuntime(),task=r.action('compose');r.edit({topic:'CUSTOMER_EDIT_WHILE_PENDING'});const before=r.snapshot();r.success(0,original().result);await task;
 assert.equal(r.snapshot(),before);assert.equal(r.fields.topic,'CUSTOMER_EDIT_WHILE_PENDING');assert.equal(r.toasts.length,0);assert.equal(r.compose.disabled,false);
});
for(const scenario of ['route-away','new-session','unsigned','clear-refresh'])for(const outcome of ['success','error'])test(`save ${scenario} late ${outcome} never paints receipt/clears newer receipt/unlocks newer UI`,async()=>{
 const r=createReferenceRuntime(),task=r.action('save-plan');assert.equal(r.requests.length,1);
 if(scenario==='route-away')r.navigate('/studio');if(scenario==='new-session')r.newSession();if(scenario==='unsigned')r.unsigned();if(scenario==='clear-refresh')r.clear();r.replaceControls(true);
 const before=r.snapshot(),messages=r.toasts.length,mounts=r.mounts.length;
 if(outcome==='success')r.success(0,original().receipt,'draft');else r.fail(0);
 await task;assert.equal(r.snapshot(),before);assert.equal(r.toasts.length,messages);assert.equal(r.mounts.length,mounts);assert.equal(r.save.disabled,true);
});
test('current save retains exact bounded payload/idempotency and valid private receipt',async()=>{
 const r=createReferenceRuntime(),task=r.action('save-plan');assert.equal(r.requests.length,1);const request=r.requests[0];
 assert.match(request.payload.idempotency_key,/^[A-Za-z0-9._:-]{12,160}$/);assert.equal(request.payload.destination,'video_plan');r.success(0,original().receipt,'draft');await task;
 assert.equal(r.state.referenceFormatPlannerSaveReceipt.plan.id,original().receipt.plan.id);assert.equal(r.toasts.length,1);
});
test('uncertain current save retry uses identical original payload and idempotency key, never blindly replays',async()=>{
 const r=createReferenceRuntime(),a=r.action('save-plan');assert.equal(r.requests.length,1);r.transportFail(0);await a;assert.equal(r.requests.length,1);
 const b=r.action('save-plan');assert.equal(r.requests.length,2);assert.deepEqual(r.requests[1].payload,r.requests[0].payload);r.success(1,original().receipt,'draft');await b;assert.ok(r.state.referenceFormatPlannerSaveReceipt.plan);
});
test('edited current fields cannot save a previously generated source/result',async()=>{
 const r=createReferenceRuntime();r.edit({topic:'CUSTOMER_EDIT_BEFORE_SAVE'});const task=r.action('save-plan');await tick();
 if(r.requests.length)r.success(0,original().receipt,'draft');await task;assert.equal(r.requests.length,0,'Stale visible selection may not start a durable save');
});
test('old route action cannot submit a new compose after navigation',async()=>{
 const r=createReferenceRuntime();r.navigate('/studio');const task=r.action('compose');await tick();if(r.requests.length)r.success(0,original().result);await task;assert.equal(r.requests.length,0);
});
test('pending durable save locks native fields and does not start a second compose or save',async()=>{
 const r=createReferenceRuntime(),a=r.action('save-plan');assert.equal(r.requests.length,1);
 const fieldsLocked=r.nativeFields.every(field=>field.disabled),b=r.action('compose'),c=r.action('save-plan');await tick();
 for(let i=1;i<r.requests.length;i++)r.success(i,r.requests[i].url.endsWith('/save')?original().receipt:original().result,r.requests[i].url.endsWith('/save')?'draft':'ready');
 r.success(0,original().receipt,'draft');await Promise.all([a,b,c]);assert.equal(fieldsLocked,true);assert.equal(r.requests.length,1,'A pending write cannot fork another intent');
});
test('lost save reply keeps native fields locked and only same-request save retry is available',async()=>{
 const r=createReferenceRuntime(),a=r.action('save-plan');r.transportFail(0);await a;
 assert.equal(r.nativeFields.every(field=>field.disabled),true,'Unknown commit outcome locks exact original fields');assert.equal(r.save.disabled,false,'Explicit idempotent retry stays usable');
 const b=r.action('save-plan');assert.equal(r.requests.length,2);assert.deepEqual(r.requests[1].payload,r.requests[0].payload);r.success(1,original().receipt,'draft');await b;
});
test('a valid terminal receipt cannot start another durable save',async()=>{
 const r=createReferenceRuntime(),a=r.action('save-plan');r.success(0,original().receipt,'draft');await a;const b=r.action('save-plan');await tick();if(r.requests.length>1)r.success(1,original().receipt,'draft');await b;
 assert.equal(r.requests.length,1);
});
test('acknowledged stale HTTP error still discards only its old submission key',async()=>{
 const r=createReferenceRuntime(),a=r.action('save-plan');r.navigate('/studio');r.fail(0,503);await a;r.navigate(route);
 const b=r.action('save-plan');assert.equal(r.requests.length,2);const sameKey=r.requests[0].payload.idempotency_key===r.requests[1].payload.idempotency_key;
 r.success(1,original().receipt,'draft');await b;assert.equal(sameKey,false,'Known HTTP response preserves original discard semantics,unlike response-less transport failure');
});
