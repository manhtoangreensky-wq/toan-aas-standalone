import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const integrationPath = path.resolve(__dirname, '../static/portal/integration.js');
const source = fs.readFileSync(integrationPath, 'utf8').replace(/\r\n/g, '\n');

function extractFn(src, name) {
  const marker = '  function ' + name + '(';
  const start = src.indexOf(marker);
  if (start === -1) return '';
  const end = src.indexOf('\n  }', start);
  return end === -1 ? '' : src.slice(start, end + 4);
}

const bStart = source.indexOf('const MUSIC_PROMPT_COMPOSER_BOUNDARY_KEYS =');
const bEnd = source.indexOf('\n  ]);', bStart);
const boundaryConst = source.slice(bStart, bEnd + 5);
const rStart = source.indexOf('const MUSIC_PROMPT_COMPOSER_RESULT_KEYS =', bEnd);
const rEnd = source.indexOf(';', rStart);
const resultConst = source.slice(rStart, rEnd + 1);

const fnExactKeys = extractFn(source, 'musicPromptComposerExactKeys');
const fnOldBoundary = extractFn(source, 'musicDirectionPresetBoundaryIsSafe');
const fnNewBoundary = extractFn(source, 'musicDirectionPresetGuardBoundaryIsSafe');
const fnFeedback = extractFn(source, 'musicSfxEditorialFeedbackText');

const actionStart = source.indexOf('if (action === "music-direction-preset-compose") {');
const actionEnd = source.indexOf('if (action === "sfx', actionStart);
const actionBody = source.slice(actionStart, actionEnd);

const FLAGS = [
  'input_persisted', 'source_audio_inspected', 'provider_called', 'ai_music_called',
  'lyrics_generated', 'audio_created', 'preview_created', 'output_created',
  'job_created', 'wallet_mutated', 'payment_started', 'asset_saved',
  'collection_saved', 'publish_action_created', 'telegram_called', 'rights_verified'
];

function makeValidBoundary() {
  const b = { execution: 'web_native_deterministic_music_direction_only' };
  for (const f of FLAGS) b[f] = false;
  return b;
}

function createSandbox(apiHandler) {
  const state = { merged: [], toasts: [], statuses: [], busy: [] };
  const sandbox = {
    window: { TOANAASI18n: { t: (k) => k } },
    currentPortalPath: () => '/media-workspace/music-directions',
    base: () => ({ capabilities: { 'music-direction-preset-compose': true }, pageStates: {} }),
    musicDirectionPresetPayload: (f) => ({ ...f }),
    musicDirectionPresetResultMatchesSource: () => { throw new Error('Result matcher should not be called'); },
    setActionBusy: (act, rt, busy) => state.busy.push({ act, rt, busy }),
    setMusicDirectionPresetSubmissionStatus: (s) => state.statuses.push(s),
    merge: (m) => state.merged.push(JSON.parse(JSON.stringify(m))),
    toast: (msg) => state.toasts.push(msg),
    musicDirectionPresetComposeRequestEpoch: 0,
    musicDirectionPresetComposePendingRequestEpoch: 0,
    api: apiHandler
  };
  const code = [
    boundaryConst,
    resultConst,
    fnExactKeys,
    fnOldBoundary,
    fnFeedback,
    fnNewBoundary ? fnNewBoundary : 'var musicDirectionPresetGuardBoundaryIsSafe = musicDirectionPresetBoundaryIsSafe;',
    'async function runAction(action, route, fields) {',
    actionBody,
    '}'
  ].join('\n\n');
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return { sandbox, state };
}

const validFields = {
  description: 'Original product introduction',
  language: 'en',
  web_preset_id: 'commercial_bright'
};
const route = '/media-workspace/music-directions';
const action = 'music-direction-preset-compose';

test('C01: guarded response (resolved) merges draft and toasts VI without rejecting', async () => {
  const envelope = {
    status: 'guarded',
    error_code: 'WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD',
    data: makeValidBoundary()
  };
  const { sandbox, state } = createSandbox(async (p, opts) => {
    assert.equal(p, '/media-workspace/tools/music-directions/compose');
    assert.equal(opts.method, 'POST');
    return envelope;
  });
  await assert.doesNotReject(async () => {
    await sandbox.runAction(action, route, validFields);
  });
  assert.equal(state.merged.length, 1);
  assert.deepEqual(state.merged[0].musicDirectionPresetDraft, validFields);
  assert.deepEqual(state.merged[0].musicDirectionPresetResult, {});
  assert.equal(state.merged[0].pageStates[route], 'guarded');
  assert.equal(state.toasts[0], 'Hãy mô tả phong cách riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền.');
  assert.equal(state.statuses.length, 1);
});

test('C01: guarded response (thrown error.payload) catches, merges and toasts VI', async () => {
  const err = new Error('Policy guard rejected');
  err.payload = {
    status: 'guarded',
    error_code: 'WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD',
    data: makeValidBoundary()
  };
  const { sandbox, state } = createSandbox(async () => { throw err; });
  await assert.doesNotReject(async () => {
    await sandbox.runAction(action, route, validFields);
  });
  assert.equal(state.merged.length, 1);
  assert.deepEqual(state.merged[0].musicDirectionPresetDraft, validFields);
  assert.deepEqual(state.merged[0].musicDirectionPresetResult, {});
  assert.equal(state.merged[0].pageStates[route], 'guarded');
  assert.equal(state.toasts[0], 'Hãy mô tả phong cách riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền.');
});

test('C02: guard boundary validator strict contract on keys and boolean false flags', () => {
  const { sandbox } = createSandbox(async () => ({}));
  const guardIsSafe = sandbox.musicDirectionPresetGuardBoundaryIsSafe;
  const oldIsSafe = sandbox.musicDirectionPresetBoundaryIsSafe;

  assert.equal(guardIsSafe(makeValidBoundary()), true);
  assert.equal(oldIsSafe(makeValidBoundary()), false);
  assert.equal(oldIsSafe({ composer: {}, ...makeValidBoundary() }), true);

  const badValues = [true, 'false', 0, null, {}, [], undefined];
  for (const flag of FLAGS) {
    for (const bad of badValues) {
      const mutated = makeValidBoundary();
      mutated[flag] = bad;
      assert.equal(guardIsSafe(mutated), false, `flag ${flag} with ${bad} should be false`);
    }
    const deleted = makeValidBoundary();
    delete deleted[flag];
    assert.equal(guardIsSafe(deleted), false, `deleted flag ${flag} should be false`);
  }

  assert.equal(guardIsSafe(null), false);
  assert.equal(guardIsSafe([]), false);
  assert.equal(guardIsSafe('string'), false);
  assert.equal(guardIsSafe(undefined), false);
  assert.equal(guardIsSafe({ ...makeValidBoundary(), execution: 'web_native_deterministic_music_prompt_only' }), false);
  assert.equal(guardIsSafe({ ...makeValidBoundary(), composer: {} }), false);
  assert.equal(guardIsSafe({ ...makeValidBoundary(), unknown_key: false }), false);
});
