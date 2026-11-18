import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

const ROOT=fileURLToPath(new URL("../",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-history-state-copy-reviewed.json",import.meta.url);
const SHA="312fa54f7ef6bc186ec463bd54409474149907f6c6279e336d028990ae9e8e29";
const {pageMetaSources,pageMetaRenderer}=await import("./helpers/chat-page-meta-runtime.mjs");
const {resizeReadyContext}=await import("./helpers/image-resize-guidance-runtime.mjs");
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const COPY={
  vi:{guard:["Chưa thể mở lịch sử ảnh","Hãy kiểm tra quyền truy cập hoặc thử lại sau để xem lịch sử ảnh của bạn."],loading:["Đang tải lịch sử ảnh","Vui lòng chờ trong khi tải danh sách ảnh của bạn."],failed:["Chưa tải được lịch sử ảnh","Hãy thử lại để tải danh sách ảnh mới nhất."]},
  en:{guard:["Image history can't be opened yet","Check your access or try again later to view your image history."],loading:["Loading image history","Please wait while your image list loads."],failed:["Couldn't load image history","Try again to load your latest image list."]},
  zh:{guard:["暂时无法打开图像记录","请检查访问权限或稍后重试以查看您的图像记录。"],loading:["正在加载图像记录","正在加载您的图像列表，请稍候。"],failed:["未能加载图像记录","请重试以加载最新的图像列表。"]}
};
const LOCALES=["vi","en","zh"],KEYS=["history.guard.title","history.guard.body","history.loading.title","history.loading.body","history.failed.title","history.failed.body"];
function inverse(source){
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const old=phases.every(([before,after])=>before===1&&after===0),next=phases.every(([before,after])=>before===0&&after===1);
  assert.ok(old||next,"Only six exact all-OLD/all-NEW reviewed History state rows are accepted");
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const sources=pageMetaSources(),prior={...sources,i18n:inverse(sources.i18n)};
assert.equal(prior.portal,sources.portal);assert.equal(prior.pages,sources.pages);
// Current acceptance executes complete physical sources; only the prior side reverses six rows.
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/history";
const CASES=[
  {id:"guard-no-view-with-ready-stale-records",kind:"guard",view:false,read:"ready",refresh:true},
  {id:"loading-view-allowed",kind:"loading",view:true,read:"loading",refresh:true},
  {id:"failed-with-refresh",kind:"failed",view:true,read:"failed",refresh:true},
  {id:"failed-without-refresh",kind:"failed",view:true,read:"failed",refresh:false}
],READY={kind:"ready",view:true,read:"ready",refresh:true};
const CUSTOMER='CUSTOMER history.guard.title history.loading.body Facebook TikTok <img src=x onerror="literal">&';
const id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0");
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function records(locale){
  const base={state:"completed",download_ready:true,source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,
    fit_mode:"crop",preset:"custom",created_at:"2026-11-18T01:02:03Z",updated_at:"2026-11-18T02:03:04Z",completed_at:"2026-11-18T03:04:05Z"};
  return[
    {...base,id:id(1),kind:"image_resize",original_filename:CUSTOMER+".png"},
    {...base,id:id(2),kind:"image_brand_overlay",original_filename:COPY[locale].guard[0],settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}},
    {...base,id:id(3),kind:"image_background_cleanup",original_filename:COPY[locale].failed[1],settings:{profile:"white_studio"}},
    {...base,id:id(4),kind:"image_enhance",original_filename:COPY[locale].loading[0],preset:"UNKNOWN Facebook TikTok <literal>&",settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}}
  ];
}
function context(locale,variant,items){
  const raw=resizeReadyContext();raw.profile={locale:"en",displayName:CUSTOMER};raw.title=COPY[locale].guard[0];
  raw.capabilities["image-operation-view"]=variant.view;raw.capabilities["image-operation-refresh"]=variant.refresh;
  raw.imageHistoryReadState=variant.read;raw.imageHistoryOperations=items;raw.imageOperations=items.filter(row=>row.kind==="image_resize");
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:raw.imageOperations.length,has_more:false,next_offset:null,previous_offset:null}};
  return raw;
}
function result(renderer,locale,variant,items=records(locale),route=ROUTE){
  const raw=freeze(context(locale,variant,items)),saved=JSON.stringify(raw),output=renderer(locale,route,raw);
  assert.equal(JSON.stringify(raw),saved,"Unknown customer/raw DTO fields stay literal and immutable");assert.equal(output.route,route);return output;
}
function stateNode(html){
  const matches=[...html.matchAll(/(<div class="portal-state" data-state="(?:guarded|processing)">[\s\S]*?<div><h2>)([\s\S]*?)(<\/h2><p>)([\s\S]*?)(<\/p>)/g)];
  assert.equal(matches.length,1,"One selected actual History state h2/p pair");return matches[0];
}
function assertCopy(output,locale,variant){
  const match=stateNode(output.html);assert.deepEqual([decode(match[2]),decode(match[4])],COPY[locale][variant.kind]);
}
function projectStateNodes(html,oldHtml){
  const next=stateNode(html),old=stateNode(oldHtml),titleStart=next.index+next[1].length,bodyStart=titleStart+next[2].length+next[3].length;
  let projected=html.slice(0,bodyStart)+old[4]+html.slice(bodyStart+next[4].length);
  return projected.slice(0,titleStart)+old[2]+projected.slice(titleStart+next[2].length);
}
const retryTags=html=>[...html.matchAll(/<button\b[^>]*data-portal-action="image-history-refresh"[^>]*>/g)].map(match=>match[0]);
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const meta=html=>[...html.matchAll(/<div class="portal-state-meta">([\s\S]*?)<\/div>/g)].map(match=>match[0]);
for(const locale of LOCALES){
  for(const variant of CASES)test(`${locale}/${variant.id}: actual History state title and body use exact reviewed copy`,()=>assertCopy(result(render,locale,variant),locale,variant));
  test(`${locale}: four state branches preserve every HTML byte outside the exact h2/p, retry rights, stale-record suppression and context`,()=>{
    for(const variant of CASES){
      const now=result(render,locale,variant),old=result(before,locale,variant);
      assert.equal(projectStateNodes(now.html,old.html),old.html,"No global title/body/key/customer masking");
      assert.deepEqual(controls(now.html),controls(old.html));assert.deepEqual(meta(now.html),meta(old.html));assert.equal(meta(now.html).length,1);
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      assert.doesNotMatch(now.html,/<form\b/);assert.doesNotMatch(now.html,/data-image-operation="/);
      assert.match(now.html,new RegExp('data-state="'+(variant.kind==="loading"?"processing":"guarded")+'"'));
      const retry=retryTags(now.html),allowed=variant.kind==="failed"&&variant.refresh;assert.equal(retry.length,allowed?1:0);
      if(allowed){assert.ok(retry[0].includes('type="button"'));assert.ok(retry[0].includes('data-portal-route="/image/history"'));assert.equal(/\bdisabled\b/.test(retry[0]),false);}
    }
  });
  test(`${locale}: ready empty/full mixed History and neighboring Resize remain full physical byte-equal`,()=>{
    for(const items of [[],records(locale)]){
      const now=result(render,locale,READY,items),old=result(before,locale,READY,items);assert.equal(now.html,old.html);
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);
      if(items.length){
        assert.equal([...now.html.matchAll(/data-image-operation="/g)].length,4);
        for(const row of items){assert.ok(now.html.includes('data-image-operation="'+row.id+'"'));assert.ok(now.html.includes(escape(row.original_filename)));assert.ok(now.html.includes("/api/v1/image-operations/"+row.id+"/download"));}
        assert.ok(now.html.includes(escape(CUSTOMER)));assert.equal(now.html.includes("<img src=x"),false);
      }else assert.doesNotMatch(now.html,/data-image-operation="/);
    }
    const now=result(render,locale,READY,records(locale),"/image/resize"),old=result(before,locale,READY,records(locale),"/image/resize");
    assert.equal(now.html,old.html);assert.equal(now.title,old.title);assert.equal(now.attributes,old.attributes);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
  });
}
test("same VM switches each actual History state VI -> EN -> ZH -> VI without changing normalized context",()=>{
  for(const variant of CASES){
    const output=result(render,"vi",variant),saved=JSON.stringify(output.context);freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assertCopy({...output,html:output.qa.renderPage(output.page,output.context)},locale,variant);assert.equal(JSON.stringify(output.context),saved);}
  }
});
test("canonical authority is exact six count-one state-copy rows in one i18n file, R1 and independent VI/EN/ZH literals",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);
  assert.equal(authority.review.specId,"IMAGE-HISTORY-PLAIN-STATE-COPY-20261118");assert.equal(authority.review.conversation,"c48dbd20-b769-452f-9ecb-ed98578c853d");
  assert.equal(proposal.specId,"IMAGE-HISTORY-PLAIN-STATE-COPY-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,6);
  for(const[index,edit]of edits.entries()){
    assert.equal(edit.count,1);assert.equal(edit.file,"static/portal/portal-i18n.js");
    const kind=["guard","loading","failed"][Math.floor(index/2)],slot=index%2,next=JSON.parse(edit.new.trim().replace(/,$/,"")),old=JSON.parse(edit.old.trim().replace(/,$/,""));
    assert.deepEqual(next,[KEYS[index],...LOCALES.map(locale=>COPY[locale][kind][slot])]);assert.equal(old[0],KEYS[index]);assert.equal(old.length,4);
  }
});
test("finite six-row inverse rejects partial/unknown/duplicate phases and preserves all outside customer/key-like source bytes",()=>{
  const old=edits.map(edit=>edit.old).join("\n"),next=edits.map(edit=>edit.new).join("\n"),outside="CUSTOMER history.guard.title Facebook TikTok <literal>";
  assert.equal(inverse(old),old);assert.equal(inverse(next),old);assert.equal(inverse(outside+"\n"+sources.i18n+"\n"+outside),outside+"\n"+prior.i18n+"\n"+outside);
  assert.throws(()=>inverse(old.replace(edits[0].old,edits[0].new)),/all-OLD\/all-NEW/);assert.throws(()=>inverse(next.replace(edits[0].new,"UNKNOWN")),/all-OLD\/all-NEW/);
  assert.throws(()=>inverse(old+"\n"+edits[0].old),/all-OLD\/all-NEW/);
});
