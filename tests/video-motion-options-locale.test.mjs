import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const fixtures={
  "sentinel": "CUSTOMER Studio media Facebook TikTok & tên riêng",
  "motion": {
    "creativeMotionGuideEnabled": true,
    "capabilities": {
      "creative-motion-guide-compose": true,
      "creative-motion-guide-suggest": true
    }
  }
};
const table=[
  [
    "topic.product",
    "Sản phẩm / quảng cáo",
    "Sản phẩm / quảng cáo",
    "Product / advertising",
    "产品／广告"
  ],
  [
    "topic.affiliate",
    "Affiliate / TikTok Shop",
    "Tiếp thị liên kết / TikTok Shop",
    "Affiliate marketing / TikTok Shop",
    "联盟营销／TikTok Shop"
  ],
  [
    "topic.ai_tool",
    "AI tool / phần mềm",
    "Công cụ trí tuệ nhân tạo / phần mềm",
    "AI tools / software",
    "人工智能工具／软件"
  ],
  [
    "topic.place",
    "Địa điểm / không gian",
    "Địa điểm / không gian",
    "Place / space",
    "地点／空间"
  ],
  [
    "topic.fashion",
    "Thời trang / lifestyle",
    "Thời trang / lối sống",
    "Fashion / lifestyle",
    "时尚／生活方式"
  ],
  [
    "topic.food",
    "Food / nhà hàng / đồ uống",
    "Ẩm thực / nhà hàng / đồ uống",
    "Food / restaurant / drinks",
    "美食／餐厅／饮品"
  ],
  [
    "topic.education",
    "Giáo dục / hướng dẫn",
    "Giáo dục / hướng dẫn",
    "Education / tutorial",
    "教育／教程"
  ],
  [
    "topic.story",
    "Câu chuyện cinematic",
    "Câu chuyện điện ảnh",
    "Cinematic story",
    "电影感故事"
  ],
  [
    "topic.custom",
    "Tự nhập chủ đề",
    "Tự nhập chủ đề",
    "Enter a custom topic",
    "输入自定义主题"
  ],
  [
    "style.cinematic",
    "Cinematic",
    "Điện ảnh",
    "Cinematic",
    "电影感"
  ],
  [
    "style.tiktok",
    "TikTok / Reels nhanh",
    "TikTok / Reels nhịp nhanh",
    "Fast-paced TikTok / Reels",
    "快节奏TikTok／Reels"
  ],
  [
    "style.tutorial",
    "Tutorial hướng dẫn",
    "Hướng dẫn từng bước",
    "Step-by-step tutorial",
    "分步教程"
  ],
  [
    "style.ads",
    "Quảng cáo bán hàng",
    "Quảng cáo bán hàng",
    "Sales advertisement",
    "销售广告"
  ],
  [
    "style.fpv",
    "FPV / drone motion",
    "Góc nhìn thứ nhất / chuyển động thiết bị bay",
    "First-person view / drone movement",
    "第一人称视角／无人机运动"
  ],
  [
    "style.reveal",
    "3D / product reveal",
    "Giới thiệu sản phẩm ba chiều",
    "3D product reveal",
    "三维产品展示"
  ],
  [
    "style.ugc",
    "UGC đời thường",
    "Nội dung người dùng đời thường",
    "Everyday user-generated content",
    "日常用户创作内容"
  ],
  [
    "language.vi",
    "Tiếng Việt",
    "Tiếng Việt",
    "Vietnamese",
    "越南语"
  ],
  [
    "language.en",
    "English",
    "Tiếng Anh",
    "English",
    "英语"
  ],
  [
    "language.zh",
    "中文（简体）",
    "Tiếng Trung giản thể",
    "Simplified Chinese",
    "简体中文"
  ]
];
const locales=['vi','en','zh'];
const route='/video-studio/motion-guide';
const clone=value=>JSON.parse(JSON.stringify(value));
const decode=value=>String(value).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const text=value=>decode(value.replace(/<[^>]+>/g,''));
function formFor(result){
  const form=result.html.match(/<form\b[^>]*data-portal-action="creative-motion-guide-compose"[\s\S]*?<\/form>/)?.[0];
  assert.ok(form,'The actual motion form must be rendered');
  return form;
}
function controls(form){
  const selects=[...form.matchAll(/<select\b([^>]*)>([\s\S]*?)<\/select>/g)].map(match=>({
    name:match[1].match(/name="([^"]+)"/)?.[1],disabled:/\bdisabled\b/.test(match[1]),
    options:[...match[2].matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/g)].map(option=>({
      value:decode(option[1].match(/value="([^"]*)"/)?.[1]||''),selected:/\bselected\b/.test(option[1]),label:text(option[2])
    }))
  }));
  const buttons=[...form.matchAll(/<button\b([^>]*)>/g)].map(match=>({
    action:match[1].match(/data-portal-action="([^"]+)"/)?.[1]||'submit',
    disabled:/\bdisabled\b/.test(match[1])
  }));
  return {selects,buttons};
}
const values={topic_kind:['product','affiliate','ai_tool','place','fashion','food','education','story','custom'],language:['vi','en','zh'],style:['cinematic','tiktok','tutorial','ads','fpv','reveal','ugc']};
const prefixes={topic_kind:'topic.',language:'language.',style:'style.'};
const rendered=new Map();
for(const locale of locales)for(const state of ['ready','guarded']){
  const raw=clone(fixtures.motion);
  raw.capabilities['creative-motion-guide-compose']=state==='ready';
  raw.capabilities['creative-motion-guide-suggest']=state==='ready';
  const before=JSON.stringify(raw),result=renderChild(locale,route,raw),form=formFor(result);
  assert.equal(JSON.stringify(raw),before,'The real renderer may not mutate raw input');
  assert.equal(result.context.creativeMotionGuideEnabled,true,'Fixture product flag must survive normalization');
  assert.equal(result.context.capabilities['creative-motion-guide-compose'],state==='ready');
  rendered.set(locale+':'+state,{result,form,...controls(form)});
}
for(const locale of locales){
  for(const state of ['ready','guarded']){
    const view=rendered.get(locale+':'+state);
    test(locale+':'+state+' preserves option values, defaults, controls and guards',()=>{
      assert.ok(view.form.includes('data-portal-route="/video-studio/motion-guide"'));
      assert.equal(view.selects.length,3);
      assert.deepEqual(view.selects.map(select=>select.name),['topic_kind','language','style']);
      assert.deepEqual(view.selects.map(select=>select.options.length),[9,3,7]);
      for(const select of view.selects){
        assert.deepEqual(select.options.map(option=>option.value),values[select.name]);
        assert.equal(select.disabled,state==='guarded');
      }
      assert.deepEqual(view.selects.map(select=>select.options.filter(option=>option.selected).map(option=>option.value)),[['product'],['vi'],['cinematic']]);
      assert.deepEqual(view.buttons,[
        {action:'creative-motion-guide-suggest',disabled:state==='guarded'},
        {action:'creative-motion-guide-refresh',disabled:true},
        {action:'creative-motion-guide-focus-topic',disabled:false},
        {action:'submit',disabled:true}
      ]);
      assert.equal((view.form.match(/name="custom_topic"/g)||[]).length,1);
      assert.equal((view.form.match(/type="hidden"/g)||[]).length,2);
      assert.ok(view.form.includes('name="suggestion_set" value="1"'));
      assert.ok(view.form.includes('name="selected_suggestion" value="0"'));
    });
    test(locale+':'+state+' localizes all 19 option labels without changing their values',()=>{
      const column=locales.indexOf(locale)+2;
      for(const select of view.selects){
        const expected=table.filter(row=>row[0].startsWith(prefixes[select.name])).map(row=>row[column]);
        assert.deepEqual(select.options.map(option=>option.label),expected,'Fixed labels for '+select.name+' must follow the interface locale');
      }
    });
  }
  test(locale+':custom preserves customer draft text and non-default scalar selections',()=>{
    const raw=clone(fixtures.motion);
    raw.creativeMotionGuideDraft={topic_kind:'custom',custom_topic:fixtures.sentinel,language:'en',suggestion_set:0,selected_suggestion:0,style:'ugc'};
    const before=JSON.stringify(raw),result=renderChild(locale,route,raw),form=formFor(result),view=controls(form);
    assert.equal(JSON.stringify(raw),before);
    assert.equal(result.context.creativeMotionGuideDraft.custom_topic,fixtures.sentinel);
    assert.equal(result.context.creativeMotionGuideDraft.language,'en');
    assert.equal(result.context.creativeMotionGuideDraft.style,'ugc');
    const textarea=form.match(/<textarea\b[^>]*name="custom_topic"[^>]*>([\s\S]*?)<\/textarea>/);
    assert.ok(textarea);
    assert.equal(decode(textarea[1]),fixtures.sentinel);
    assert.deepEqual(view.selects.map(select=>select.options.filter(option=>option.selected).map(option=>option.value)),[['custom'],['en'],['ugc']]);
    assert.equal(view.buttons.find(button=>button.action==='creative-motion-guide-suggest').disabled,true);
    assert.equal(view.buttons.find(button=>button.action==='submit').disabled,false);
    assert.ok(form.includes('name="suggestion_set" value="0"'));
    assert.ok(form.includes('name="selected_suggestion" value="0"'));
  });
}
