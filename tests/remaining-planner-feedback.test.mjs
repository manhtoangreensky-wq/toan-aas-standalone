import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const portal=fs.readFileSync(new URL('../static/portal/portal.js',import.meta.url),'utf8');
const integration=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const catalog=fs.readFileSync(new URL('../static/portal/portal-i18n.js',import.meta.url),'utf8');
function fn(source,name){const a=source.indexOf('  function '+name+'('),b=source.indexOf('\n  }',a)+4;assert.ok(a>=0);return source.slice(a,b);}
const cases=[['cinematic-concept','synchronizeCinematicConceptDraftFreshness'],['script-to-screen-planner','synchronizeScriptToScreenDraftFreshness'],['storyboard-composer','synchronizeStoryboardComposerDraftFreshness'],['script-to-screen-planner','reconcileScriptToScreenPlannerSaveControls'],['storyboard-composer','reconcileStoryboardComposerSaveControls']];
for(const locale of['vi','en','zh'])for(const[route,name]of cases){
 test(locale+': '+name+' stale feedback is localized and continues to lock saving',()=>{
  const noop=()=>{},note={hidden:true,textContent:''},attrs={},control={disabled:false,dataset:{},setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k]},surface={toggleAttribute:noop};
  const selectAll=s=>s.includes('save-plan')?[control]:[surface];
  const page={querySelector:()=>surface,querySelectorAll:selectAll};
  const form={id:'qa',dataset:{},getAttribute:()=>route+'-compose',querySelector:()=>note,querySelectorAll:()=>[],closest:()=>page,setAttribute:noop};
  const document={querySelector:s=>s.startsWith('form')?form:surface,querySelectorAll:selectAll,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},addEventListener:noop};
  const window={document,navigator:{language:locale},location:{pathname:'/video-studio/'+route,search:''},addEventListener:noop,dispatchEvent:noop,localStorage:{getItem:()=>null,setItem:noop}};
  const ctx=vm.createContext({window,document,URLSearchParams,URL,Intl,console});vm.runInContext(catalog,ctx);window.TOANAASI18n.setLocale(locale,{emit:false});
  Object.assign(ctx,{portalI18n:()=>window.TOANAASI18n,getBootstrap:()=>({}),base:()=>({}),currentPortalPath:()=>'/video-studio/'+route,validVideoStudioPlanId:()=>true,
   cinematicConceptFormMatchesSavedSource:()=>false,scriptToScreenFormMatchesSavedSource:()=>false,storyboardComposerFormMatchesSavedSource:()=>false,
   hydrateScriptToScreenPlannerForm:noop,ensureScriptToScreenPlannerDraftControls:noop,hydrateStoryboardComposerForm:noop,ensureStoryboardComposerDraftControls:noop,
   normalizeScriptToScreenPlannerSaveReceipt:()=>({}),normalizeStoryboardComposerPlanSaveReceipt:()=>({}),
   scriptToScreenPlanSaveSource:()=>({}),storyboardComposerPlanSaveSource:()=>({}),scriptToScreenPlanSaveReceipt:()=>null,storyboardComposerPlanSaveReceipt:()=>null,
   scriptToScreenPlanSaveSourceMatchesResult:()=>false,storyboardComposerPlanSaveSourceMatchesResult:()=>false,
   scriptToScreenPlanSaveSourceMatchesCurrentFields:()=>false,storyboardComposerPlanSaveSourceMatchesCurrentFields:()=>false,
   scriptToScreenPlannerCurrentFormFields:()=>({}),storyboardComposerCurrentFormFields:()=>({}),
   scriptToScreenPlannerComposePendingRequestEpoch:0,storyboardComposerComposePendingRequestEpoch:0,storyboardComposerSavePendingRequestEpoch:0});
  vm.runInContext(fn(portal,'uiText')+'\n'+fn(name.startsWith('reconcile')?integration:portal,name),ctx);
  ctx[name](name.startsWith('reconcile')?'/video-studio/'+route:form);
  assert.equal(control.disabled,true);assert.equal(attrs['aria-disabled'],'true');
  const expectedTitle={vi:'Hãy tạo lại kế hoạch từ lựa chọn hiện tại trước khi lưu.',en:'Generate a plan from your current choices before saving.',zh:'请根据当前选项重新生成计划后再保存。'};
  assert.equal(attrs.title,expectedTitle[locale]);
  if(!name.startsWith('reconcile')){
   assert.equal(note.hidden,false);
   assert.equal(note.textContent,{vi:'Lựa chọn đã thay đổi. Hãy tạo lại kế hoạch trước khi lưu.',en:'Your choices changed. Generate the plan again before saving.',zh:'选项已更改。请重新生成计划后再保存。'}[locale]);
  }
 });
}
