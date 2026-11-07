import assert from 'node:assert/strict';
import test from 'node:test';
import { actions, campaignActionRuntime, campaignContext, detailRoute, planId } from './helpers/campaign-action-runtime.mjs';

for (const action of actions) {
  test(`${action}: positive control reaches the real Web API boundary and accepts the owner item`, async () => {
    const harness = campaignActionRuntime(action);
    const task = harness.run();
    assert.equal(harness.pending.length, 1);
    assert.equal(harness.button.disabled, true);
    const request = harness.pending[0];
    assert.equal(request.method, action === 'campaign-update' ? 'PATCH' : 'POST');
    assert.equal(request.path, action === 'campaign-create' ? '/api/v1/campaigns' : `/api/v1/campaigns/${planId}${action === 'campaign-update-status' ? '/status' : ''}`);
    assert.equal(typeof request.body.idempotency_key, 'string');
    assert.ok(request.body.idempotency_key.length > 0);
    if (action === 'campaign-update-status') assert.equal(request.body.approval_status, 'review');
    harness.settle(0);
    await task;
    assert.equal(harness.state.campaignPlans[0].id, planId);
    assert.equal(harness.state.campaignPlans[0].revision, action === 'campaign-create' ? 1 : 2);
    assert.equal(harness.state.campaignPlans[0].approval_status, action === 'campaign-update-status' ? 'review' : 'draft');
    if (action === 'campaign-create') {
      assert.deepEqual(harness.assignments, [detailRoute]);
      assert.deepEqual(harness.clears, ['/campaigns/new']);
    } else {
      assert.deepEqual(harness.networkLog.filter(row => row.method === 'GET').map(row => row.path), [`/api/v1/campaigns/${planId}`, `/api/v1/campaigns/${planId}/schedule-intents`]);
      assert.equal(harness.state.campaignPlanDetail.revision, 2);
    }
    assert.equal(harness.button.disabled, false);
    assert.equal(harness.toasts.length, 1);
  });
}

async function waitForReads(harness) {
  for (let index = 0; index < 30 && harness.reads.length < 2; index++) await Promise.resolve();
  assert.equal(harness.reads.length, 2, 'the existing detail and schedule reads must actually be pending');
}

for (const action of actions) for (const kind of ['guarded', 'transport_error']) {
  test(`${action}: old ${kind} failure stays silent after account replacement`, async () => {
    const harness = campaignActionRuntime(action), task = harness.run();
    harness.replace(campaignContext(action === 'campaign-create' ? '/campaigns/new' : detailRoute, 'B'));
    const snapshot = JSON.stringify(harness.state);
    harness.settle(0, kind); await task;
    assert.equal(JSON.stringify(harness.state), snapshot);
    assert.equal(harness.toasts.length, 0);
    assert.equal(harness.button.disabled, true);
  });
  test(`${action}: current ${kind} failure is still visible and releases its controls`, async () => {
    const harness = campaignActionRuntime(action), task = harness.run();
    harness.settle(0, kind); await task;
    assert.equal(harness.toasts.length, 1);
    assert.equal(harness.toasts[0].getAttribute('role'), 'alert');
    assert.equal(harness.button.disabled, false);
    assert.equal(harness.clears.length, 0); assert.equal(harness.assignments.length, 0);
  });
}

for (const action of actions) for (const change of ['account', 'logout', 'capability', 'csrf']) {
  test(`${action}: ${change} invalidates the pending UI receipt without relying on a simulated epoch`, async () => {
    const harness = campaignActionRuntime(action), task = harness.run();
    const next = campaignContext(action === 'campaign-create' ? '/campaigns/new' : detailRoute, change === 'account' ? 'B' : 'A');
    if (change === 'logout') next.session.authenticated = false;
    if (change === 'capability') next.capabilities[action] = false;
    if (change === 'csrf') next.session.csrfToken = 'changed-synthetic-token';
    harness.replace(next, { epoch: false }); const snapshot = JSON.stringify(harness.state);
    harness.settle(0); await task;
    assert.equal(JSON.stringify(harness.state), snapshot);
    assert.equal(harness.toasts.length, 0); assert.equal(harness.button.disabled, true);
    assert.equal(harness.clears.length, 0); assert.equal(harness.assignments.length, 0);
  });
}

for (const action of actions.filter(value => value !== 'campaign-create')) {
  test(`${action}: a current detail reload preserves its signed item`, async () => {
    const harness = campaignActionRuntime(action, { deferReads: true }), task = harness.run();
    harness.settle(0); await waitForReads(harness); harness.settleReads(); await task;
    assert.equal(harness.state.campaignPlanDetail.revision, 2);
    assert.equal(harness.state.campaignPlanDetail.scheduleIntentsReadState, 'read_only');
    assert.equal(harness.toasts.length, 1); assert.equal(harness.button.disabled, false);
  });
  for (const kind of ['valid', 'error']) test(`${action}: departing during ${kind} detail reload cannot toast or enable the next screen`, async () => {
    const harness = campaignActionRuntime(action, { deferReads: true }), task = harness.run();
    harness.settle(0); await waitForReads(harness);
    harness.replace(campaignContext('/campaigns')); const snapshot = JSON.stringify(harness.state);
    harness.settleReads(kind); await task;
    assert.equal(JSON.stringify(harness.state), snapshot);
    assert.equal(harness.toasts.length, 0); assert.equal(harness.button.disabled, true);
  });
}

