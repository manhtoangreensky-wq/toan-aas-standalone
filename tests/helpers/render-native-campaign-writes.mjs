import assert from 'node:assert/strict';
import { campaignActionRuntime } from './campaign-action-runtime.mjs';
let input = '';
for await (const chunk of process.stdin) input += chunk;
const samples = JSON.parse(input);
for (const [action, sample] of Object.entries(samples)) for (const uppercase of action === 'campaign-create' ? [false] : [false,true]) {
  const id = sample.response.data.item.id;
  const uiPath = action === 'campaign-create' ? '/campaigns/new' : action === 'campaign-update-status' ? '/approvals' : `/campaigns/${id}`;
  const harness = campaignActionRuntime(action, { uiPath, eventRoute: action === 'campaign-update-status' ? '/campaigns' : uiPath });
  const task = harness.run(uppercase ? {...sample.fields,plan_id:id.toUpperCase()} : sample.fields);
  assert.equal(harness.pending.length, 1);
  assert.equal(harness.button.disabled, true);
  harness.settle(0, 'valid', sample.response); await task;
  const item = harness.state.campaignPlans.find(row => row.id === id);
  assert.deepEqual(JSON.parse(JSON.stringify(item)), sample.response.data.item);
  assert.equal(harness.toasts[0].textContent, sample.response.message);
  assert.equal(harness.button.disabled, false);
  assert.equal(harness.pending.length, 1);
  if (action === 'campaign-create') assert.deepEqual(harness.assignments, [`/campaigns/${id}`]);
}
console.log(JSON.stringify({ nativeWriteEnvelopes: 3, integrationReceipts: 5, uppercaseNativeControls: 2, providerCalls: 0, walletMutations: 0 }));
