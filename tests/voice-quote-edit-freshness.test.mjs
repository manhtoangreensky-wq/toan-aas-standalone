import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function fn(name){const a=source.indexOf(`  function ${name}(`);assert.ok(a>=0,`${name} must exist`);return source.slice(a,source.indexOf('\n  }',a)+4);}
const route='/voice/tts';
const input={script:'Quoted script',default_voice_gender:'female',speed:'1.0',volume_percent:'0'};
const fields=[{name:'script',control:'textarea'},{name:'default_voice_gender',control:'select',options:[{value:'female',label:'Nữ'},{value:'male',label:'Nam'}]},{name:'speed',type:'number',defaultValue:'1.0'},{name:'volume_percent',type:'number',defaultValue:'100'}];
const page={path:route,type:'feature',action:'feature-estimate',fields};
const quote=()=>({phase:'estimate',status:'awaiting_confirm',input:{...input},estimateFingerprint:'quoted-input',webQuoteReceipt:'Q'.repeat(48),data:{estimate:{available:true,estimated_xu:3}}});
function runtime(locale='vi'){
  const ctx={canAct:()=>true,actionBlockReason:()=>'',featureKeyForPage:()=> 'voice_tts',workspaceDraftIdForRoute:()=>'',featureConfirmExecutionReady:()=>true,voiceQuoteAmount:()=>3,classifyPageBoundary:()=> 'runtime_generator',ALLOWED_STATES:new Set(['awaiting_confirm']),draft:{},resolvePage:()=>page,window:{__TOAN_AAS_PORTAL__:{featureFlows:{[route]:quote()}}}};
  ctx.transientFormValues=()=>ctx.draft;
  vm.createContext(ctx);vm.runInContext(catalog,ctx);
  const i18n=ctx.window.TOANAASI18n || ctx.TOANAASI18n;
  ctx.uiText=(key,fallback,params)=>i18n.has(key)?i18n.t(key,params,locale):fallback;
  ctx.voiceUiText=(key,fallback,params)=>ctx.uiText(`voiceUi.${key}`,fallback,params);
  const a=source.indexOf('  function renderFields('),b=source.indexOf('  function statusMessage(',a);
  const c=source.indexOf('  function voiceFeedbackMetrics('),d=source.indexOf('  const ADMIN_TAB_GROUPS',c);
  vm.runInContext(fn('safeText')+'\n'+source.slice(a,b)+'\n'+fn('flowQuoteExpiry')+'\n'+fn('flowHasFreshEstimate')+'\n'+fn('voiceQuoteExpiryState')+'\n'+source.slice(c,d)+'\n'+fn('collectFormFields')+'\n'+fn('synchronizeVoiceQuoteFreshness'),ctx);
  return ctx;
}

test('Voice quote comparison handles edits, zero, defaults and unrelated keys without mutating input',()=>{
  const ctx=runtime(),flow=quote();
  assert.equal(ctx.voiceQuoteHasEdits(page,flow,{}),false);
  assert.equal(ctx.voiceQuoteHasEdits(page,flow,{...input,volume_percent:0,unrelated:'value'}),false);
  for(const [name,value] of Object.entries({script:'New script',default_voice_gender:'male',speed:'1.2',volume_percent:'100'})){
    assert.equal(ctx.voiceQuoteHasEdits(page,flow,{...input,[name]:value}),true,name);
  }
  assert.deepEqual(flow.input,input);
});

test('A new file or changed consent invalidates the UI quote without inventing upload state',()=>{
  const ctx=runtime();
  const clone={fields:[{name:'sample',type:'file'},{name:'consent',type:'checkbox'}]};
  const flow={...quote(),input:{consent:true}};
  assert.equal(ctx.voiceQuoteHasEdits(clone,flow,{consent:true}),false);
  assert.equal(ctx.voiceQuoteHasEdits(clone,flow,{consent:false}),true);
  assert.equal(ctx.voiceQuoteHasEdits(clone,flow,{consent:true,sample:{name:'sample.mp3'}}),true);
  assert.equal(ctx.voiceQuoteHasEdits(clone,{...flow,phase:'confirm'},{consent:false}),false);
});

for(const locale of ['vi','en','zh']){
  const ctx=runtime(locale);
  const render=draft=>{ctx.draft=draft;return ctx.renderFormCard(page,{featureFlows:{[route]:quote()}});};
  test(`Voice fresh quote retains its existing confirmation (${locale})`,()=>{
    const html=render({...input});
    assert.match(html,/data-portal-action="feature-confirm"/);
    assert.match(html,/data-voice-quote-edited[^>]* hidden/);
  });
  test(`Voice scalar edits cannot restore an old confirm after hydration (${locale})`,()=>{
    for(const [key,value] of Object.entries({script:'Edited script',default_voice_gender:'male',speed:'1.2',volume_percent:'100'})){
      const html=render({...input,[key]:value});
      assert.doesNotMatch(html,/data-portal-action="feature-confirm"/,key);
      assert.ok(html.includes(ctx.voiceUiText('form.quoteChanged','')));
      assert.doesNotMatch(html,/data-voice-quote-edited[^>]* hidden/);
      assert.match(html,/data-portal-action="feature-estimate"/);
    }
  });
  test(`Voice live edits hide confirm and preserve busy state when the user reverts (${locale})`,()=>{
    const values={...input,script:'Edited script'};
    const confirm={hidden:false,disabled:true};
    const note={hidden:true};
    const controls=fields.map(field=>({name:field.name,type:field.type||'text',get value(){return values[field.name];}}));
    const card={querySelectorAll:()=>[confirm]};
    const form={getAttribute:()=>route,closest:()=>card,querySelector:()=>note,querySelectorAll:()=>controls};
    ctx.synchronizeVoiceQuoteFreshness(form);
    assert.equal(confirm.hidden,true);assert.equal(note.hidden,false);assert.equal(confirm.disabled,true);
    values.script=input.script;
    ctx.synchronizeVoiceQuoteFreshness(form);
    assert.equal(confirm.hidden,false);assert.equal(note.hidden,true);assert.equal(confirm.disabled,true);
    assert.equal(values.volume_percent,'0');
  });
}