for (const action of actions) test(`${action}: rejecting a duplicate must not invalidate the accepted pending request`, async () => {
  const harness = campaignActionRuntime(action), task = harness.run();
  await harness.run(); assert.equal(harness.pending.length, 1);
  harness.toasts.splice(0); harness.settle(0); await task;
  assert.equal(harness.toasts.length, 1); assert.equal(harness.button.disabled, false);
  assert.equal(harness.state.campaignPlans[0].revision, action === 'campaign-create' ? 1 : 2);
});

for (const order of [[0, 1], [1, 0]]) test(`independent record writes both keep receipts in order ${order}`, async () => {
  const harness = campaignActionRuntime('campaign-update-status', { uiPath: '/campaigns', eventRoute: '/campaigns' });
  const otherId = '44444444-4444-4444-8444-444444444444';
  const tasks = [harness.run(), harness.run({ ...harness.fields, plan_id: otherId })];
  assert.equal(harness.pending.length, 2);
  harness.settle(order[0]); await tasks[order[0]];
  const firstControlDisabled = harness.button.disabled;
  for (const toast of [...harness.toasts]) toast.remove();
  harness.settle(order[1]); await tasks[order[1]];
  assert.deepEqual(Array.from(harness.state.campaignPlans, item => item.id).sort(), [planId, otherId].sort());
  assert.ok(harness.state.campaignPlans.every(item => item.revision === 2));
  assert.equal(harness.toastEvents.length, 2, 'neither independent record is an obsolete write; duplicate text may share one visible toast');
  assert.equal(firstControlDisabled, true, 'the shared action/route control group is still processing another record');
  assert.equal(harness.button.disabled, false);
});

test('independent edit and status scopes on the board are both acknowledged', async () => {
  const harness = campaignActionRuntime('campaign-update', { uiPath: '/campaigns', eventRoute: '/campaigns' });
  const first = harness.run(), second = harness.run({ plan_id: planId, approval_status: 'review', review_note: 'STATUS_NOTE' }, 'campaign-update-status');
  harness.settle(0); await first; harness.settle(1); await second;
  assert.equal(harness.toastEvents.length, 2); assert.equal(harness.pending.length, 2);
});

for (const order of [[0, 1], [1, 0]]) test(`newer same-scope write owns feedback and control, completion order ${order}`, async () => {
  const harness = campaignActionRuntime('campaign-update-status', { uiPath: '/campaigns', eventRoute: '/campaigns' });
  const tasks = [harness.run(), harness.run({ ...harness.fields, approval_status: 'approved' })];
  for (const index of order) {
    harness.settle(index); await tasks[index];
    if (index === 0 && order[0] === 0) assert.equal(harness.button.disabled, true, 'an older completion must not release the newer pending action');
  }
  assert.equal(harness.state.campaignPlans[0].approval_status, 'approved');
  assert.equal(harness.toastEvents.length, 1); assert.equal(harness.button.disabled, false);
});

test('Approvals captures the actual UI path separately from its valid /campaigns form route', async () => {
  const harness = campaignActionRuntime('campaign-update-status', { uiPath: '/approvals', eventRoute: '/campaigns' }), task = harness.run();
  assert.equal(harness.button.disabled, true, 'the real Approvals form route must own its busy control');
  harness.settle(0); await task;
  assert.equal(harness.state.path, '/approvals'); assert.equal(harness.state.campaignPlans[0].approval_status, 'review');
  assert.equal(harness.toasts.length, 1); assert.equal(harness.button.disabled, false);
});

for (const action of actions) {
  for (const change of ['route', 'session']) {
    test(`${action}: acknowledged old write cannot affect a newer ${change} context`, async () => {
      const harness = campaignActionRuntime(action);
      const task = harness.run();
      assert.equal(harness.pending.length, 1);
      const nextPath = change === 'route' ? '/campaigns' : (action === 'campaign-create' ? '/campaigns/new' : detailRoute);
      const next = campaignContext(nextPath, change === 'session' ? 'B' : 'A');
      harness.replace(next, { epoch: change === 'session', disabled: true });
      const snapshot = JSON.stringify(harness.state);
      harness.settle(0);
      await task;
      assert.equal(JSON.stringify(harness.state), snapshot, 'old write must not merge into the newer context');
      assert.equal(harness.toasts.length, 0, 'old write must not announce success in the newer context');
      assert.equal(harness.button.disabled, true, 'old write must not release the newer context control');
      assert.equal(harness.assignments.length, 0, 'old write must not redirect a newer page');
      assert.equal(harness.clears.length, 0, 'old write must not clear the current draft');
    });
  }
}
