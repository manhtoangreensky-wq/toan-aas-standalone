import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
function fn(name){const a=source.indexOf(`  function ${name}(`),b=source.indexOf('\n  }',a)+4;assert.ok(a>=0&&b>a,name);return source.slice(a,b);}
const id='00000000-0000-4000-8000-000000000001';
const fixedText=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();

for(const locale of ['vi','en','zh']){
  const ctx={ICONS:{voice:'voice',prompt:'prompt'},ALLOWED_STATES:new Set(['ready','guarded','read_only','empty']),
    renderHero:()=>'', renderEmpty:(title,description)=>`<h2>${title}</h2><p>${description}</p>`,
    transientFormValues:()=>({}), safeCatalogRoute:value=>value,isNavCurrent:()=>false,CUSTOMER_APPLICATION_ROUTE:/^\/[a-z0-9][a-z0-9._~/-]*$/i};
  vm.createContext(ctx);vm.runInContext(catalog,ctx);
  ctx.uiText=(key,fallback,params)=>ctx.TOANAASI18n.has(key)?ctx.TOANAASI18n.t(key,params,locale):fallback;
  vm.runInContext(fn('safeText')+'\n'+fn('badge')+'\n'+fn('validProjectId')+'\n'+fn('memoryListingPagination')+'\n'+fn('renderMemoryPagination')+'\n'+
    section('  function renderFields(', '  function statusMessage(')+'\n'+
    section('  // Voice Studio is intentionally distinct', '  function renderVoiceCueSheet(')+'\n'+fn('currentCustomerWorkflowGroup'),ctx);
  const data={capabilities:{'voice-studio-view':true,'voice-vault-create':true},voiceStudioReadState:'ready',
    voiceStudioListing:{pagination:{offset:50,returned:1,previous_offset:0,has_more:true,next_offset:100}},
    voiceStudioEvents:[{action:'vault_created',revision:1,created_at:'2026-10-07'}],
    voiceVaults:[{id,title:'QA_CUSTOM_TITLE',state:'active',vault_kind:'brand_narration',consent_status:'self_attested',is_default:true,revision:1,policy:{status:'guarded'}}]};

  test(`Voice Studio localizes visible fixed copy including form, default, filter, events and pagination (${locale})`,()=>{
    const html=ctx.renderVoiceStudio({path:'/voice-studio'},data),text=fixedText(html);
    assert.match(html,/QA_CUSTOM_TITLE/,'user-owned names are not translated');
    if(locale!=='en') assert.doesNotMatch(text,/direction|metadata|self-attestation|signed|consent|authoring_only|provider|audit.safe|web.native/i);
    assert.doesNotMatch(text,/authoring_only/);
    if(locale==='en') assert.doesNotMatch(text,/[À-ỹ]/);
    assert.match(text,locale==='vi'?/Lưu hồ sơ/:locale==='en'?/Save (?:voice )?profile/:/保存(?:语音)?档案/);
    assert.match(text,locale==='vi'?/Trang trước/:locale==='en'?/Previous page/:/上一页/);
    assert.match(html,/data-voice-studio-offset="100"/);
    assert.match(html,new RegExp(`/voice-studio/${id}`));
    assert.doesNotMatch(html,/<audio\b|onclick=/i);
  });
  test(`Voice Studio keeps field names, limits and option values while translating labels (${locale})`,()=>{
    const fields=ctx.voiceStudioVaultFields({});
    assert.deepEqual(Array.from(fields,f=>f.name),['title','vault_kind','language','style_notes','use_context','consent_status','consent_note','is_default','tags','project_id','content_brief_id']);
    assert.equal(fields.find(f=>f.name==='title').maxLength,180);
    assert.equal(fields.find(f=>f.name==='consent_note').maxLength,1400);
    assert.deepEqual(Array.from(fields.find(f=>f.name==='vault_kind').options,o=>o[0]),['delivery_style','brand_narration','consented_reference']);
    assert.deepEqual(Array.from(fields.find(f=>f.name==='consent_status').options,o=>o[0]),['not_required','self_attested','revoked']);
    const html=ctx.renderFields(fields,true,{},ctx.voiceStudioVaultValues({}));
    if(locale==='en') assert.doesNotMatch(fixedText(html),/[À-ỹ]/);
    assert.match(html,/name="consent_status"[^>]* required/);
    assert.match(html,/name="language"[^>]*value="vi"/);
    assert.doesNotMatch(html,/voice_profile_id|type="file"/);
  });
  test(`Voice Studio keeps the list first, hides optional filters and opens creation only on the new route (${locale})`,()=>{
    const html=ctx.renderVoiceStudio({path:'/voice-studio'},data);
    assert.ok(html.indexOf('data-portal-action="voice-studio-filter"')<html.indexOf('data-voice-studio-create'));
    assert.match(html,/<details[^>]*data-voice-studio-filters><summary>/);
    assert.doesNotMatch(html,/<details[^>]*data-voice-studio-create open/);
    const create=ctx.renderVoiceStudio({path:'/voice-studio/new'},data);
    assert.match(create,/<details[^>]*data-voice-studio-create open/);
    assert.equal((html.match(/name="q"/g)||[]).length,1);
    assert.equal((html.match(/name="state"/g)||[]).length,1);
  });
  test(`Voice Studio current navigation uses the same localized profile name (${locale})`,()=>{
    const group=ctx.currentCustomerWorkflowGroup({path:'/voice-studio',access:'member',layout:'voice-studio',title:'Voice Studio & Consent Vault'},[]);
    assert.match(group.links[0][1],locale==='vi'?/Hồ sơ giọng/:locale==='en'?/Voice profiles/:/声音档案/);
    assert.equal(group.links[0][0],'/voice-studio');
  });
  for(const state of ['loading','failed','guarded']){
    test(`Voice Studio ${state} never reveals stale profiles (${locale})`,()=>{
      const html=ctx.renderVoiceStudio({path:'/voice-studio'}, {...data,voiceStudioReadState:state});
      assert.doesNotMatch(html,/QA_CUSTOM_TITLE/);
      const text=fixedText(html);
      if(locale!=='en') assert.doesNotMatch(text,/direction|metadata|signed|consent|authoring_only|provider/i);
      if(locale==='en') assert.doesNotMatch(text,/[À-ỹ]/);
    });
  }
  test(`Voice Studio access gate keeps create controls hidden (${locale})`,()=>{
    const html=ctx.renderVoiceStudio({path:'/voice-studio'}, {...data,capabilities:{}});
    assert.doesNotMatch(html,/QA_CUSTOM_TITLE|data-portal-action="voice-vault-create"/);
    if(locale==='en') assert.doesNotMatch(fixedText(html),/[À-ỹ]/);
  });
}
