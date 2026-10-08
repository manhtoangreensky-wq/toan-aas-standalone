import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
function fn(name){const a=source.indexOf(`  function ${name}(`),b=source.indexOf('\n  }',a)+4;assert.ok(a>=0&&b>a,name);return source.slice(a,b);}
const route='/voice/tts';
const page={path:route,access:'member',type:'feature',action:'feature-estimate',status:'guarded',fields:[{name:'script',label:'Script',control:'textarea',required:true}]};
const visible=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const makeContext=()=>({path:route,session:{authenticated:true,csrfReady:true},bridge:{available:true,csrfReady:true,featureExecutionFeatures:['voice_tts'],featureExecutionAvailable:true},capabilities:{'feature-estimate':true,'feature-confirm':true},catalog:[{key:'voice_tts',route}],workspaceDraftFeatures:[],pageStates:{}});
const quote=(xu=3)=>({phase:'estimate',feature:'voice_tts',status:'awaiting_confirm',estimateFingerprint:'qa-fingerprint',webQuoteReceipt:'Q'.repeat(48),input:{script:'QA_SCRIPT'},data:{estimate:{available:true,estimated_xu:xu,character_count:9,source:'internal_catalog',source_price_usd:'SECRET_COST',cost_minor:92391}}});

for(const locale of ['vi','en','zh']){
  const ctx={manifest:{[route]:page},FEATURE_PAGE_KEY_ALIASES:{[route]:'voice_tts'},WEB_LOCAL_ACTIONS:new Set(),transientWorkspaceDraftIds:new Map(),transientFormDrafts:new Map(),
    renderHero:()=>'',renderSummary:()=>'',renderStatusCard:()=>'',renderNotes:()=>'',renderInteractiveFeatureWorkbench:()=>'',renderSubtitleStudioCompanionLink:()=>'',renderFeatureBotHandoff:()=>'',
    renderEmpty:(title,body)=>`<h3>${title}</h3><p>${body}</p>`,classifyPageBoundary:()=> 'runtime_generator'};
  vm.createContext(ctx);vm.runInContext(catalog,ctx);ctx.uiText=(k,f,p)=>ctx.TOANAASI18n.has(k)?ctx.TOANAASI18n.t(k,p,locale):f;
  vm.runInContext(fn('safeText')+'\n'+fn('normalizePath')+'\n'+fn('validProjectId')+'\n'+fn('validWorkspaceDraftId')+'\n'+section('  const ALLOWED_STATES','  const PAYMENT_STATUS_LABELS')+'\n'+fn('badge')+'\n'+fn('canAct')+'\n'+fn('telegramIdentityLinked')+'\n'+fn('actionBlockReason')+'\n'+fn('stateFor')+'\n'+fn('voiceUiText')+'\n'+fn('workspaceDraftIdForRoute')+'\n'+
    section('  function renderFields(', '  function statusMessage(')+'\n'+section('  function flowHasFreshEstimate(', '  const ADMIN_TAB_GROUPS')+'\n'+
    section('  const RESULT_LABELS', '  const SUBTITLE_STUDIO_COMPANION_INTENTS')+'\n'+fn('renderWorkspace'),ctx);
  const render=(flow,overrides={})=>ctx.renderWorkspace(page,{...makeContext(),...overrides,featureFlows:{[route]:flow}});
  test(`Voice quote is localized, preserves zero/unknown, and hides provider costs (${locale})`,()=>{
    const html=render(quote());
    assert.match(visible(html),/3 Xu/);
    assert.doesNotMatch(html,/SECRET_COST|92391|internal_catalog|source_price_usd|cost_minor/);
    if(locale==='en') assert.doesNotMatch(visible(html),/[À-ỹ]/);
    if(locale!=='en') assert.doesNotMatch(visible(html),/canonical|Core Bridge|planning|Job Center|adapter|Output engine/i);
    assert.match(visible(render(quote(0))),/0 Xu/);
    assert.doesNotMatch(visible(render(quote(null))),/0 Xu/);
    assert.doesNotMatch(render(quote(null)),/data-portal-action="feature-confirm"/,'do not offer money confirmation when the public price is unknown');
    const withCost=quote(3);withCost.data.estimate.cost_xu=98765;
    assert.match(visible(render(withCost)),/3 Xu/,'an internal cost must not replace a public quote');
    const costOnly=quote(null);costOnly.data.estimate.cost_xu=98765;
    assert.doesNotMatch(visible(render(costOnly)),/98765/,'do not label ambiguous cost data as a sale price');
    assert.doesNotMatch(render(costOnly),/data-portal-action="feature-confirm"/);
  });
  test(`Voice retains existing draft copy/apply controls without creating media (${locale})`,()=>{
    const html=render({phase:'draft',status:'draft',feature:'voice_tts',data:{draft:{available:true,content:{script:'QA_SCRIPT <script>'}}}});
    assert.match(html,/data-portal-action="copy-canonical-draft"/);
    assert.match(html,/data-portal-action="apply-canonical-draft"/);
    assert.match(html,/data-canonical-field="script"/);
    assert.doesNotMatch(html,/<script\b|<audio\b/);
    if(locale==='en')assert.doesNotMatch(visible(html),/[À-ỹ]/);
  });
  test(`Voice confirmation stays gated by a fresh receipt and actual execution access (${locale})`,()=>{
    assert.match(render(quote()),/data-portal-action="feature-confirm"/);
    for(const broken of [{...quote(),webQuoteReceipt:''},{...quote(),estimateFingerprint:''},{...quote(),data:{estimate:{available:false}}},{...quote(),phase:'draft'},{...quote(),data:{estimate:{available:true,tier_required:true}}}])assert.doesNotMatch(render(broken),/data-portal-action="feature-confirm"/);
    const noAccess=makeContext();noAccess.capabilities['feature-confirm']=false;
    assert.doesNotMatch(render(quote(),noAccess),/data-portal-action="feature-confirm"/);
  });
  test(`Voice disabled form tooltip follows the selected locale (${locale})`,()=>{
    const blocked=makeContext();blocked.capabilities['feature-estimate']=false;
    const html=render(quote(),blocked);
    const title=html.match(/<button class="portal-button portal-button--primary" type="submit" disabled title="([^"]+)"/);
    assert.ok(title,'guarded form should expose an accessible localized explanation');
    assert.equal(title[1],ctx.uiText('voiceUi.form.guarded','',locale));
    if(locale==='en')assert.doesNotMatch(title[1],/[À-ỹ]/);
  });
  test(`Voice runtime readiness does not imply audio or a confirmed job (${locale})`,()=>{
    const html=render({phase:'estimate',status:'ready',feature:'voice_tts',data:{}});
    assert.match(visible(html),new RegExp(ctx.uiText('voiceUi.flow.state.ready','',locale).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
    assert.doesNotMatch(html,/data-portal-action="feature-confirm"|<audio\b|<source\b|href="\/jobs\//);
  });
  test(`Voice shows the quote before confirmation and clearly marks stale quotes (${locale})`,()=>{
    const html=render(quote());
    assert.ok(html.indexOf('data-voice-sale-price')<html.indexOf('data-portal-form'),'price must precede the confirmation form');
    const stale=visible(render({...quote(),webQuoteReceipt:''}));
    assert.match(stale,locale==='vi'?/làm mới/:locale==='en'?/refresh/i:/重新获取/);
  });
  test(`Voice draft controls stay localized when quote execution and local authoring are both available (${locale})`,()=>{
    const html=render(quote(),{workspaceDraftFeatures:['voice_tts'],capabilities:{...makeContext().capabilities,'workspace-draft-save':true}});
    assert.match(html,/data-portal-action="workspace-draft-save"/);
    if(locale==='en')assert.doesNotMatch(visible(html),/[À-ỹ]/);
    ctx.transientWorkspaceDraftIds.set(route,'00000000-0000-4000-8000-000000000010');
    try {
      const resumed=render(quote(),{workspaceDraftFeatures:['voice_tts'],capabilities:{...makeContext().capabilities,'workspace-draft-save':true,'workspace-draft-update':true}});
      const saveNew=resumed.match(/<button[^>]*data-portal-action="workspace-draft-save"[^>]*>([^<]*)<\/button>/);
      assert.ok(saveNew,'resumed draft retains the save-new action');
      assert.equal(saveNew[1],{vi:'Lưu thành bản mới',en:'Save as a new draft',zh:'另存为新草稿'}[locale]);
      assert.match(resumed,/data-portal-action="workspace-draft-update"/);
    } finally { ctx.transientWorkspaceDraftIds.delete(route); }
  });
  for(const status of ['queued','processing','completed','failed','failed_no_charge','cancelled','refunded']){
    test(`Voice ${status} uses only matching tracking and never fabricates media (${locale})`,()=>{
      const f={phase:'confirm',status,feature:'voice_tts',message:'QA_SERVER_MESSAGE <script>',data:{tracking:{id:'QA-job-01',feature:'voice_tts',status},output_available:true,output_url:'https://invalid.example/private.mp3'}};
      const html=render(f);
      assert.ok(html.indexOf('data-voice-flow-state')<html.indexOf('data-portal-form'),'current task status must precede the old form');
      assert.match(html,/<details[^>]*data-voice-task-form/);
      assert.match(html,/href="\/jobs\/QA-job-01"/);
      assert.doesNotMatch(html,/<audio\b|src=|https:\/\/invalid\.example|<script\b/);
      assert.match(html,/QA_SERVER_MESSAGE &lt;script&gt;/);
      if(locale==='en')assert.doesNotMatch(visible(html),/[À-ỹ]/);
      for(const invalid of [{...f,data:{tracking:{...f.data.tracking,feature:'video_ai_prompt'}}},{...f,data:{tracking:{...f.data.tracking,status:'unknown'}}},{...f,data:{job_id:'QA-job-01'}}])assert.doesNotMatch(render(invalid),/href="\/jobs\/QA-job-01"/);
    });
  }
  test(`Voice error preserves escaped server feedback without fake output (${locale})`,()=>{
    const html=render({phase:'estimate',status:'error',feature:'voice_tts',message:'QA_ERROR <script>',data:{}});
    assert.match(html,/QA_ERROR &lt;script&gt;/);assert.doesNotMatch(html,/<audio\b|<script\b|feature-confirm/);
    if(locale==='en')assert.doesNotMatch(visible(html),/[À-ỹ]/);
  });
}
