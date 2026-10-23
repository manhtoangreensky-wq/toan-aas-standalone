import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8').replace(/\r\n/g,'\n');
const catalogue=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
function fn(name){const a=source.indexOf(`  function ${name}(`);assert.ok(a>=0,name);const b=source.indexOf('\n  }',a);assert.ok(b>a,name);return source.slice(a,b+4);}
function presets(name){const a=source.indexOf(`  const ${name} = Object.freeze([`);assert.ok(a>=0,name);return source.slice(a,source.indexOf('\n  ]);',a)+7);}
const lanes={
  music:{action:'music-direction-preset-compose',prefix:'music-direction',input:'web_preset_id',
    sync:'synchronizeMusicDirectionPresetForm',edit:'markMusicDirectionPresetDraftEdited',event:'toanaas:music-direction-preset-draft-edited',
    labels:[['commercial_bright','Thương mại sáng','Bright commercial','明亮商业'],['technology_future','Công nghệ tương lai','Future technology','未来科技'],['cinematic_brand','Cinematic thương hiệu','Cinematic brand','品牌电影感'],['warm_story','Kể chuyện ấm','Warm story','温暖故事'],['short_viral','Short-form bắt nhịp','Short-form momentum','短内容节奏']],
    unselected:['Chưa chọn preset. Hãy chọn một hướng trước khi lập hướng.','No preset selected. Choose one before creating a direction.','尚未选择预设。创建方向前请选择一个。'],
    selected:[label=>`Đã chọn ${label}. Hoàn tất brief rồi bấm lập hướng.`,label=>`${label} selected. Complete the brief and create the direction.`,label=>`已选择 ${label}。完成摘要后创建方向。`],
    stale:['Nội dung đã thay đổi. Các hướng bên dưới thuộc nội dung trước; lập lại hướng âm nhạc để cập nhật.','The brief has changed. The directions below use the previous brief; create music directions again to update them.','摘要已更改。下方方向仍基于先前内容，请重新创建音乐方向以更新。']},
  sfx:{action:'sfx-cue-sheet-compose',prefix:'sfx-cue-sheet',input:'web_sfx_preset_id',
    sync:'synchronizeSfxCueSheetForm',edit:'markSfxCueSheetDraftEdited',event:'toanaas:sfx-cue-sheet-draft-edited',
    labels:[['motion_transition','Chuyển động mượt','Smooth transition','流畅转场'],['interface_confirm','Xác nhận giao diện','Interface confirmation','界面确认'],['reveal_impact','Điểm nhấn mở lộ','Reveal impact','揭示强调'],['status_signal','Tín hiệu trạng thái','Status signal','状态信号'],['caption_emphasis','Nhấn chú thích / lời kêu gọi','Caption / call-to-action emphasis','字幕 / 行动号召强调']],
    unselected:['Chưa chọn preset. Hãy chọn một hướng trước khi lập cue sheet.','No preset selected. Choose one before creating the cue sheet.','尚未选择预设。创建提示表前请选择一个。'],
    selected:[label=>`Đã chọn ${label}. Hoàn tất brief rồi bấm lập cue sheet.`,label=>`${label} selected. Complete the brief and create the cue sheet.`,label=>`已选择 ${label}。完成摘要后创建提示表。`],
    stale:['Nội dung đã thay đổi. Bảng hiệu ứng bên dưới thuộc nội dung trước; lập lại bảng để cập nhật.','The brief has changed. The cue sheet below uses the previous brief; create the cue sheet again to update it.','摘要已更改。下方音效提示表仍基于先前内容，请重新创建提示表以更新。']}
};
function harness(locale,lane,{id='',enabled='true',receipt=false,stale=false}={}){
  const events=[];let remembers=0;
  const forbidden=()=>{throw Error('Unexpected network/storage/submit/navigation');};
  const ctx={window:{dispatchEvent:e=>events.push(e.type),fetch:forbidden,location:{assign:forbidden,replace:forbidden}},
    fetch:forbidden,localStorage:{getItem:forbidden,setItem:forbidden},sessionStorage:{getItem:forbidden,setItem:forbidden},
    CustomEvent:class{constructor(type){this.type=type;}},rememberSfxCueSheetTransientDraft:()=>{remembers++;}};
  vm.createContext(ctx);vm.runInContext(catalogue,ctx);
  ctx.uiText=(key,fallback,params)=>ctx.window.TOANAASI18n.t(key,params,locale)||fallback;
  vm.runInContext(presets('MUSIC_DIRECTION_PRESETS')+'\n'+presets('SFX_CUE_SHEET_PRESETS')+
    '\nconst MUSIC_DIRECTION_PRESET_IDS=new Set(MUSIC_DIRECTION_PRESETS.map(x=>x.id));const SFX_CUE_SHEET_PRESET_IDS=new Set(SFX_CUE_SHEET_PRESETS.map(x=>x.id));\n'+
    ['musicDirectionUiText','musicDirectionPresetText','sfxCueSheetUiText','sfxCueSheetPresetText',...Object.values(lanes).flatMap(x=>[x.sync,x.edit])].map(fn).join('\n'),ctx);
  const note={textContent:'INITIAL'},input={value:id},description={value:'Keep this draft <script>'};
  const attrs={'data-stale':stale?'true':'false'};
  const result={textContent:'Keep the original result <script>',getAttribute:k=>attrs[k]??null,setAttribute:(k,v)=>attrs[k]=v};
  const submit={disabled:false,attrs:{},setAttribute(k,v){this.attrs[k]=v;}};
  const cards=lane.labels.map(([value])=>({attrs:{[`data-${lane.prefix}-preset-card`]:value},getAttribute(k){return this.attrs[k];},setAttribute(k,v){this.attrs[k]=v;}}));
  const form={getAttribute:k=>k==='data-portal-action'?lane.action:k===`data-${lane.prefix}-compose-enabled`?enabled:null,
    querySelector:q=>q===`input[name="${lane.input}"]:checked`?(input.value?input:null):q===`[data-${lane.prefix}-selection]`?note:q===`[data-${lane.prefix}-submit]`?submit:q==='[name="description"]'?description:null,
    querySelectorAll:q=>q===`[data-${lane.prefix}-preset-card]`?cards:[],
    closest:()=>({querySelector:()=>receipt?result:null}),submit:forbidden,requestSubmit:forbidden,reset:forbidden};
  return {ctx,form,note,input,description,result,attrs,submit,cards,events,get remembers(){return remembers;}};
}
for(const [index,locale] of ['vi','en','zh'].entries())for(const [name,lane] of Object.entries(lanes)){
  test(`localized selection, all five presets, cards and submit (${name}/${locale})`,()=>{
    for(const row of lane.labels){const h=harness(locale,lane,{id:row[0]});h.ctx[lane.sync](h.form);
      assert.equal(h.note.textContent,lane.selected[index](row[index+1]));assert.equal(h.submit.disabled,false);assert.equal(h.submit.attrs['aria-disabled'],'false');
      assert.deepEqual(h.cards.map(c=>c.attrs['data-selected']),lane.labels.map(([id])=>String(id===row[0])));assert.equal(h.events.length,0);}
  });
  test(`unselected/unknown/disabled remain fail-closed (${name}/${locale})`,()=>{
    for(const id of ['', 'unknown-preset']){const h=harness(locale,lane,{id});h.ctx[lane.sync](h.form);assert.equal(h.note.textContent,lane.unselected[index]);assert.equal(h.submit.disabled,true);assert.equal(h.submit.attrs['aria-disabled'],'true');}
    for(const enabled of ['false','1','TRUE','',null]){const h=harness(locale,lane,{id:lane.labels[0][0],enabled});h.ctx[lane.sync](h.form);assert.equal(h.submit.disabled,true);assert.equal(h.submit.attrs['aria-disabled'],'true');}
  });
  test(`no result keeps selection feedback without inventing a result (${name}/${locale})`,()=>{
    const h=harness(locale,lane,{id:lane.labels[0][0]});h.ctx[lane.edit](h.form);
    assert.equal(h.note.textContent,lane.selected[index](lane.labels[0][index+1]));assert.equal(h.attrs['data-stale'],'false');
    assert.deepEqual(h.events,[lane.event]);assert.equal(h.remembers,name==='sfx'?1:0);
  });
  test(`three edits preserve localized stale feedback and content (${name}/${locale})`,()=>{
    for(const stale of [false,true]){const h=harness(locale,lane,{id:lane.labels[0][0],receipt:true,stale});
      for(let n=1;n<=3;n++){h.ctx[lane.edit](h.form);assert.equal(h.note.textContent,lane.stale[index]);assert.equal(h.attrs['data-stale'],'true');
        assert.equal(h.result.textContent,'Keep the original result <script>');assert.equal(h.description.value,'Keep this draft <script>');assert.equal(h.input.value,lane.labels[0][0]);
        assert.deepEqual(h.events,Array(n).fill(lane.event));assert.equal(h.remembers,name==='sfx'?n:0);}}
  });
  test(`null and unrelated form are no-ops (${name}/${locale})`,()=>{
    const h=harness(locale,lane);const unrelated={getAttribute:()=> 'unrelated',querySelector:()=>{throw Error('unrelated form queried');}};
    for(const form of [null,undefined,unrelated]){h.ctx[lane.sync](form);h.ctx[lane.edit](form);}assert.equal(h.events.length,0);assert.equal(h.remembers,0);
  });
}
