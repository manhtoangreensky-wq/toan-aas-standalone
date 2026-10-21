import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const portal = fs.readFileSync('static/portal/portal.js', 'utf8');
const i18n = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const bridge = fs.readFileSync('copyfast_voice_clone_runtime_bridge.py', 'utf8');

const voiceStart = portal.indexOf('    voice: [');
const savedStart = portal.indexOf('    voiceSaved: [', voiceStart);
const cloneStart = portal.indexOf('    voiceClone: [', savedStart);
const musicStart = portal.indexOf('    music: [', cloneStart);
assert.ok(voiceStart >= 0 && savedStart > voiceStart && cloneStart > savedStart && musicStart > cloneStart,
  'Voice field sets must remain in the canonical order');

const voiceFields = portal.slice(voiceStart, savedStart);
const savedFields = portal.slice(savedStart, cloneStart);
const cloneFields = portal.slice(cloneStart, musicStart);

test('Voice default lane keeps distinct required male/female selection', () => {
  assert.match(voiceFields, /name: "default_voice_gender"/);
  assert.match(voiceFields, /value: "female"/);
  assert.match(voiceFields, /value: "male"/);
  assert.match(voiceFields, /default_voice_gender[\s\S]*required: true/);
  for (const key of ['option.default_voice_gender.female', 'option.default_voice_gender.male']) {
    assert.ok(i18n.includes(`"${key}"`), `missing locale key ${key}`);
  }
});

test('Voice saved lane is sourced from the owner-scoped Voice Vault', () => {
  assert.match(savedFields, /name: "voice_profile_id"/);
  assert.match(savedFields, /optionsFrom: "voiceProfiles"/);
  assert.match(savedFields, /voice_profile_id[\s\S]*required: true/);
  assert.match(savedFields, /emptyLabel: "Chọn một giọng đã sẵn sàng"/);
});

test('Voice clone lane keeps upload, consent and bounded naming controls', () => {
  assert.match(cloneFields, /name: "display_name"[\s\S]*maxLength: 120/);
  assert.match(bridge, /Display Name Contract: optional, maximum 120 characters/);
  assert.match(bridge, /Optional display_name up to 120 characters/);
  assert.match(bridge, /len\(raw_display_name\) > 120/);
  assert.match(cloneFields, /name: "sample"[\s\S]*type: "file"/);
  assert.match(cloneFields, /name: "sample"[\s\S]*requiredUpload: true/);
  assert.match(cloneFields, /audio\/mpeg,audio\/wav,audio\/x-wav,audio\/mp4,audio\/ogg/);
  assert.match(cloneFields, /name: "consent"[\s\S]*type: "checkbox"[\s\S]*required: true/);
});

test('Voice workspace keeps the complete UI route handoff without claiming output delivery', () => {
  for (const route of ['/voice/tts', '/voice/saved', '/voice/clone', '/voice/preview', '/voice/outputs', '/voice-studio']) {
    assert.ok(
      portal.includes(`customerPage("${route}"`)
        || portal.includes(`featurePage("${route}"`)
        || portal.includes(`readOnlyPage("${route}"`)
        || portal.includes(`guardedFeaturePage("${route}"`),
      `missing Voice route ${route}`
    );
  }
  assert.match(portal, /Bot P0 chưa có adapter delivery Voice-output riêng cho Web/);
  assert.match(portal, /Không có preview, URL hay output thay thế nào được hiển thị/);
});

test('Voice clone route exposes the complete guarded seven-step flow', () => {
  assert.match(portal, /data-voice-clone-steps/);
  for (const key of ['consent', 'sample', 'name', 'quote', 'preview', 'save', 'back']) {
    assert.ok(i18n.includes(`[` + `"clone.step.${key}"`), `missing locale key voiceUi.clone.step.${key}`);
  }
  assert.match(portal, /voiceUiText\(`clone\.step\.\$\{step\}`/);
  assert.match(portal, /clone\.stepsGuarded/);
  const guidanceStart = portal.indexOf('const voiceCloneGuidance');
  const guidanceEnd = portal.indexOf('return `${voiceCloneGuidance', guidanceStart);
  assert.ok(guidanceStart >= 0 && guidanceEnd > guidanceStart, 'clone guidance must be rendered before its form');
  assert.doesNotMatch(portal.slice(guidanceStart, guidanceEnd), /<audio\b|provider/i);
});
