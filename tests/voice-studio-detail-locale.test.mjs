import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
function fn(name){const a=source.indexOf(`  function ${name}(`),b=source.indexOf('\n  }',a)+4;assert.ok(a>=0&&b>a,name);return source.slice(a,b);}
const id='00000000-0000-4000-8000-000000000001',sid='00000000-0000-4000-8000-000000000010';
const text=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
for(const locale of ['vi','en','zh']){
  const ctx={ICONS:{voice:'voice'},renderHero:()=>'',renderEmpty:(title,description)=>`<h2>${title}</h2><p>${description}</p>`,ALLOWED_STATES:new Set(['empty','ready','guarded','read_only']),STATE_I18N_KEYS:{empty:'states.empty'},STATE_LABELS:{empty:'Empty'}};
  vm.createContext(ctx);vm.runInContext(catalog,ctx);ctx.uiText=(k,f,p)=>ctx.TOANAASI18n.has(k)?ctx.TOANAASI18n.t(k,p,locale):f;
  vm.runInContext(fn('safeText')+'\n'+fn('stateLabel')+'\n'+fn('badge')+'\n'+fn('validProjectId')+'\n'+section('  function renderFields(', '  function statusMessage(')+'\n'+section('  // Voice Studio is intentionally distinct', '  // Video Production Studio'),ctx);
  const page={path:'/voice-studio/:id',routePath:`/voice-studio/${id}`,recordId:id};
  const capabilities=Object.fromEntries(['voice-studio-view','voice-vault-update','voice-vault-archive','voice-vault-restore','voice-vault-duplicate','voice-vault-restore-version','voice-vault-compose','voice-script-create','voice-script-update','voice-script-archive','voice-script-restore','voice-script-duplicate','voice-script-restore-version','voice-script-cue-sheet'].map(k=>[k,true]));
  const vault={id,title:'QA_PROFILE <script>',state:'active',vault_kind:'brand_narration',consent_status:'self_attested',language:'vi',revision:3};
  const script={id:sid,title:'QA_SCRIPT',state:'active',script_kind:'narration',source_kind:'local_deterministic_draft_only',script_text:'QA_BODY',revision:2,language:'vi',versions:[{revision:1}]};
  const data={capabilities,voiceStudioReadState:'ready',voiceVaultDetail:{vault,scripts:[script],versions:[{revision:1}],events:[{action:'script_created'}]}};
  test(`Voice detail keeps localized status/source/version buttons and unchanged IDs/limits (${locale})`,()=>{
    const html=ctx.renderVoiceStudioDetail(page,data),fixed=text(html);
    assert.match(html,/QA_PROFILE &lt;script&gt;/);assert.doesNotMatch(html,/<script\b|onclick=|<audio\b/i);
    assert.match(html,new RegExp(`data-voice-vault-id="${id}"`));assert.match(html,/data-voice-vault-revision="3"/);
    assert.match(html,new RegExp(`data-voice-script-id="${sid}"`));
    assert.match(fixed,locale==='vi'?/Trạng thái/:locale==='en'?/Status/:/状态/);
    assert.match(fixed,locale==='vi'?/Từ bộ soạn thảo/:locale==='en'?/Composer/:/来自编排器/);
    assert.match(html,/<button[^>]*data-portal-action="voice-vault-restore-version"[^>]*>[^<]*\S[^<]*v1<\/button>/);
    if(locale==='en') assert.doesNotMatch(fixed,/[À-ỹ]/);
    const f=ctx.voiceStudioScriptFields();assert.deepEqual(Array.from(f,x=>x.name),['title','script_kind','language','audience','pace_wpm','script_text','delivery_notes','pronunciation_notes','tags']);
    assert.equal(f.find(x=>x.name==='script_text').maxLength,24000);assert.equal(f.find(x=>x.name==='pace_wpm').min,80);assert.equal(f.find(x=>x.name==='pace_wpm').max,240);
  });
  test(`Voice detail blocks wrong record and localizes absent/loading/failed states (${locale})`,()=>{
    for(const readState of ['loading','failed','guarded','ready']){
      const html=ctx.renderVoiceStudioDetail(page,{capabilities,voiceStudioReadState:readState,voiceVaultDetail:{}});
      assert.doesNotMatch(html,/QA_PROFILE|voice-vault-update|voice-script-update/);
      if(locale==='en') assert.doesNotMatch(text(html),/[À-ỹ]/);
    }
    const html=ctx.renderVoiceStudioDetail({...page,recordId:sid},data);assert.doesNotMatch(html,/QA_PROFILE|QA_BODY/);
  });
  test(`Revoked rights preserve archive but lock compose/duplicate/script/cue actions (${locale})`,()=>{
    const d={...data,voiceVaultDetail:{...data.voiceVaultDetail,vault:{...vault,vault_kind:'consented_reference',consent_status:'revoked'}}};
    const html=ctx.renderVoiceStudioDetail(page,d);
    for(const action of ['voice-vault-compose','voice-vault-duplicate','voice-script-duplicate','voice-script-cue-sheet','voice-script-restore-version']){assert.match(html,new RegExp(`<button[^>]*data-portal-action="${action}"[^>]* disabled`));}
    assert.match(html,/<button[^>]*data-portal-action="voice-vault-archive"[^>]*(?<! disabled)>/);
    const archived=ctx.renderVoiceStudioDetail(page,{...data,voiceVaultDetail:{...data.voiceVaultDetail,vault:{...vault,state:'archived'}}});
    assert.match(archived,/<button[^>]*data-portal-action="voice-vault-restore"/);
    assert.match(archived,/<button[^>]*data-portal-action="voice-vault-compose"[^>]* disabled/);
  });
  test(`Cue sheets require a matching no-audio receipt and escape script text (${locale})`,()=>{
    const cue={script_id:sid,execution:'local_deterministic_writing_aid',provider_called:false,audio_created:false,metrics:{words:4,sentences:1,estimated_seconds:2,pace_wpm:120},items:[{index:1,start_seconds:0,end_seconds:2,text:'QA <script>',word_count:2}]};
    const html=ctx.renderVoiceCueSheet(cue,sid);assert.match(html,/QA &lt;script&gt;/);assert.doesNotMatch(html,/<audio\b|<script\b|onclick=/i);
    for(const invalid of [{...cue,script_id:id},{...cue,provider_called:true},{...cue,audio_created:true},{...cue,execution:'unknown'}]) assert.equal(ctx.renderVoiceCueSheet(invalid,sid),'');
    if(locale==='en') assert.doesNotMatch(text(html),/[À-ỹ]/);
  });
}
