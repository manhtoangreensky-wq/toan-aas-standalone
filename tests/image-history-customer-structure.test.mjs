import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pathToFileURL,fileURLToPath} from "node:url";
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-history-customer-structure-reviewed.json",import.meta.url);
const SHA="2bd1a16e4bb9ff78f3344ec8f2b010ff7f23644ffb63ccf9f5f6f44f66d64673";
const {pageMetaSources,pageMetaRenderer}=await import(pathToFileURL(ROOT+"/tests/helpers/chat-page-meta-runtime.mjs").href);
const {resizeReadyContext}=await import(pathToFileURL(ROOT+"/tests/helpers/image-resize-guidance-runtime.mjs").href);
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const LOCALES=["vi","en","zh"],HREFS=["/image/resize","/image/edit","/image/brand-overlay"];
const COPY={
  vi:{labels:["Tạo ảnh theo kích thước mới","Tạo bản sao đã chỉnh","Tạo bản sao thương hiệu"],lead:"Muốn tạo bản mới, mở đúng công cụ ảnh tương ứng.",metric:"Ngoài phạm vi",description:"Tác vụ Bot và đầu ra nhà cung cấp không được truy vấn",newMetric:"Ảnh ở trang này",newDescription:"Xem lại các lần chỉnh ảnh và tải ảnh đã hoàn tất."},
  en:{labels:["Create a resized image","Create an enhanced copy","Create a branded copy"],lead:"To create a new copy, open the corresponding image tool.",metric:"Out of scope",description:"Bot jobs and provider output are not queried",newMetric:"Images on this page",newDescription:"Review your image edits and download completed images."},
  zh:{labels:["创建调整尺寸后的图像","创建增强副本","创建品牌副本"],lead:"要创建新副本，请打开对应的图像工具。",metric:"不在范围内",description:"不会查询 Bot 任务和服务商输出",newMetric:"本页图像",newDescription:"查看您的图像编辑记录并下载已完成的图像。"}
};
function inverse(source){
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const old=phases.every(([before,after])=>before===1&&after===0),next=phases.every(([before,after])=>before===0&&after===1);
  assert.ok(old||next,"Only two exact all-OLD/all-NEW reviewed History template rows are accepted");
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const sources=pageMetaSources(),prior={...sources,portal:inverse(sources.portal)},isNew=edits.every(edit=>count(sources.portal,edit.new)===1);
assert.equal(prior.i18n,sources.i18n);assert.equal(prior.pages,sources.pages);
// Acceptance receives the full physical source; only the prior side reverses two templates.
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/history";
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
const CUSTOMER='CUSTOMER history.metric.outOfScope Facebook TikTok <img src=x onerror="literal">&',id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0");
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function records(locale){
  const copy=COPY[locale],base={original_filename:copy.metric+" / "+copy.description+" / "+copy.newMetric+" / "+copy.newDescription+" / "+CUSTOMER,
    state:"completed",download_ready:true,source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,fit_mode:"crop",preset:"custom",
    created_at:"2026-11-19T01:02:03Z",updated_at:"2026-11-19T02:03:04Z",completed_at:"2026-11-19T03:04:05Z"};
  return[
    {...base,id:id(1),kind:"image_resize"},
    {...base,id:id(2),kind:"image_brand_overlay",download_ready:false,settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}},
    {...base,id:id(3),kind:"image_background_cleanup",state:"failed",settings:{profile:"white_studio"}},
    {...base,id:id(4),kind:"image_enhance",preset:"UNKNOWN "+CUSTOMER,settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}}
  ];
}
function context(items,variant={}){
  const raw=resizeReadyContext();raw.profile={locale:"en",displayName:CUSTOMER};
  raw.capabilities["image-operation-view"]=variant.view!==false;raw.capabilities["image-operation-refresh"]=variant.refresh!==false;
  raw.imageHistoryReadState=variant.read||"ready";raw.imageHistoryOperations=items;raw.imageOperations=items.filter(row=>row.kind==="image_resize");
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{limit:50,offset:variant.later?50:0,returned:items.length,has_more:Boolean(variant.later&&items.length),next_offset:variant.later&&items.length?100:null,previous_offset:variant.later?0:null}};
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:raw.imageOperations.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageEnhanceEnabled=true;raw.imageEnhanceOperationsReadState="ready";raw.imageEnhanceOperations=items.filter(row=>row.kind==="image_enhance");
  raw.capabilities["image-operation-enhance"]=true;raw.capabilities["image-enhance-refresh"]=true;return raw;
}
function result(renderer,locale,items,variant={},route=ROUTE){
  const raw=freeze(context(items,variant)),saved=JSON.stringify(raw),output=renderer(locale,route,raw);
  assert.equal(JSON.stringify(raw),saved,"Raw customer/rights/listing DTO stays immutable");assert.equal(output.route,route);return output;
}
const one=(text,pattern,label)=>{const matches=[...text.matchAll(pattern)];assert.equal(matches.length,1,label);return matches[0];};
const intro=html=>one(html,/(<section class="portal-document-operation-intro">)([\s\S]*?)(<\/section>)/g,"one actual History intro");
const metrics=html=>{const part=intro(html),dl=one(part[2],/(<dl>)([\s\S]*?)(<\/dl>)/g,"one intro metric list");return{part,dl,cells:[...dl[2].matchAll(/<div><dt>[\s\S]*?<\/dt><dd>[\s\S]*?<\/dd><\/div>/g)].map(match=>match[0])};};
const boundaries=html=>[...html.matchAll(/<section class="portal-card portal-card-pad portal-operations-boundary">[\s\S]*?<\/section>/g)];
const footers=html=>[...html.matchAll(/<div class="portal-form-footer"><p>[\s\S]*?<\/p><\/div>/g)].filter(match=>HREFS.every(href=>match[0].includes('href="'+href+'"')));
const links=html=>[...html.matchAll(/<a href="([^"]+)">([^<]*)<\/a>/g)].filter(match=>HREFS.includes(match[1])).map(match=>({href:match[1],label:decode(match[2])}));
function assertCompact(output,locale,items){
  const measure=metrics(output.html);assert.equal(measure.cells.length,1,"Only the useful count metric remains");
  assert.ok(measure.cells[0].startsWith("<div><dt>"+items.length+"</dt>"));assert.equal(boundaries(output.html).length,0,"No technical boundary card");
  const footer=footers(output.html);assert.equal(footer.length,1,"Exactly one compact tool footer");
  assert.deepEqual(links(footer[0][0]),HREFS.map((href,index)=>({href,label:COPY[locale].labels[index]})));
  assert.equal(footer[0][0],'<div class="portal-form-footer"><p>'+escape(COPY[locale].lead)+" "+HREFS.map((href,index)=>'<a href="'+href+'">'+escape(COPY[locale].labels[index])+"</a>").join(", ")+".</p></div>");
}
function restoreOnlyRemovedRegions(html,oldHtml){
  const oldMetrics=metrics(oldHtml);assert.equal(oldMetrics.cells.length,2);const oldBoundary=boundaries(oldHtml);assert.equal(oldBoundary.length,1);
  if(!isNew){assert.equal(metrics(html).cells.length,2);assert.equal(boundaries(html).length,1);assert.equal(footers(html).length,0);return html;}
  const footer=footers(html);assert.equal(footer.length,1);assert.equal(boundaries(html).length,0);
  let restored=html.slice(0,footer[0].index)+oldBoundary[0][0]+html.slice(footer[0].index+footer[0][0].length);
  const now=metrics(restored);assert.equal(now.cells.length,1);assert.equal(now.cells[0],oldMetrics.cells[0],"Useful metric remains byte-exact");
  const point=now.part.index+now.part[1].length+now.dl.index+now.dl[1].length+now.dl[2].length;
  return restored.slice(0,point)+oldMetrics.cells[1]+restored.slice(point);
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const card=(html,operationId)=>one(html,new RegExp('<article\\b[^>]*data-image-operation="'+operationId+'"[\\s\\S]*?<\\/article>',"g"),"one card "+operationId)[0];
for(const locale of LOCALES){
  for(const empty of [true,false])test(`${locale}/${empty?"empty":"full"}: actual ready History keeps one metric and three compact translated tool links`,()=>{
    const items=empty?[]:records(locale);assertCompact(result(render,locale,items),locale,items);
  });
  test(`${locale}: restoration touches only removed internal metric/footer region, preserving all records and controls`,()=>{
    for(const items of [[],records(locale)])for(const variant of [{},{later:true},{refresh:false}]){
      const now=result(render,locale,items,variant),old=result(before,locale,items,variant);
      assert.equal(restoreOnlyRemovedRegions(now.html,old.html),old.html,"No whole intro/results/card/customer projection");
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));assert.deepEqual(controls(now.html),controls(old.html));
      const newTools=isNew?footers(now.html)[0][0]:boundaries(now.html)[0][0];assert.deepEqual(links(newTools),links(boundaries(old.html)[0][0]));
      const refresh=one(now.html,/<button\b[^>]*data-portal-action="image-history-refresh"[^>]*>/g,"one ready refresh")[0];assert.ok(refresh.includes('data-portal-route="/image/history"'));assert.equal(/\bdisabled\b/.test(refresh),variant.refresh===false);
      assert.deepEqual([...now.html.matchAll(/data-image-operation="([^"]+)"/g)].map(match=>match[1]),items.map(row=>row.id));assert.doesNotMatch(now.html,/<form\b/);
      for(const row of items){
        const current=card(now.html,row.id);assert.equal(current,card(old.html,row.id));assert.ok(current.includes(escape(row.original_filename)));assert.equal(current.includes("<img src=x"),false);
        assert.equal(current.includes("/api/v1/image-operations/"+row.id+"/download"),row.state==="completed"&&row.download_ready===true);
        for(const value of ["640 × 480","1280 × 720","2026-11-19T03:04:05Z"])assert.ok(current.includes(value));
      }
      const saved=JSON.stringify(now.context);freeze(now.context);assert.equal(now.qa.renderPage(now.page,now.context),now.html);assert.equal(JSON.stringify(now.context),saved);
    }
  });
  test(`${locale}: guard/loading/failed with refresh on/off and neighboring Resize/Edit stay byte-identical`,()=>{
    for(const variant of [{view:false},{read:"loading"},{read:"failed"},{read:"failed",refresh:false}]){
      const now=result(render,locale,records(locale),variant),old=result(before,locale,records(locale),variant);assert.equal(now.html,old.html);assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.doesNotMatch(now.html,/data-image-operation="/);
    }
    for(const route of ["/image/resize","/image/edit"]){
      const now=result(render,locale,records(locale),{},route),old=result(before,locale,records(locale),{},route);assert.equal(now.html,old.html);assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
    }
  });
}
test("same VM keeps one metric and localized compact links VI -> EN -> ZH -> VI without context mutation",()=>{
  for(const empty of [true,false]){
    const items=empty?[]:records("vi"),output=result(render,"vi",items),saved=JSON.stringify(output.context);freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assertCompact({...output,html:output.qa.renderPage(output.page,output.context)},locale,items);assert.equal(JSON.stringify(output.context),saved);}
  }
});
test("canonical authority is exact two count-one portal template substitutions from the accepted R1 conversation",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);assert.equal(authority.review.conversation,"de9c50e6-3cc8-4084-8225-a88c8d63ce01");
  assert.equal(authority.review.specId,"IMAGE-HISTORY-CUSTOMER-STRUCTURE-20261118");assert.equal(proposal.specId,"IMAGE-HISTORY-CUSTOMER-STRUCTURE-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,2);
  for(const edit of edits){assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);}
  assert.ok(edits[0].old.includes('t("metric.outOfScope"'));assert.equal(edits[0].new.includes('t("metric.outOfScope"'),false);
  assert.ok(edits[1].old.includes("portal-operations-boundary"));assert.ok(edits[1].new.startsWith('       <div class="portal-form-footer"><p>'));
});
test("finite two-template inverse rejects partial/unknown/duplicate phases and preserves outside literals",()=>{
  const old=edits.map(edit=>edit.old).join("\n"),next=edits.map(edit=>edit.new).join("\n"),outside="CUSTOMER Facebook TikTok history.metric.outOfScope <literal>";
  assert.equal(inverse(old),old);assert.equal(inverse(next),old);assert.equal(inverse(outside+"\n"+sources.portal+"\n"+outside),outside+"\n"+prior.portal+"\n"+outside);
  assert.throws(()=>inverse(old.replace(edits[0].old,edits[0].new)),/all-OLD\/all-NEW/);assert.throws(()=>inverse(next.replace(edits[0].new,"UNKNOWN")),/all-OLD\/all-NEW/);assert.throws(()=>inverse(old+"\n"+edits[0].old),/all-OLD\/all-NEW/);
});
