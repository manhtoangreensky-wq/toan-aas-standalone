import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const portal = fs.readFileSync('static/portal/portal.js', 'utf8');
const i18n = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const theme = fs.readFileSync('static/portal/portal-theme.css', 'utf8');

test('Voice workspace exposes a guarded STT lane with source and result controls', () => {
  const voiceStart = portal.indexOf('    voice: [');
  const musicStart = portal.indexOf('    music: [', voiceStart);
  assert.ok(voiceStart >= 0 && musicStart > voiceStart);
  const voiceFields = portal.slice(voiceStart, musicStart);
  assert.match(voiceFields, /voiceStt:\s*\[/);
  assert.match(voiceFields, /voiceStt:[\s\S]*name: "source"[\s\S]*requiredUpload: true/);
  assert.match(voiceFields, /voiceStt:[\s\S]*name: "source_language"[\s\S]*options: LANGUAGE_OPTIONS/);
  assert.match(voiceFields, /voiceStt:[\s\S]*name: "output_format"[\s\S]*value: "srt"/);
  assert.match(portal, /featurePage\("\/voice\/stt"[\s\S]*FIELD_SETS\.voiceStt/);
  assert.match(portal, /"\/voice\/stt": "voice_stt"/);
});

test('Voice workspace navigation keeps the four modes in one accessible vertical flow', () => {
  assert.match(portal, /function renderVoiceWorkspaceNav\(route\)/);
  assert.match(portal, /data-voice-workspace/);
  for (const path of ['/voice/tts', '/voice/stt', '/voice/saved', '/voice/clone']) {
    assert.match(portal, new RegExp(`\\["[^"\\n]+", "${path.replace('/', '\\/')}"\\]`));
  }
  assert.match(portal, /aria-current="page"/);
  assert.match(portal, /voiceWorkspaceNav/);
});

test('Voice STT and workspace copy is balanced in VI, EN and ZH', () => {
  for (const key of [
    'workspace.kicker', 'workspace.title', 'workspace.description', 'workspace.navLabel',
    'workspace.tab.tts', 'workspace.tab.stt', 'workspace.tab.saved', 'workspace.tab.clone',
    'tool.stt.title', 'tool.stt.description', 'field.source.label',
    'field.source_language.label', 'field.source_language.empty', 'field.output_format.label',
    'option.output_format.txt', 'option.output_format.srt', 'option.output_format.vtt'
  ]) {
    assert.match(i18n, new RegExp(`\\["${key.replace('.', '\\.')}",`), `missing voiceUi.${key}`);
  }
  for (const value of ['vi', 'en', 'zh', 'auto', 'ja', 'ko', 'fr', 'de', 'es']) {
    assert.match(i18n, new RegExp(`\\["option\\.source_language\\.${value.replace('.', '\\.')}",`));
  }
});

test('Voice workspace tabs retain the blue/teal palette and responsive touch targets', () => {
  assert.match(theme, /\.portal-voice-workspace-tab[^\n]*min-height: 56px/);
  assert.match(theme, /\.portal-voice-workspace-tab\.is-active[^\n]*var\(--portal-brand\)/);
  assert.match(theme, /@media \(max-width: 760px\)[\s\S]*\.portal-voice-workspace-nav/);
  assert.match(theme, /@media \(max-width: 430px\)[\s\S]*\.portal-voice-workspace-nav/);
});
