import assert from 'node:assert/strict';
import test from 'node:test';
import {actions,campaignActionRuntime,campaignItem,detailRoute} from './helpers/campaign-action-runtime.mjs';

function envelope(action) {
  const status=action==='campaign-update-status'?'review':'draft';
  return {ok:true,status,message:'NATIVE_ACK',error_code:null,data:{item:campaignItem(action==='campaign-create'?1:2,status)}};
}

const invalids={
  missingData: response=>{delete response.data;},
  missingItem: response=>{delete response.data.item;},
  nullItem: response=>{response.data.item=null;},
  arrayItem: response=>{response.data.item=[];},
  stringItem: response=>{response.data.item='not a record';},
  missingId: response=>{delete response.data.item.id;},
  invalidId: response=>{response.data.item.id='invalid-plan';},
  stringRevision: response=>{response.data.item.revision='2';},
  zeroRevision: response=>{response.data.item.revision=0;},
  fractionalRevision: response=>{response.data.item.revision=1.5;},
  missingRevision: response=>{delete response.data.item.revision;},
  invalidPlatform: response=>{response.data.item.platform='unknown';},
  invalidObjective: response=>{response.data.item.objective='unknown';},
  invalidPlanState: response=>{response.data.item.approval_status='published';response.status='published';},
  mismatchedEnvelopeState: response=>{response.status='archived';},
};
for(const field of ['title','destination_url','scheduled_for','review_note','created_at','updated_at']) {
  invalids['missing_'+field]=response=>{delete response.data.item[field];};
  invalids['wrongType_'+field]=response=>{response.data.item[field]=42;};
}

for(const action of actions) {
  test(`${action}: original native receipt shape is accepted without a Bot bridge`,async()=>{
    const h=campaignActionRuntime(action),task=h.run(),response=envelope(action);
    assert.equal(h.pending.length,1);assert.equal(h.button.disabled,true);
    h.settle(0,'valid',response);await task;
    assert.equal(h.state.campaignPlans[0].revision,action==='campaign-create'?1:2);
    assert.equal(h.state.campaignPlans[0].approval_status,action==='campaign-update-status'?'review':'draft');
    assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].getAttribute('role'),'status');assert.equal(h.button.disabled,false);
    if(action==='campaign-create')assert.deepEqual(h.assignments,[detailRoute]);
  });
  for(const [kind,change] of Object.entries(invalids))test(`${action}: ${kind} cannot announce success or apply a receipt`,async()=>{
    const h=campaignActionRuntime(action),snapshot=JSON.stringify(h.state),task=h.run(),response=envelope(action);
    change(response);h.settle(0,'valid',response);await task;
    assert.equal(JSON.stringify(h.state),snapshot,'invalid ACK must not replace signed projection');
    assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].getAttribute('role'),'alert');
    assert.equal(h.button.disabled,false);assert.equal(h.assignments.length,0);assert.equal(h.clears.length,0);
    assert.equal(h.networkLog.filter(row=>row.method==='GET').length,0,'invalid ACK must not start detail hydration');
  });
  test(`${action}: harmless extra server fields remain intact`,async()=>{
    const h=campaignActionRuntime(action),task=h.run(),response=envelope(action);
    response.data.item.server_note='OWNER_SERVER_NOTE';h.settle(0,'valid',response);await task;
    assert.equal(h.state.campaignPlans[0].server_note,'OWNER_SERVER_NOTE');assert.equal(h.toasts[0].getAttribute('role'),'status');
  });
  test(`${action}: native optional empty strings and large positive revision are not rejected by schedule-only bounds`,async()=>{
    const h=campaignActionRuntime(action),task=h.run(),response=envelope(action);
    response.data.item.scheduled_for='';response.data.item.review_note='';response.data.item.revision=1000001;
    response.data.item.platform='facebook';response.data.item.objective='conversion';
    h.settle(0,'valid',response);await task;
    assert.equal(h.state.campaignPlans[0].revision,1000001);assert.equal(h.state.campaignPlans[0].platform,'facebook');
    assert.equal(h.toasts[0].getAttribute('role'),'status');
  });
  test(`${action}: an invalid receipt stays silent after the UI account changes`,async()=>{
    const h=campaignActionRuntime(action),task=h.run();
    const next=JSON.parse(JSON.stringify(h.state));next.account.id='22222222-2222-4222-8222-222222222222';
    h.replace(next,{epoch:false});const snapshot=JSON.stringify(h.state),response=envelope(action);delete response.data.item;
    h.settle(0,'valid',response);await task;
    assert.equal(JSON.stringify(h.state),snapshot);assert.equal(h.toasts.length,0);assert.equal(h.button.disabled,true);
  });
}

for(const action of ['campaign-update','campaign-update-status']) {
  test(`${action}: a different valid UUID cannot be merged as the requested plan`,async()=>{
    const h=campaignActionRuntime(action),snapshot=JSON.stringify(h.state),task=h.run(),response=envelope(action);
    response.data.item.id='44444444-4444-4444-8444-444444444444';h.settle(0,'valid',response);await task;
    assert.equal(JSON.stringify(h.state),snapshot);assert.equal(h.toasts[0].getAttribute('role'),'alert');
    assert.equal(h.networkLog.filter(row=>row.method==='GET').length,0);
  });
  test(`${action}: native lowercase receipt for an uppercase requested UUID remains valid`,async()=>{
    const id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    const h=campaignActionRuntime(action,{uiPath:'/campaigns',eventRoute:'/campaigns'}),task=h.run({...h.fields,plan_id:id.toUpperCase()}),response=envelope(action);
    response.data.item.id=id;h.settle(0,'valid',response);await task;
    assert.ok(h.state.campaignPlans.some(item=>item.id===id));assert.equal(h.toasts[0].getAttribute('role'),'status');
  });
}

test('create accepts a new arbitrary server UUID rather than inventing an expected ID',async()=>{
  const h=campaignActionRuntime('campaign-create'),task=h.run(),response=envelope('campaign-create');
  response.data.item.id='44444444-4444-4444-8444-444444444444';h.settle(0,'valid',response);await task;
  assert.deepEqual(h.assignments,['/campaigns/44444444-4444-4444-8444-444444444444']);
  assert.equal(h.toasts[0].getAttribute('role'),'status');
});
for(const action of ['campaign-create','campaign-update-status'])test(`${action}: a different acknowledged state is not the requested transition`,async()=>{
  const h=campaignActionRuntime(action),snapshot=JSON.stringify(h.state),task=h.run(),response=envelope(action);
  response.status=response.data.item.approval_status='archived';h.settle(0,'valid',response);await task;
  assert.equal(JSON.stringify(h.state),snapshot);assert.equal(h.toasts[0].getAttribute('role'),'alert');
});
