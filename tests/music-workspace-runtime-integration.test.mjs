import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalogue=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const baseline=execFileSync('git',['show','2c216825b2b1fdfcdc4f97853961117299e39547:static/portal/portal.js'],{encoding:'utf8',maxBuffer:12*1024*1024});
function fn(text,name){const a=text.indexOf(`  function ${name}(`);assert.ok(a>=0,name);return text.slice(a,text.indexOf('\n  }',a)+4);}
const statuses=['draft','ready','guarded','awaiting_confirm','queued','processing','completed','failed','failed_no_charge','error','cancelled','refunded'];
const route='/music/song';
function runtime(locale='vi',text=source){
  const ctx={MUSIC_PRODUCT_ROUTES:['/music/create','/music/song'],ALLOWED_STATES:new Set(statuses),FEATURE_TRACKING_JOB_STATES:new Set(statuses.slice(4)),FEATURE_TRACKING_ID_PATTERN:/^[A-Za-z0-9._:-]{1,160}$/,FEATURE_TRACKING_KEY_PATTERN:/^[a-z][a-z0-9_]{1,120}$/,
    STATE_LABELS:Object.fromEntries(statuses.map(s=>[s,s])),STATE_I18N_KEYS:Object.fromEntries(statuses.map(s=>[s,`state.${s}`])),RESULT_LABELS:{prompt:'Prompt'},manifest:{[route]:{fields:[{name:'brief'}]}},normalizePath:s=>s,
    renderHero:()=>'<h1>Music</h1>',renderFormCard:()=>'<form data-test-form></form>',renderSubtitleStudioCompanionLink:()=>'',renderMusicProductGuidance:()=>'',renderInteractiveFeatureWorkbench:()=>'',stateFor:()=> 'guarded',renderEmpty:(title,body)=>`<p>${title} ${body}</p>`};
  ctx.window=ctx;vm.createContext(ctx);vm.runInContext(catalogue,ctx);ctx.TOANAASI18n.setLocale(locale,{emit:false});
  const names=['portalI18n','uiText','safeText','stateLabel','badge','musicProductText','canonicalDraftText','featureDraftTarget','canonicalDraftActions','canonicalPreferredText','resultLabel','renderCanonicalValue','renderCanonicalSuggestions','renderCanonicalFlow','safeFeatureTracking','safeVoiceReport','renderFeatureTracking','flowQuoteExpiry','flowHasFreshEstimate','voiceQuoteAmount'];
  for(const name of ['renderMusicCanonicalSuggestions','renderMusicCanonicalReport','renderMusicFlowState'])if(text.includes(`  function ${name}(`))names.push(name);
  names.push('renderWorkspace');vm.runInContext(names.map(name=>fn(text,name)).join('\n'),ctx);return ctx;
}
const workspace=(ctx,flow)=>ctx.renderWorkspace({path:route,fields:[{name:'brief'}]}, {path:route,featureFlows:{[route]:flow}});
const suggestionFlow={feature:'music_song',phase:'draft',status:'draft',message:'INTERNAL_MACHINE_COPY',data:{draft:{available:true,content:{suggestions:[{name:'QA 1',prompt:'Original prompt 1'},{name:'QA 2',prompt:'Original prompt 2'},{name:'QA 3',prompt:'Original prompt 3'}]}}}};
const plain=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();

for(const locale of ['vi','en','zh']){
  test(`Music workspace uses actual localized actions and no generic technical wrapper (${locale})`,()=>{
    const html=workspace(runtime(locale),suggestionFlow),text=plain(html);
    assert.doesNotMatch(text,/INTERNAL_MACHINE_COPY|canonical|planning|engine|provider/i);
    if(locale==='en')assert.doesNotMatch(text,/[À-ỹĐđ]/);
    if(locale==='zh')assert.doesNotMatch(text,/Sao chép|Dùng trong form|Trạng thái/);
    assert.equal((html.match(/data-portal-action="apply-canonical-draft"/g)||[]).length,3);
    assert.match(html,/data-canonical-route="\/music\/song"/);assert.match(html,/data-canonical-field="brief"/);
    assert.match(html,/Original prompt 2/);
  });
  test(`Music report-only real envelope reaches the workspace (${locale})`,()=>{
    const html=workspace(runtime(locale),{feature:'music_song',phase:'confirm',status:'processing',data:{report:{status:'processing',progress_percent:50,output_available:false,download_ready:false},tracking:{id:'qa-job-1',feature:'music_song',status:'processing'}}});
    assert.match(html,/data-music-report/);assert.match(html,/50%/);assert.match(html,/href="\/jobs\/qa-job-1"/);
    assert.doesNotMatch(html,/<audio\b|download=/i);
    assert.doesNotMatch(plain(html),/canonical|planning|engine/i);
    const direct=workspace(runtime(locale),{feature:'music_song',phase:'confirm',status:'queued',data:{id:'internal-not-a-tracking-reference',feature_key:'music_song',status:'queued',quote_xu:137,charged_xu:0}});
    assert.match(direct,/data-music-report/);
    assert.doesNotMatch(direct,/internal-not-a-tracking-reference|137 Xu|0%|<audio\b/);
  });
  test(`Music public quote is rendered, including a real zero (${locale})`,()=>{
    const ctx=runtime(locale),html=workspace(ctx,{feature:'music_song',phase:'estimate',status:'awaiting_confirm',webQuoteReceipt:'Q'.repeat(32),estimateFingerprint:'fp',data:{estimate:{available:true,content:{estimated_xu:0}}}});
    assert.match(html,/data-music-sale-price[^>]*>0 Xu</);
    const unknown=workspace(ctx,{feature:'music_song',phase:'estimate',status:'awaiting_confirm',data:{estimate:{available:true,content:{provider_cost:22}}}});
    assert.doesNotMatch(unknown,/22 Xu/);assert.match(unknown,/data-music-sale-price[^>]*>—</);
  });
  test(`Applying a Music suggestion retains text and localizes its receipt (${locale})`,()=>{
    const ctx=runtime(locale),toasts=[];
    ctx.transientFormDrafts=new Map();ctx.showToast=text=>toasts.push(text);
    ctx.document={querySelectorAll:()=>[]};ctx.setTimeout=callback=>callback();ctx.TOANAASPortal={mount(){}};
    vm.runInContext(fn(source,'transientFormValues')+'\n'+fn(source,'applyCanonicalDraftToForm'),ctx);
    ctx.applyCanonicalDraftToForm(route,'brief','Original prompt 2');
    assert.equal(ctx.transientFormValues(route).brief,'Original prompt 2');
    assert.doesNotMatch(toasts.join(' '),/planning|canonical|form\b/i);
    if(locale==='en')assert.doesNotMatch(toasts.join(' '),/[À-ỹĐđ]/);
    if(locale==='zh')assert.match(toasts.join(' '),/描述/);
  });
}
test('non-Music generic result preserves baseline escaping and visible values',()=>{
  const flow={feature:'video_product',phase:'draft',status:'draft',data:{draft:{available:true,source:'QA & <source>',content:{prompt:'A & B <script>'}}}};
  assert.equal(runtime('vi').renderCanonicalFlow(flow,'/video/product'),runtime('vi',baseline).renderCanonicalFlow(flow,'/video/product'));
});
