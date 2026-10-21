import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
const source=fs.readFileSync('static/portal/portal.js','utf8');
const block=source.slice(source.indexOf('  const SUBDUB_PRODUCT_MODES'),source.indexOf('\n  function renderDocumentHub',source.indexOf('  const SUBDUB_PRODUCT_MODES')));
function harness(){
  const drafts=new Map();
  const api=new Function('transientFormDrafts','clearTransientFormDraft',block+'\nreturn {captureSubDubDraft,subDubDraftSnapshot,subDubDraftValue,synchronizeSubDubWorkspaceDraftSession,normalizeSubDubDraftValue};')(drafts,route=>drafts.delete(route));
  const session=token=>api.synchronizeSubDubWorkspaceDraftSession({session:{authenticated:!!token,csrfToken:token}});
  session('qa-account-A');return{api,drafts,session};
}
function control({name='',value='',type='select-one',attrs={},disabled=false,checked=true}={}){
  return{name,value,type,disabled,checked,getAttribute:key=>attrs[key]??null,hasAttribute:key=>Object.hasOwn(attrs,key)};
}
function rootFor(controls,mode='SUBTITLE_PLUS_DUBBING'){
  return{querySelector:()=>null,querySelectorAll:()=>[{hidden:false,getAttribute:()=>mode,querySelectorAll:()=>controls}]};
}
test('actual capture retains nameless ranges, suffixed position and selected display',()=>{
 const h=harness();
 h.api.captureSubDubDraft(rootFor([
  control({attrs:{'data-subdub-local-volume':'original'},value:'0',type:'range'}),
  control({attrs:{'data-subdub-local-volume':'dubbing'},value:'200',type:'range'}),
  control({name:'subdub_combo_subtitle_position',value:'top_center'}),
  control({name:'sub_display_type',value:'single'}),
  control({name:'subdub_voice_lane_combo',value:'default_male',type:'radio',attrs:{'data-subdub-voice-lane-input':''}})
 ]));
 assert.deepEqual(h.api.subDubDraftSnapshot().shared,{original_volume:'0',dubbing_volume:'200',voice_lane:'default_male',sub_display_type:'single',subtitle_position:'top_center'});
});
test('latest compatible value follows the user instead of an older per-mode snapshot',()=>{
 const h=harness();
 h.api.captureSubDubDraft(rootFor([control({name:'target_language',value:'en'})],'DUBBING_ONLY'));
 h.api.captureSubDubDraft(rootFor([control({name:'target_language',value:'zh'})]));
 assert.equal(h.api.subDubDraftValue(h.api.subDubDraftSnapshot(),'DUBBING_ONLY','target_language','vi'),'zh');
});
test('mode-specific output formats remain independent and invalid/private values are not captured',()=>{
 const h=harness();
 h.api.captureSubDubDraft(rootFor([control({name:'subdub-source-output-format',value:'txt',type:'radio'})],'SUBTITLE_ONLY'));
 h.api.captureSubDubDraft(rootFor([
  control({name:'subdub-combined-output-format',value:'vtt',type:'radio'}),
  control({attrs:{'data-subdub-local-volume':'original'},value:'101',type:'range'}),
  control({name:'file',type:'file',value:'private-path'}),
  control({name:'voice_profile_id',value:'foreign-id'}),
  control({name:'target_language',value:'not-a-language'}),
  control({name:'source_language',value:'en',disabled:true})
 ]));
 const draft=h.api.subDubDraftSnapshot();
 assert.equal(draft.modes.SUBTITLE_ONLY['subdub-source-output-format'],'txt');
 assert.equal(draft.modes.SUBTITLE_PLUS_DUBBING['subdub-combined-output-format'],'vtt');
 assert.deepEqual(draft.shared,{});assert.doesNotMatch(JSON.stringify(draft),/private-path|foreign-id|not-a-language/);
});
test('same signed session retains the draft; account replacement and logout clear it',()=>{
 const h=harness();
 const capture=()=>h.api.captureSubDubDraft(rootFor([control({name:'target_language',value:'en'})]));
 capture();h.session('qa-account-A');assert.equal(h.api.subDubDraftSnapshot().shared.target_language,'en');
 h.session('qa-account-B');assert.equal(h.drafts.has('/subdub'),false);
 capture();h.session('');assert.equal(h.drafts.has('/subdub'),false);
 h.api.captureSubDubDraft(rootFor([control({name:'target_language',value:'zh'})]));assert.equal(h.drafts.has('/subdub'),false);
});
