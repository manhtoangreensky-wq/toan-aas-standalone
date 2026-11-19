import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {createHash} from "node:crypto";
import {pathToFileURL,fileURLToPath} from "node:url";
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const pins=[
  ["image-history-technical-notes-reviewed","4d5c30122cef5ba9098751350ae44084d7a2e71473d7ed814cceb1c0cbef99ab","IMAGE-HISTORY-TECHNICAL-NOTES-20261119","83f531bf-39ef-4e4b-baf1-a76596166a52","R1",1],
  ["image-history-state-meta-reviewed","d2960de5d5e263271fd2b9eb765abe25ccdbe6f421a9ab05813c5df51b20982b","IMAGE-HISTORY-STATE-META-20261119","d43b069b-76b4-41e8-8e4c-f46bc0899e8d","R2",3]
];
const rawAuthorities=pins.map(([name])=>fs.readFileSync(new URL("./fixtures/"+name+".json",import.meta.url))),authorities=rawAuthorities.map(raw=>JSON.parse(raw)),edits=authorities.flatMap(value=>value.proposal.changes);
const count=(text,part)=>text.split(part).length-1,fail="Unreviewed History notes/state-meta",FILE="static/portal/portal.js";
// Expose the actual notes renderer through a test-local copy of the established QA loader only.
// Application sources are complete physical bundles; no candidate replay, helper file write or notes implementation.
let loader=fs.readFileSync(path.join(ROOT,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
function expose(old,next){assert.equal(count(loader,old),1,"Exact test-loader exposure");loader=loader.replace(old,()=>next);}
expose("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","\nconst root="+JSON.stringify(ROOT)+";");
expose("supportTicketHeroSection,resolvePage,safeText,withUiText:","supportTicketHeroSection,resolvePage,safeText,renderNotes,withUiText:");
const{pageMetaSources,pageMetaRenderer}=await import("data:text/javascript;base64,"+Buffer.from(loader).toString("base64"));
const{resizeReadyContext}=await import(pathToFileURL(path.join(ROOT,"tests/helpers/image-resize-guidance-runtime.mjs")).href);
function inverse(source){
  assert.equal(typeof source,"string",fail);assert.equal(edits.length,4,fail+" edit count");
  const phases=edits.map(edit=>{const old=count(source,edit.old),next=count(source,edit.new)-old*count(edit.old,edit.new);assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/modified/duplicate");return next;});
  assert.ok(phases.every(value=>value===0)||phases.every(value=>value===1),fail+" mixed four-edit set");
  const next=phases[0]===1,owner="  function renderImageOperationHistory(",boundary="  function renderImageBrandOverlay(page, context) {";
  assert.equal(count(source,owner),1,fail+" owner");assert.equal(count(source,boundary),1,fail+" boundary");
  const start=source.indexOf(owner),end=source.indexOf(boundary,start);assert.ok(end>start,fail+" owner order");
  assert.equal(source.indexOf("\n  function ",start+owner.length)+1,end,fail+" immediate next-function boundary");
  const notes=next?edits[0].new:edits[0].old,notesPoint=source.indexOf(notes);assert.ok(notesPoint>start&&notesPoint<end,fail+" notes owner");assert.equal(notesPoint+notes.length,end+boundary.length,fail+" exact notes suffix");
  let previous=start;for(const edit of edits.slice(1)){const text=next?edit.new:edit.old,point=source.indexOf(text);assert.ok(point>previous&&point+text.length<end,fail+" detached/reordered state");previous=point;}
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const sources=pageMetaSources(),prior={...sources,portal:inverse(sources.portal)},isNew=edits.every(edit=>count(sources.portal,edit.old)===0);
assert.equal(prior.i18n,sources.i18n);assert.equal(prior.pages,sources.pages);
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/history",HREFS=["/image/resize","/image/edit","/image/brand-overlay"];
const LOCALES=["vi","en","zh"],STATES=["guarded","loading","failed","empty","full"],id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0");
const CUSTOMER='CUSTOMER Trạng thái tích hợp Nguyên tắc an toàn Phiên đã xác thực Không lưu bộ nhớ đệm riêng tư portal-state-meta Facebook TikTok <img src=x onerror="literal">&';
const META={vi:["Lịch sử ảnh","Xem lại các lần chỉnh ảnh và tải ảnh đã hoàn tất."],en:["Image history","Review your image edits and download completed images."],zh:["图像记录","查看您的图像编辑记录并下载已完成的图像。"]};
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function records(){
  const base={original_filename:CUSTOMER,state:"completed",download_ready:true,source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,fit_mode:"crop",preset:"custom",created_at:"2026-11-19T01:02:03Z",updated_at:"2026-11-19T02:03:04Z",completed_at:"2026-11-19T03:04:05Z"};
  return[{...base,id:id(1),kind:"image_resize"},{...base,id:id(2),kind:"image_brand_overlay",download_ready:false,settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}},
    {...base,id:id(3),kind:"image_background_cleanup",state:"failed",settings:{profile:"white_studio"}},{...base,id:id(4),kind:"image_enhance",preset:"UNKNOWN "+CUSTOMER,settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}}];
}
function context(state,refresh=true,later=false){
  const raw=resizeReadyContext(),items=state==="empty"?[]:records();raw.profile={locale:"en",displayName:CUSTOMER};raw.title="SPOOFED TITLE";
  Object.assign(raw.capabilities,{"image-operation-view":state!=="guarded","image-operation-refresh":refresh,"image-operation-enhance":true,"image-enhance-refresh":true,"image-brand-overlay-view":true,"image-brand-overlay-run":true,"image-brand-overlay-refresh":true});
  raw.imageHistoryReadState=["loading","failed"].includes(state)?state:"ready";raw.imageHistoryOperations=items;raw.imageOperations=items.filter(row=>row.kind==="image_resize");
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{limit:50,offset:later?50:0,returned:items.length,has_more:later&&items.length>0,next_offset:later&&items.length?100:null,previous_offset:later?0:null}};
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:raw.imageOperations.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageEnhanceEnabled=true;raw.imageEnhanceOperationsReadState="ready";raw.imageEnhanceOperations=items.filter(row=>row.kind==="image_enhance");raw.imageBrandOverlayEnabled=true;raw.imageBrandOverlayOperationsReadState="ready";raw.imageBrandOverlayOperations=items.filter(row=>row.kind==="image_brand_overlay");return raw;
}
function result(renderer,locale,state,refresh=true,later=false,route=ROUTE){const raw=freeze(context(state,refresh,later)),saved=JSON.stringify(raw),output=renderer(locale,route,raw);assert.equal(JSON.stringify(raw),saved,"Raw rights/customer/listing input held");assert.equal(output.route,route);return output;}
const one=(html,pattern,label)=>{const matches=[...html.matchAll(pattern)];assert.equal(matches.length,1,label);return matches[0];};
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const stateMeta=html=>[...html.matchAll(/<div class="portal-state-meta">(?:<span>[^<]*<\/span>){3}<\/div>/g)];
const panels=html=>[...html.matchAll(/<div class="portal-panel-list">/g)];
const card=(html,key)=>one(html,new RegExp('<article\\b[^>]*data-image-operation="'+key+'"[\\s\\S]*?<\\/article>',"g"),"one actual card")[0];
function withoutOwnedRegion(old,state){
  if(["guarded","loading","failed"].includes(state)){
    const meta=stateMeta(old.html);assert.equal(meta.length,1,"Exactly one selected old state cluster");
    const owner=one(old.html,/<div class="portal-state" data-state="(?:guarded|processing)">[\s\S]*?<div><h2>[\s\S]*?<\/h2><p>[\s\S]*?<\/p>/g,"actual old state owner");
    assert.equal(meta[0].index,owner.index+owner[0].length,"Cluster is directly after actual state body");
    return old.html.slice(0,meta[0].index)+old.html.slice(meta[0].index+meta[0][0].length);
  }
  const notes=old.qa.renderNotes(old.page);assert.ok(notes.startsWith('<div class="portal-panel-list">'));assert.equal(count(old.html,notes),1,"Actual old notes output appears once");
  const owned="      "+notes+"\n",point=old.html.indexOf(owned);assert.ok(point>old.html.lastIndexOf('<div class="portal-form-footer"><p>'),"Notes follow compact tools");assert.equal(old.html.slice(point+owned.length),"    </article>","Only final actual notes block/line removed");
  return old.html.slice(0,point)+old.html.slice(point+owned.length);
}
function assertRemoved(output,state){
  assert.equal(stateMeta(output.html).length,0,"No nonactionable fixed state cluster");
  assert.equal(panels(output.html).length,0,"No technical notes panel or empty replacement");
  assert.doesNotMatch(output.html,/<div class="portal-panel-list">\s*<\/div>/);
  if(["empty","full"].includes(state)){
    const intro=one(output.html,/<section class="portal-document-operation-intro">([\s\S]*?)<\/section>/g,"ready intro"),cells=[...intro[1].matchAll(/<div><dt>[\s\S]*?<\/dt><dd>[\s\S]*?<\/dd><\/div>/g)];assert.equal(cells.length,1);
    const footer=one(output.html,/<div class="portal-form-footer"><p>[\s\S]*?<\/p><\/div>/g,"compact tool footer");assert.deepEqual([...footer[0].matchAll(/<a href="([^"]+)">/g)].map(match=>match[1]),HREFS);
  }
}
for(const locale of LOCALES){
  for(const state of STATES)test(`${locale}/${state}: physical History removes only nonactionable regions`,()=>assertRemoved(result(render,locale,state),state));
  test(`${locale}: full HTML outside exact state clusters/actual notes output is held, with rights/pagination/customer cards`,()=>{
    for(const state of STATES)for(const refresh of [true,false])for(const later of (["empty","full"].includes(state)?[false,true]:[false])){
      const now=result(render,locale,state,refresh,later),old=result(before,locale,state,refresh,later),expected=isNew?withoutOwnedRegion(old,state):old.html;
      assert.equal(now.html,expected,"Do not mask whole intro/card/customer/h2/p/global text");assert.deepEqual(controls(now.html),controls(old.html));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      assert.equal(now.qa.localizedPageTitle(now.page,now.context),META[locale][0]);assert.equal(now.qa.localizedPageDescription(now.page),META[locale][1]);assert.equal(now.title,META[locale][0]+" · TOAN AAS");assert.doesNotMatch(now.html,/<form\b/);
      const retry=[...now.html.matchAll(/<button\b[^>]*data-portal-action="image-history-refresh"[^>]*>/g)].map(match=>match[0]);
      if(["guarded","loading","failed"].includes(state)){
        assert.doesNotMatch(now.html,/data-image-operation="/,"Stale rows must stay suppressed");assert.equal(retry.length,state==="failed"&&refresh?1:0);if(retry.length){assert.ok(retry[0].includes('type="button"')&&retry[0].includes('data-portal-route="/image/history"'));assert.equal(/\bdisabled\b/.test(retry[0]),false);}
      }else{
        assert.equal(retry.length,1);assert.equal(/\bdisabled\b/.test(retry[0]),!refresh);const items=state==="empty"?[]:records();assert.deepEqual([...now.html.matchAll(/data-image-operation="([^"]+)"/g)].map(match=>match[1]),items.map(row=>row.id));
        for(const item of items){const current=card(now.html,item.id);assert.equal(current,card(old.html,item.id));assert.ok(current.includes(escape(item.original_filename)));assert.equal(current.includes("<img src=x"),false);assert.equal(current.includes("/api/v1/image-operations/"+item.id+"/download"),item.state==="completed"&&item.download_ready===true);for(const text of ["640 × 480","1280 × 720","2026-11-19T03:04:05Z"])assert.ok(current.includes(text));}
      }
      const saved=JSON.stringify(now.context);freeze(now.context);assert.equal(now.qa.renderPage(now.page,now.context),now.html);assert.equal(JSON.stringify(now.context),saved);
    }
  });
  test(`${locale}: neighboring Resize/Edit/BrandOverlay keep complete physical HTML and context`,()=>{
    for(const route of HREFS){const now=result(render,locale,"full",true,false,route),old=result(before,locale,"full",true,false,route);assert.equal(now.html,old.html);assert.equal(now.title,old.title);assert.equal(now.attributes,old.attributes);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));}
  });
}
test("same VM VI -> EN -> ZH -> VI keeps cleanup, translated copy, records and context",()=>{
  for(const state of STATES){const output=result(render,"vi",state),previous=result(before,"vi",state),saved=JSON.stringify(output.context);freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);previous.setLocale(locale);const current={...output,html:output.qa.renderPage(output.page,output.context)},old={...previous,html:previous.qa.renderPage(previous.page,previous.context)};assertRemoved(current,state);assert.equal(current.html,withoutOwnedRegion(old,state));assert.equal(output.qa.localizedPageTitle(output.page,output.context),META[locale][0]);assert.equal(JSON.stringify(output.context),saved);}
  }
});
test("exact immutable notes R1 + state-meta R2 authority, four edits/one owner, all outside source bytes held",()=>{
  for(const[index,[,sha,spec,conversation,revision,total]]of pins.entries()){const value=authorities[index];assert.equal(createHash("sha256").update(rawAuthorities[index]).digest("hex"),sha);assert.equal(value.review.schemaValid,true);assert.equal(value.review.proposalExact,true);assert.equal(value.review.specId,spec);assert.equal(value.review.conversation,conversation);assert.equal(value.proposal.specId,spec);assert.equal(value.proposal.revision,revision);assert.equal(value.proposal.changes.length,total);}
  for(const edit of edits){assert.equal(edit.file,FILE);assert.equal(edit.count,1);}assert.equal(edits.length,4);
  const outside="\r\n/* CUSTOMER Facebook TikTok portal-state-meta Trạng thái tích hợp */\r\n";assert.equal(inverse(outside+sources.portal+outside),outside+prior.portal+outside);assert.equal(inverse(prior.portal),prior.portal);
});
test("finite four-edit inverse rejects partial changed duplicate detached and reordered edits",()=>{
  const old=prior.portal;for(const edit of edits){assert.throws(()=>inverse(old.replace(edit.old,()=>edit.new)),new RegExp(fail));assert.throws(()=>inverse(old.replace(edit.old,"UNKNOWN")),new RegExp(fail));assert.throws(()=>inverse(old+"\n"+edit.old),new RegExp(fail));assert.throws(()=>inverse(old.replace(edit.old,"")+"\n"+edit.old),new RegExp(fail));}
  const[a,b]=edits.slice(1,3),marker="@@STATE_META_SWAP@@";assert.throws(()=>inverse(old.replace(a.old,marker).replace(b.old,()=>a.old).replace(marker,()=>b.old)),new RegExp(fail));
});
