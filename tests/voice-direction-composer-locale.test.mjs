import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const catalog=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const receipts=JSON.parse(fs.readFileSync('tests/fixtures/voice-direction-composer-receipts.json','utf8'));
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
function fn(name){const a=source.indexOf(`  function ${name}(`),b=source.indexOf('\n  }',a)+4;assert.ok(a>=0&&b>a,name);return source.slice(a,b);}
const text=html=>html.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
for(const locale of ['vi','en','zh']){
  const ctx={renderHero:()=>'',ALLOWED_STATES:new Set(['empty','ready','guarded','read_only']),STATE_LABELS:{empty:'Empty'},STATE_I18N_KEYS:{empty:'states.empty'}};
  vm.createContext(ctx);vm.runInContext(catalog,ctx);
  ctx.uiText=(key,fallback,params)=>ctx.TOANAASI18n.has(key)?ctx.TOANAASI18n.t(key,params,locale):fallback;
  vm.runInContext(fn('safeText')+'\n'+fn('stateLabel')+'\n'+fn('badge')+'\n'+fn('voiceStudioText')+'\n'+
    section('  function renderFields(', '  function statusMessage(')+'\n'+
    section('  const VOICE_DIRECTION_COMPOSER_LANGUAGES', '  // Voice Studio is intentionally distinct'),ctx);
  const lang=locale==='vi'?'vi':'en';
  test(`Composer form translates labels/options while preserving five input contracts (${locale})`,()=>{
    const html=ctx.renderVoiceDirectionComposer({path:'/voice-studio/direction-composer'},{capabilities:{'voice-direction-compose':true}});
    const fields=ctx.voiceDirectionComposerFields();
    assert.deepEqual(Array.from(fields,f=>f.name),['text','language','suggestion_set','selected_suggestion','reading_speed']);
    assert.equal(fields[0].maxLength,260);assert.equal(fields[0].minLength,2);
    assert.deepEqual(Array.from(fields[1].options,o=>o[0]),['vi','en']);
    assert.deepEqual(Array.from(fields[2].options,o=>o[0]),['core','extended']);
    assert.match(html,/data-portal-action="voice-direction-compose"/);
    assert.match(html,/data-portal-no-transient/);
    assert.doesNotMatch(html,/portal-voice-direction-composer-intro/,'do not push the actual form behind repeated introduction/count panels');
    assert.match(html,/<details[^>]*portal-voice-direction-composer-boundary/);
    assert.doesNotMatch(text(html),/\boff\b|\bCore\b|\bExtended\b/);
    if(locale!=='en') assert.doesNotMatch(text(html),/\bdirection\b|\bdelivery\b|\bvoice profile\b|\bengine\b|\breview\b|\btext\b/i);
    if(locale==='en') assert.doesNotMatch(text(html),/[À-ỹ]/);
  });
  for(const set of ['core','extended']){
    test(`Composer renders a ${set} server receipt with three choices and translated notes (${locale})`,()=>{
      const receipt=receipts[`${lang}:${set}`];
      const html=ctx.renderVoiceDirectionComposerResult(receipt);
      assert.equal((html.match(/<li data-selected="true"/g)||[]).length,1);
      assert.match(html,/QA_CUSTOM_TEXT_UNCHANGED/);
      assert.equal((html.match(/portal-voice-direction-composer-index/g)||[]).length,3);
      assert.doesNotMatch(text(html),/pace_adjustment|pause_notes|emphasis_notes|cta_notes|female-soft|male-deep|youth-sales|luxury-cinematic|tutorial-clear|faceless-story/);
      const noteLabel={vi:'Khoảng nghỉ',en:'Pauses',zh:'停顿'};
      assert.match(text(html),new RegExp(noteLabel[locale]));
      if(locale==='en') assert.doesNotMatch(text(html),/[À-ỹ]/);
      if(locale==='vi') assert.doesNotMatch(text(html),/\breview\b|\bclaim\b|\bworkflow\b|\baudio\b|\bpreview\b|\bclone\b|\boutput\b/);
      assert.doesNotMatch(html,/<audio\b|<script\b|onclick=|(?:href|src)="https?:/i);
    });
  }
  test(`Composer rejects incomplete/provider/mismatched receipts without invented results (${locale})`,()=>{
    const valid=receipts[`${lang}:core`];
    for(const invalid of [{composer:valid.composer},{...valid,provider_called:true},{...valid,composer:{...valid.composer,selected_direction:{...valid.composer.selected_direction,choice:1}}}]){
      const html=ctx.renderVoiceDirectionComposerResult(invalid);
      assert.doesNotMatch(html,/QA_CUSTOM_TEXT_UNCHANGED|portal-voice-direction-composer-index/);
      assert.doesNotMatch(html,/<audio\b|<script\b|onclick=/i);
    }
  });
  test(`Composer localizes exact boilerplate only and leaves user or unknown text unchanged (${locale})`,()=>{
    assert.equal(ctx.voiceDirectionFixedGuidance('QA custom review <script>'), 'QA custom review <script>');
    const receipt=structuredClone(receipts[`${lang}:core`]);
    receipt.composer.text='QA user review <script>keep</script>';
    const before=JSON.stringify(receipt);
    const html=ctx.renderVoiceDirectionComposerResult(receipt);
    assert.match(html,/QA user review &lt;script&gt;keep&lt;\/script&gt;/);
    assert.doesNotMatch(html,/<script\b/);
    assert.equal(JSON.stringify(receipt),before,'presentation never changes the receipt');
  });
}
