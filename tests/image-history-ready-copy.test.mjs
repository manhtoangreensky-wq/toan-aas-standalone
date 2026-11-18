import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pathToFileURL,fileURLToPath} from "node:url";
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-history-ready-copy-reviewed.json",import.meta.url);
const SHA="4c4a2c9cf418331701f52195c092a150627375f6281bcfab0a470f14df8a3820";
const {pageMetaSources,pageMetaRenderer}=await import(pathToFileURL(ROOT+"/tests/helpers/chat-page-meta-runtime.mjs").href);
const {resizeReadyContext}=await import(pathToFileURL(ROOT+"/tests/helpers/image-resize-guidance-runtime.mjs").href);
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const LOCALES=["vi","en","zh"],KEYS=["history.intro.kicker","history.intro.title","history.intro.body","history.metric.count","history.results.title","history.results.description","history.empty.title","history.empty.body"];
const COPY={
  vi:["Lịch sử ảnh","Ảnh đã xử lý của bạn","Xem lại các lần chỉnh ảnh và tải ảnh đã hoàn tất.","Ảnh ở trang này","Kết quả chỉnh ảnh","Chọn ảnh đã hoàn tất để tải xuống. Nếu chưa tải được, hãy làm mới danh sách.","Chưa có ảnh đã xử lý","Ảnh bạn chỉnh bằng các công cụ ảnh sẽ xuất hiện tại đây."],
  en:["Image history","Your processed images","Review your image edits and download completed images.","Images on this page","Image editing results","Choose a completed image to download. If you can't download it, refresh the list.","No processed images yet","Images you edit with the image tools will appear here."],
  zh:["图像记录","您已处理的图像","查看您的图像编辑记录并下载已完成的图像。","本页图像","图像编辑结果","选择已完成的图像进行下载。如果无法下载，请刷新列表。","暂无已处理的图像","您使用图像工具编辑的图像将显示在这里。"]
};
function inverse(source){
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const old=phases.every(([before,after])=>before===1&&after===0),next=phases.every(([before,after])=>before===0&&after===1);
  assert.ok(old||next,"Only eight exact all-OLD/all-NEW reviewed History ready rows are accepted");
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const sources=pageMetaSources(),prior={...sources,i18n:inverse(sources.i18n)};
assert.equal(prior.portal,sources.portal);assert.equal(prior.pages,sources.pages);
// Acceptance is the complete physical renderer, never a replayed proposal or projected input.
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/history";
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0"),CUSTOMER='CUSTOMER history.intro.title Facebook TikTok <img src=x onerror="literal">&';
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function records(locale){
  const oldKicker=JSON.parse(edits[0].old.trim().replace(/,$/,""))[LOCALES.indexOf(locale)+1],filename=oldKicker+" / "+COPY[locale][0]+" / "+CUSTOMER;
  const base={original_filename:filename,state:"completed",download_ready:true,source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,
    fit_mode:"crop",preset:"custom",created_at:"2026-11-18T01:02:03Z",updated_at:"2026-11-18T02:03:04Z",completed_at:"2026-11-18T03:04:05Z"};
  return[
    {...base,id:id(1),kind:"image_resize"},
    {...base,id:id(2),kind:"image_brand_overlay",download_ready:false,settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}},
    {...base,id:id(3),kind:"image_background_cleanup",state:"failed",settings:{profile:"white_studio"}},
    {...base,id:id(4),kind:"image_enhance",original_filename:COPY[locale][4],preset:"UNKNOWN "+CUSTOMER,settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}}
  ];
}
function context(locale,items,variant={}){
  const raw=resizeReadyContext();raw.profile={locale:"en",displayName:CUSTOMER};raw.title=COPY[locale][1];
  raw.capabilities["image-operation-view"]=variant.view!==false;raw.capabilities["image-operation-refresh"]=variant.refresh!==false;
  raw.imageHistoryReadState=variant.read||"ready";raw.imageHistoryOperations=items;raw.imageOperations=items.filter(row=>row.kind==="image_resize");
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{limit:50,offset:variant.later?50:0,returned:items.length,has_more:Boolean(variant.later&&items.length),next_offset:variant.later&&items.length?100:null,previous_offset:variant.later?0:null}};
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:raw.imageOperations.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageEnhanceEnabled=true;raw.imageEnhanceOperationsReadState="ready";raw.imageEnhanceOperations=items.filter(row=>row.kind==="image_enhance");
  raw.capabilities["image-operation-enhance"]=true;raw.capabilities["image-enhance-refresh"]=true;
  return raw;
}
function result(renderer,locale,items,variant={},route=ROUTE){
  const raw=freeze(context(locale,items,variant)),saved=JSON.stringify(raw),output=renderer(locale,route,raw);
  assert.equal(JSON.stringify(raw),saved,"Raw records/rights remain immutable");assert.equal(output.route,route);return output;
}
const one=(text,pattern,label)=>{const matches=[...text.matchAll(pattern)];assert.equal(matches.length,1,label);return matches[0];};
function slots(html,empty){
  const intro=one(html,/(<section class="portal-document-operation-intro">)([\s\S]*?)(<\/section>)/g,"one ready History intro");
  const sections=[...html.matchAll(/(<section class="portal-card portal-card-pad">)([\s\S]*?)(<\/section>)/g)].filter(match=>match[2].includes('data-portal-action="image-history-refresh"'));
  assert.equal(sections.length,1,"one History results section");const results=sections[0],found=[];
  const add=(part,pattern,label,expected=1)=>{
    const matches=[...part[2].matchAll(pattern)];assert.equal(matches.length,expected,label);const offset=part.index+part[1].length;
    for(const match of matches)found.push({label,start:offset+match.index+match[1].length,value:match[2]});
  };
  add(intro,/(<span class="portal-section-kicker">)([\s\S]*?)(<\/span>)/g,"intro kicker");
  add(intro,/(<h2>)([\s\S]*?)(<\/h2>)/g,"intro title");add(intro,/(<p>)([\s\S]*?)(<\/p>)/g,"intro body");
  add(intro,/(<dl><div><dt>[^<]*<\/dt><dd>)([^<]*)(<\/dd>)/g,"count label");
  add(results,/(<div class="portal-card-header"><div><h2 class="portal-card-title">)([\s\S]*?)(<\/h2>)/g,"results title");
  add(results,/(<div class="portal-card-header"><div><h2 class="portal-card-title">[\s\S]*?<\/h2><p class="portal-card-subtitle">)([\s\S]*?)(<\/p>)/g,"results description");
  add(results,/(<div class="portal-empty">[\s\S]*?<h3>)([\s\S]*?)(<\/h3>)/g,"empty title",empty?1:0);
  add(results,/(<div class="portal-empty">[\s\S]*?<h3>[\s\S]*?<\/h3><p>)([\s\S]*?)(<\/p>)/g,"empty body",empty?1:0);
  assert.equal(found.length,empty?8:6);return found;
}
function assertCopy(output,locale,empty){assert.deepEqual(slots(output.html,empty).map(row=>row.value),COPY[locale].slice(0,empty?8:6).map(escape));}
function projectFixedNodes(html,oldHtml,empty){
  const next=slots(html,empty),old=slots(oldHtml,empty);let result=html;
  for(const[index,node]of next.map((node,index)=>[index,node]).sort((a,b)=>b[1].start-a[1].start))result=result.slice(0,node.start)+old[index].value+result.slice(node.start+node.value.length);
  return result;
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
function card(html,operationId){return one(html,new RegExp('<article\\b[^>]*data-image-operation="'+operationId+'"[\\s\\S]*?<\\/article>',"g"),"one actual card "+operationId)[0];}
for(const locale of LOCALES){
  for(const empty of [true,false])test(`${locale}/${empty?"empty":"mixed full"}: actual ready History shows eight-or-six reviewed fixed text nodes`,()=>assertCopy(result(render,locale,empty?[]:records(locale)),locale,empty));
  test(`${locale}: ready HTML preserves records, counts, pagination, refresh rights, tool links and every byte outside own static nodes`,()=>{
    for(const items of [[],records(locale)])for(const variant of [{},{later:true},{refresh:false}]){
      const now=result(render,locale,items,variant),old=result(before,locale,items,variant);
      assert.equal(projectFixedNodes(now.html,old.html,items.length===0),old.html,"Only exact fixed-node text is projected, never customer/global/card content");
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));assert.deepEqual(controls(now.html),controls(old.html));
      assert.ok(now.html.includes("<dl><div><dt>"+items.length+"</dt><dd>"));assert.doesNotMatch(now.html,/<form\b/);
      const refresh=one(now.html,/<button\b[^>]*data-portal-action="image-history-refresh"[^>]*>/g,"one ready refresh")[0];
      assert.ok(refresh.includes('data-portal-route="/image/history"'));assert.equal(/\bdisabled\b/.test(refresh),variant.refresh===false);
      for(const href of ["/image/resize","/image/edit","/image/brand-overlay"])assert.ok(now.html.includes('href="'+href+'"'));
      assert.deepEqual([...now.html.matchAll(/data-image-operation="([^"]+)"/g)].map(match=>match[1]),items.map(row=>row.id));
      for(const row of items){
        const current=card(now.html,row.id);assert.equal(current,card(old.html,row.id));assert.ok(current.includes(escape(row.original_filename)));
        assert.equal(current.includes("/api/v1/image-operations/"+row.id+"/download"),row.state==="completed"&&row.download_ready===true);
        assert.ok(current.includes("640 × 480")&&current.includes("1280 × 720")&&current.includes("2026-11-18T03:04:05Z"));
        assert.equal(current.includes("<img src=x"),false);
      }
      const saved=JSON.stringify(now.context);freeze(now.context);assert.equal(now.qa.renderPage(now.page,now.context),now.html);assert.equal(JSON.stringify(now.context),saved);
    }
  });
  test(`${locale}: guard/loading/failed with both refresh rights and neighboring Resize/Edit are unchanged`,()=>{
    for(const variant of [{view:false},{read:"loading"},{read:"failed"},{read:"failed",refresh:false}]){
      const now=result(render,locale,records(locale),variant),old=result(before,locale,records(locale),variant);
      assert.equal(now.html,old.html);assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.doesNotMatch(now.html,/data-image-operation="/);
    }
    for(const route of ["/image/resize","/image/edit"]){
      const now=result(render,locale,records(locale),{},route),old=result(before,locale,records(locale),{},route);
      assert.equal(now.html,old.html);assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
    }
  });
}
test("same VM changes ready empty/full fixed History copy VI -> EN -> ZH -> VI without mutating context",()=>{
  for(const empty of [true,false]){
    const output=result(render,"vi",empty?[]:records("vi")),saved=JSON.stringify(output.context);freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assertCopy({...output,html:output.qa.renderPage(output.page,output.context)},locale,empty);assert.equal(JSON.stringify(output.context),saved);}
  }
});
test("canonical authority is exact eight count-one rows, key order, R1 and independent twenty-four translated values",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);
  assert.equal(authority.review.specId,"IMAGE-HISTORY-READY-COPY-20261118");assert.equal(authority.review.conversation,"5eee3247-8f69-48f6-8004-bfda7e287fac");
  assert.equal(proposal.specId,"IMAGE-HISTORY-READY-COPY-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,8);
  for(const[index,edit]of edits.entries()){
    assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);
    assert.deepEqual(JSON.parse(edit.new.trim().replace(/,$/,"")),[KEYS[index],...LOCALES.map(locale=>COPY[locale][index])]);
    const old=JSON.parse(edit.old.trim().replace(/,$/,""));assert.equal(old[0],KEYS[index]);assert.equal(old.length,4);
  }
});
test("finite eight-row inverse rejects partial/unknown/duplicate phases and preserves outside customer/key-like bytes",()=>{
  const old=edits.map(edit=>edit.old).join("\n"),next=edits.map(edit=>edit.new).join("\n"),outside="CUSTOMER history.intro.title Facebook TikTok <literal>";
  assert.equal(inverse(old),old);assert.equal(inverse(next),old);assert.equal(inverse(outside+"\n"+sources.i18n+"\n"+outside),outside+"\n"+prior.i18n+"\n"+outside);
  assert.throws(()=>inverse(old.replace(edits[0].old,edits[0].new)),/all-OLD\/all-NEW/);assert.throws(()=>inverse(next.replace(edits[0].new,"UNKNOWN")),/all-OLD\/all-NEW/);assert.throws(()=>inverse(old+"\n"+edits[0].old),/all-OLD\/all-NEW/);
});
