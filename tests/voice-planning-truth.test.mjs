import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const begin=source.indexOf('  function renderVoiceStudio(page, context) {');
const end=source.indexOf('  function renderVoiceCueSheet(',begin);
assert.ok(begin>=0&&end>begin);
const context={
  safeText:value=>String(value??''),
  renderHero:()=>'', renderEmpty:()=>'', badge:()=>'', renderFields:()=>'', renderNotes:()=>'',
  voiceStudioListing:()=>({filters:{}}), voiceStudioVaultValues:value=>value,
  voiceStudioVaultFields:()=>[],
  renderVoiceStudioPolicy:()=>'',
  transientFormValues:()=>({}), ICONS:{voice:'voice'}
};
vm.runInNewContext(fs.readFileSync('static/portal/portal-i18n.js','utf8'),context);
context.uiText=(key,fallback,params)=>context.TOANAASI18n.has(key)?context.TOANAASI18n.t(key,params,'vi'):fallback;
const helper=source.indexOf('  function voiceStudioText(');
const helperEnd=source.indexOf('\n  }',helper)+4;
vm.runInNewContext(source.slice(helper,helperEnd)+'\n'+source.slice(begin,end),context);

for(const path of ['/voice-studio','/voice-studio/new']){
  test(`${path} must not receive simulated TTS, sample MP3 or paid creation UI`,()=>{
    const html=context.renderVoiceStudio({path},{capabilities:{'voice-studio-view':true},voiceStudioReadState:'guarded'});
    assert.doesNotMatch(html,/Neural Voice Engine|voice_speech_sample|\(-5 Xu\)|onclick="alert\(/i,'Voice planning must use its real metadata/text form without the fake TTS panel');
  });
}
