import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {resizeReadyContext} from "./helpers/image-resize-guidance-runtime.mjs";

const AUTHORITY=new URL("./fixtures/image-resize-subtitle-cases-reviewed.json",import.meta.url);
const bytes=fs.readFileSync(AUTHORITY),authority=JSON.parse(bytes);
assert.equal(createHash("sha256").update(bytes).digest("hex"),"fd1e8f1b3d7377e957eeb5b3813e9eced040c31a71153381f2649e9f682798f6");
assert.equal(authority.review.specId,"RESIZE-SUBTITLE-READ-CONTRACT-20261118");
assert.equal(authority.review.conversation,"d79bbf98-6651-4c28-adb6-8711d3985573");
assert.equal(authority.review.status,"SOURCE_CASE_PLAN_ACCEPTED_NOT_RUNTIME");
assert.deepEqual(authority.proposal.cases.map(row=>row.id),Array.from({length:8},(_,i)=>"RSC-0"+(i+1)));
// Acceptance always executes the current full physical bundles. No proposal replay or source inverse.
const render=await pageMetaRenderer(pageMetaSources());
const LOCALES=["vi","en","zh"],ROUTES=["/image/resize","/image/history"];
const COPY={
  vi:{outer:"Đổi kích thước · ",custom:"Tùy chỉnh",fit:{crop:"Cắt giữa khung · lấp đầy, có thể cắt rìa",pad:"Đệm nền trắng · giữ trọn ảnh, không cắt",blur:"Nền mờ · giữ trọn ảnh ở giữa, nền mờ"}},
  en:{outer:"Image resize · ",custom:"Custom",fit:{crop:"Center crop · fill the frame, edges may be cropped",pad:"White padding · keep full image, no crop",blur:"Blurred background · keep image centered"}},
  zh:{outer:"调整尺寸 · ",custom:"自定义",fit:{crop:"居中裁剪 · 填满画面，可能裁掉边缘",pad:"白色填充 · 保留完整图像，不裁剪",blur:"模糊背景 · 图像居中保留"}}
};
const CUSTOMER='CUSTOMER media studio Facebook TikTok <img src=x onerror="literal">&';
const id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0");
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
function freeze(value){
  if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}
  return value;
}
function item(n,extra={}){
  return{id:id(n),kind:"image_resize",state:"completed",download_ready:true,original_filename:CUSTOMER+".png",
    source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,
    fit_mode:"crop",preset:"custom",created_at:"2026-11-18T01:02:03Z",updated_at:"2026-11-18T02:03:04Z",
    completed_at:"2026-11-18T03:04:05Z",...extra};
}
function context(items){
  const raw=resizeReadyContext();
  raw.profile={locale:"en",displayName:CUSTOMER};
  raw.imageOperations=items;raw.imageHistoryOperations=items;raw.imageHistoryReadState="ready";
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}};
  return raw;
}
function view(locale,route,items){
  const raw=freeze(context(items)),saved=JSON.stringify(raw),output=render(locale,route,raw);
  assert.equal(JSON.stringify(raw),saved,"Full raw customer/context data stays immutable");
  assert.equal(output.route,route);return output;
}
function card(html,operationId){
  const matches=[...html.matchAll(/<article\b[^>]*data-image-operation="([^"]+)"[\s\S]*?<\/article>/g)].filter(match=>match[1]===operationId);
  assert.equal(matches.length,1,"One actual operation card "+operationId);return matches[0][0];
}
function subtitleHtml(html){
  const matches=[...html.matchAll(/<p class="portal-card-subtitle">([\s\S]*?)<\/p>/g)];
  assert.equal(matches.length,1,"Exactly one fixed subtitle inside the selected card");return matches[0][1];
}
const subtitle=(html,operationId)=>decode(subtitleHtml(card(html,operationId)));
const expected=(locale,fit,preset)=>COPY[locale].outer+COPY[locale].fit[fit]+" · "+preset;
function assertPreset(items,token){
  for(const locale of LOCALES)for(const route of ROUTES){
    const output=view(locale,route,items);
    for(const row of items)assert.equal(subtitle(output.html,row.id),expected(locale,row.fit_mode,token===null?COPY[locale].custom:token));
  }
}
function maskCardSubtitle(html,operationId){
  const old=card(html,operationId),body=subtitleHtml(old);
  const next=old.replace('<p class="portal-card-subtitle">'+body+"</p>",'<p class="portal-card-subtitle">OWNED_RESIZE_SUBTITLE</p>');
  assert.notEqual(old,next);return html.replace(old,next);
}

