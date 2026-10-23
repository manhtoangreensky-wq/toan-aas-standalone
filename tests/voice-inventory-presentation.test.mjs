import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a);return source.slice(a,b);}
function fn(name){const a=source.indexOf(`  function ${name}(`);assert.ok(a>=0,name);return source.slice(a,source.indexOf('\n  }',a)+4);}
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
    fn('flowQuoteExpiry')+'\n'+fn('voiceQuoteExpiryState')+'\n'+
    section('  function voiceFeedbackMetrics(', '  const ADMIN_TAB_GROUPS ='), context);
  const profiles=[{id:'qa-ready',display_name:'Giọng QA <script>',is_default:true,status:'read_only',tts_ready:true,preview_ready:true,consent_status:'confirmed',updated_at:'2026-10-07'}];
  test(`saved voice inventory shows the default marker and escapes names (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:profiles,voiceInventoryReadState:'ready'});
    assert.match(html,/Giọng QA &lt;script&gt;/);
    assert.doesNotMatch(html,/<audio\b|<script\b|onclick=/i);
    assert.match(html,locale==='vi'?/Mặc định/:locale==='en'?/Default/:/默认/);
    assert.match(html,/<details\b/);
    assert.doesNotMatch(html,/<table\b/);
  });
  test(`saved voice inventory distinguishes navigation from profile transfer and omits unavailable actions (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:profiles,voiceInventoryReadState:'ready'});
    assert.match(html,/data-voice-library-actions/);
    assert.match(html,locale==='vi'?/Mở SubDub/:locale==='en'?/Open SubDub/:/打开 SubDub/);
    assert.match(html,locale==='vi'?/Mở công cụ video/:locale==='en'?/Open video tools/:/打开视频工具/);
    assert.doesNotMatch(html,/data-voice-operation|data-voice-handoff|data-voice-profile-actions/);
    assert.match(html,locale==='vi'?/chưa được chuyển/:locale==='en'?/not transferred/:/不会传递/);
    assert.doesNotMatch(html,/<audio\b|href="https?:\/\//i);
  });
  test(`saved voice inventory keeps the server status (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:profiles,voiceInventoryReadState:'ready'});
    assert.match(html,/data-status="read_only"/);
    assert.match(html,locale==='vi'?/Chỉ xem/:locale==='en'?/View only/:/仅查看/);
  });
  test(`unknown voice status stays unconfirmed rather than ready (${locale})`,()=>{
    const html=context.renderVoiceVault({voiceProfiles:[{display_name:'QA',status:'unknown_state',tts_ready:false}],voiceInventoryReadState:'ready'});
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
  test(`inventory rejects non-boolean-true flags and preserves copy (${locale})`,()=>{
    const badFlags=[false,undefined,null,0,1,-1,'','false','true','0','1',{},[]];
    const literalExpectations={
      vi:{default:'Mặc định',ready:'Có thể dùng để đọc',guarded:'Chưa thể dùng để đọc',preview:'Có thông tin bản nghe thử; cần đường dẫn được cấp quyền để phát.',noPreview:'Chưa có thông tin bản nghe thử.'},
      en:{default:'Default',ready:'Available for speech',guarded:'Not available for speech yet',preview:'Preview information exists; playback requires an authorized link.',noPreview:'No preview information yet.'},
      zh:{default:'默认',ready:'可用于朗读',guarded:'暂不可用于朗读',preview:'已有试听信息，播放需要授权链接。',noPreview:'暂无试听信息。'}
    }[locale];
    for(const bad of badFlags){
      const rawBadProfile={id:`qa-bad-${String(bad)}`,display_name:`Giọng Bad <script>`,is_default:bad,status:'read_only',tts_ready:bad,preview_ready:bad,consent_status:'confirmed',updated_at:'2026-10-07'};
      const rawSnapshot=JSON.stringify(rawBadProfile);
      const badHtml=context.renderVoiceVault({voiceProfiles:[rawBadProfile],voiceInventoryReadState:'ready'});
      assert.equal(JSON.stringify(rawBadProfile),rawSnapshot);
      assert.match(badHtml,/Giọng Bad &lt;script&gt;/);
      assert.doesNotMatch(badHtml,/<audio\b|<script\b/i);
      const summaryMatch=badHtml.match(/<summary>([\s\S]*?)<\/summary>/);
      assert.ok(summaryMatch);
      const summaryHtml=summaryMatch[1];
      assert.doesNotMatch(summaryHtml,new RegExp(literalExpectations.default));
      assert.equal(summaryHtml.match(/<span>([^<]*)<\/span>/)?.[1],literalExpectations.guarded);
      assert.match(badHtml,new RegExp(literalExpectations.noPreview));
      assert.doesNotMatch(badHtml,new RegExp(literalExpectations.preview));
    }
    const trueHtml=context.renderVoiceVault({voiceProfiles:profiles,voiceInventoryReadState:'ready'});
    const trueSummaryMatch=trueHtml.match(/<summary>([\s\S]*?)<\/summary>/);
    assert.ok(trueSummaryMatch);
    assert.match(trueSummaryMatch[1],new RegExp(literalExpectations.default));
    assert.equal(trueSummaryMatch[1].match(/<span>([^<]*)<\/span>/)?.[1],literalExpectations.ready);
    assert.match(trueHtml,new RegExp(literalExpectations.preview));
    assert.doesNotMatch(trueHtml,new RegExp(literalExpectations.noPreview));
  });
  test(`generic select options strictly filter tts_ready and format default marker (${locale})`,()=>{
    const badFlags=[false,undefined,null,0,1,-1,'','false','true','0','1',{},[]];
    for(const bad of badFlags){
      const voiceProfiles=[
        {id:'qa-bad-tts',display_name:'Bad TTS',tts_ready:bad,is_default:true},
        {id:'qa-bad-default',display_name:'Bad Default',tts_ready:true,is_default:bad},
        {id:'qa-good',display_name:'Good Profile',tts_ready:true,is_default:true},
        {display_name:'Missing ID',tts_ready:true,is_default:true}
      ];
      const snapshot=JSON.stringify(voiceProfiles);
      const html=context.renderFields([
        {name:'voice_profile_id',label:'Voice',control:'select',optionsFrom:'voiceProfiles',emptyLabel:'Choose voice',required:true}
      ],true,{voiceProfiles},{});
      assert.equal(JSON.stringify(voiceProfiles),snapshot);
      assert.doesNotMatch(html,/<option[^>]*value="qa-bad-tts"/);
      assert.doesNotMatch(html,/Bad TTS/);
      assert.doesNotMatch(html,/Missing ID/);
      assert.match(html,/<option[^>]*value="qa-bad-default"[^>]*>Bad Default<\/option>/);
      assert.doesNotMatch(html,/<option[^>]*value="qa-bad-default"[^>]*>Bad Default · Mặc định<\/option>/);
      assert.match(html,/<option[^>]*value="qa-good"[^>]*>Good Profile · Mặc định<\/option>/);
    }
  });
  test(`voice form select card enforces canonical flags and localizes default marker (${locale})`,()=>{
    const badFlags=[false,undefined,null,0,1,-1,'','false','true','0','1',{},[]];
    const expectedMarker={vi:' · Mặc định',en:' · Default',zh:' · 默认'}[locale];
    for(const bad of badFlags){
      const voiceProfiles=[
        {id:'qa-bad-tts',display_name:'Bad TTS <tag>',tts_ready:bad,is_default:true},
        {id:'qa-bad-default',display_name:'Bad Default <tag>',tts_ready:true,is_default:bad},
        {id:'qa-good',display_name:'Good Voice <tag>',tts_ready:true,is_default:true},
        {display_name:'Missing ID',tts_ready:true,is_default:true}
      ];
      const snapshot=JSON.stringify(voiceProfiles);
      const html=context.renderFormCard({path:'/voice/saved',type:'feature',action:'feature-estimate',fields:[
        {name:'voice_profile_id',label:'Voice',control:'select',optionsFrom:'voiceProfiles',emptyLabel:'Choose voice',required:true}
      ]},{voiceProfiles});
      assert.equal(JSON.stringify(voiceProfiles),snapshot);
      assert.doesNotMatch(html,/<option[^>]*value="qa-bad-tts"/);
      assert.doesNotMatch(html,/Bad TTS/);
      assert.doesNotMatch(html,/Missing ID/);
      assert.match(html,/<option[^>]*value="qa-bad-default"[^>]*>Bad Default &lt;tag&gt;<\/option>/);
      assert.doesNotMatch(html,new RegExp(`<option[^>]*value="qa-bad-default"[^>]*>Bad Default &lt;tag&gt;${expectedMarker}<\\/option>`));
      assert.match(html,new RegExp(`<option[^>]*value="qa-good"[^>]*>Good Voice &lt;tag&gt;${expectedMarker}<\\/option>`));
    }
  });
}
