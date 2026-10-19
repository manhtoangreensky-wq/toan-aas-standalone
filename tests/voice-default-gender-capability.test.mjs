import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const voiceStart = source.indexOf('    voice: [');
const voiceEnd = source.indexOf('    voiceSaved: [', voiceStart);
assert.ok(voiceStart >= 0 && voiceEnd > voiceStart, 'Voice field set must remain discoverable');
const voiceFields = source.slice(voiceStart, voiceEnd);

const helperStart = source.indexOf('  const VOICE_DEFAULT_GENDER_VALUES =');
const helperEnd = source.indexOf('  function renderVoiceFormFeedback', helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, 'Voice gender capability helper must remain discoverable');
const context = {};
vm.createContext(context);
vm.runInContext(source.slice(helperStart, helperEnd), context);

test('Voice default lane keeps the canonical female/male pair when capability is not explicit', () => {
  assert.deepEqual([...context.voiceDefaultGenderValues({})], ['female', 'male']);
  assert.doesNotMatch(voiceFields, /Nữ \(female\)|Nam \(male\)/);
});

test('Voice default lane follows an explicit single-gender capability without silent substitution', () => {
  assert.deepEqual(
    [...context.voiceDefaultGenderValues({ readiness: { features: { voice_tts: { default_voice_genders: ['male', 'unknown'] } } } })],
    ['male'],
  );
  assert.deepEqual(
    [...context.voiceDefaultGenderValues({ readiness: { features: { voice_tts: { default_voice_gender: 'female' } } } })],
    ['female'],
  );
  assert.deepEqual(
    [...context.voiceDefaultGenderValues({ readiness: { features: { voice_tts: { default_voice_genders: [] } } } })],
    [],
  );
});

test('Voice form selects the sole capability default only when one is explicitly available', () => {
  assert.match(
    source,
    /defaultValue: field\.name === "default_voice_gender" && defaultVoiceGenders\.length === 1\s*\? defaultVoiceGenders\[0\]/,
  );
  assert.match(source, /field\.name === "default_voice_gender"\s*\n\s*\? defaultVoiceGenders\.map/);
});