test("RSC-01 custom token is localized in actual Resize and mixed-history consumers",()=>{
  assertPreset([item(1)],null);
});
test("RSC-02 empty preset defaults to the localized custom token without replacing outer/fit text",()=>{
  assertPreset([item(2,{preset:"",fit_mode:"pad"})],null);
});
test("RSC-03 omitted and undefined preset both default to the localized custom token",()=>{
  const absent=item(3,{fit_mode:"blur"});delete absent.preset;
  assertPreset([absent,item(4,{preset:undefined,fit_mode:"blur"})],null);
});
test("RSC-04 all nine ratio scalars remain exact tokens in both actual consumers",()=>{
  const ratios=["1:1","4:5","9:16","16:9","3:4","4:3","3:2","2:3","21:9"];
  const rows=ratios.map((preset,index)=>item(10+index,{preset}));
  for(const locale of LOCALES)for(const route of ROUTES){
    const output=view(locale,route,rows);
    for(const row of rows)assert.equal(subtitle(output.html,row.id),expected(locale,"crop",row.preset));
  }
});
test("RSC-05 unknown/customer scalars, proper names and markup-like text remain literal and escaped",()=>{
  const rows=[item(30,{preset:CUSTOMER,fit_mode:"pad"}),item(31,{preset:"CUSTOM",fit_mode:"pad"})];
  for(const locale of LOCALES)for(const route of ROUTES){
    const output=view(locale,route,rows);
    for(const row of rows){
      const html=card(output.html,row.id);
      assert.equal(subtitle(output.html,row.id),expected(locale,"pad",row.preset));
      assert.ok(html.includes('<h2 class="portal-card-title">'+escape(CUSTOMER+".png")+"</h2>"));
      assert.equal(html.includes("<img src=x"),false);
      assert.ok(html.includes("Facebook TikTok"));assert.ok(html.includes("&lt;img"));
    }
  }
});
test("RSC-06 same renderer instance updates custom, outer and fit text on VI -> EN -> ZH -> VI",()=>{
  for(const route of ROUTES){
    const row=item(40),output=view("vi",route,[row]),saved=JSON.stringify(output.context);
    freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){
      output.setLocale(locale);
      const html=output.qa.renderPage(output.page,output.context);
      assert.equal(subtitle(html,row.id),expected(locale,"crop",COPY[locale].custom));
      assert.equal(JSON.stringify(output.context),saved,"Locale rendering does not mutate normalized records");
    }
  }
});
test("RSC-07 mixed history preserves complete non-Resize cards and existing canonical subtitles",()=>{
  const rows=[
    item(50,{kind:"image_brand_overlay",settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}}),
    item(51,{kind:"image_background_cleanup",settings:{profile:"white_studio"}}),
    item(52,{kind:"image_enhance",preset:"product_clean",settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}})
  ];
  for(const locale of LOCALES){
    const mixed=view(locale,"/image/history",[item(49),...rows]),separate=view(locale,"/image/history",rows),messages=mixed.messages[locale];
    const key="imageOperationUi.result.brand.subtitle",brand=messages[key];
    assert.equal(typeof brand,"string");assert.equal(subtitle(mixed.html,rows[0].id),brand);
    for(const row of rows){
      assert.equal(card(mixed.html,row.id),card(separate.html,row.id),"Complete non-Resize card remains independent of Resize preset rendering");
      assert.ok(card(mixed.html,row.id).includes("/api/v1/image-operations/"+row.id+"/download"));
    }
    const background=messages["imageOperationUi.result.background.subtitle"];
    assert.equal(subtitle(mixed.html,rows[1].id),background.replace("{profile}","Trắng studio"));
    assert.ok(subtitle(mixed.html,rows[2].id).length>0);
  }
});
test("RSC-08 frozen data, controls, UUID/status/geometry/downloads and whole HTML outside one subtitle are unchanged",()=>{
  for(const locale of LOCALES)for(const route of ROUTES){
    const ratio=item(60,{preset:"16:9"}),unknown=item(60,{preset:CUSTOMER});
    const failed=item(61,{state:"failed",download_ready:false,preset:"4:5"});
    const guarded=item(62,{state:"qa_unknown_state",download_ready:true,preset:"4:3"});
    const now=view(locale,route,[unknown,failed,guarded]),comparison=view(locale,route,[ratio,failed,guarded]);
    assert.equal(maskCardSubtitle(now.html,id(60)),maskCardSubtitle(comparison.html,id(60)),
      "Only the exact selected card subtitle may depend on its preset; no global text masking");
    const done=card(now.html,id(60)),bad=card(now.html,id(61)),closed=card(now.html,id(62));
    assert.ok(done.includes('href="/api/v1/image-operations/'+id(60)+'/download"'));
    assert.ok(!bad.includes("/api/v1/image-operations/"+id(61)+"/download"));
    assert.ok(!closed.includes("/api/v1/image-operations/"+id(62)+"/download"));
    for(const value of ["640 × 480","1280 × 720","2026-11-18T03:04:05Z"])assert.ok(done.includes(value),value);
    const normalized=JSON.stringify(now.context);freeze(now.context);
    assert.equal(now.qa.renderPage(now.page,now.context),now.html);
    assert.equal(JSON.stringify(now.context),normalized);
    assert.equal(now.attributes,comparison.attributes);
    assert.equal(now.title,comparison.title);
  }
});
