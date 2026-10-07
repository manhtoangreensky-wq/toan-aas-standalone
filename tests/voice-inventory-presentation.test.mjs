import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a);return source.slice(a,b);}
// The escape helper ends before the next function; preserve its real body.
const safeAt=source.indexOf('  function safeText(value, fallback) {');
const safeEnd=source.indexOf('\n  }',safeAt)+4;
const renderer=section('  function renderVoiceVault(context) {','  function resolveLegacySubDubCanonicalUrl(');

for(const locale of ['vi','en','zh']){
  const context={
    ICONS:{voice:'voice'}, renderEmpty:()=>'',
    canAct:()=>true, actionBlockReason:()=>'', flowHasFreshEstimate:()=>false,
    featureKeyForPage:()=> 'savedVoice', workspaceDraftIdForRoute:()=>'',
    featureConfirmExecutionReady:()=>false, transientFormValues:()=>({}),
    classifyPageBoundary:()=> 'runtime_generator', ALLOWED_STATES:new Set(['read_only','ready','guarded'])
  };
  vm.createContext(context);vm.runInContext(catalog,context);
  context.voiceUiText=(key,fallback,params)=>context.TOANAASI18n.t(`voiceUi.${key}`,params,locale)||fallback;
  context.uiText=(key,fallback,params)=>context.TOANAASI18n.t(key,params,locale)||fallback;
  vm.runInContext(source.slice(safeAt,safeEnd)+'\n'+section('  function badge(', '  function subtitleAssetOperationsReadBadge(')+'\n'+renderer+'\n'+
    section('  function renderFields(', '  function statusMessage(')+'\n'+
    section('  function renderFormCard(', '  const ADMIN_TAB_GROUPS ='), context);
  const profiles=[{id:'qa-ready',display_name:'Giọng QA <script>',is_default:true,status:'read_only',tts_ready:true,preview_ready:true,consent_status:'confirmed',updated_at:'2026-10-07'}];
  test(`saved voice inventory shows the default marker and escapes names (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:profiles});
    assert.match(html,/Giọng QA &lt;script&gt;/);
    assert.doesNotMatch(html,/<audio\b|<script\b|onclick=/i);
    assert.match(html,locale==='vi'?/Mặc định/:locale==='en'?/Default/:/默认/);
    assert.match(html,/<details\b/);
    assert.doesNotMatch(html,/<table\b/);
  });
  test(`saved voice inventory keeps the server status (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:profiles});
    assert.match(html,/data-status="read_only"/);
    assert.match(html,locale==='vi'?/Chỉ xem/:locale==='en'?/View only/:/仅查看/);
  });
  test(`unknown voice status stays unconfirmed rather than ready (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:[{display_name:'QA',status:'unknown_state',tts_ready:false}]});
    assert.match(html,locale==='vi'?/Chưa xác nhận/:locale==='en'?/Unconfirmed/:/尚未确认/);
    assert.doesNotMatch(html,locale==='vi'?/<span>Có thể dùng để đọc<\/span>/:locale==='en'?/<span>Available for speech<\/span>/:/<span>可用于朗读<\/span>/);
  });
  test(`saved voice selection localizes default/unnamed labels without changing ready-profile filtering (${locale})`,()=>{
    const html=context.renderFormCard({path:'/voice/saved',type:'feature',action:'feature-estimate',fields:[
      {name:'voice_profile_id',label:'Giọng từ Voice Vault',control:'select',optionsFrom:'voiceProfiles',emptyLabel:'Chọn giọng',required:true}
    ]},{voiceProfiles:[...profiles,{id:'qa-unnamed',display_name:'',tts_ready:true},{id:'qa-not-ready',display_name:'blocked',tts_ready:false},{display_name:'missing id',tts_ready:true}]});
    assert.match(html,/<option value="qa-ready">Giọng QA &lt;script&gt; · /);
    assert.match(html,locale==='vi'?/Mặc định/:locale==='en'?/Default/:/默认/);
    assert.match(html,locale==='vi'?/Giọng chưa đặt tên/:locale==='en'?/Unnamed voice/:/未命名声音/);
    assert.doesNotMatch(html,/qa-not-ready|missing id|<script\b|onclick=/i);
    assert.match(html,/name="voice_profile_id"[^>]* required/);
    if(locale!=='vi') assert.doesNotMatch(html,/Mặc định|Giọng chưa đặt tên/);
  });
}
