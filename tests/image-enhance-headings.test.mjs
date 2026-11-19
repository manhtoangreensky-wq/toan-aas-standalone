import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
import {imageEditCustomerHistoricalSource} from "./helpers/image-edit-customer-copy-snapshot.mjs";

// LEGACY_HISTORICAL_RENDER_COMPARATOR: the reviewed Edit batch intentionally removed these six heading blocks.
// Original assertions/hash/negative vectors remain; current Edit acceptance uses separate full physical sources.
const ROOT=fileURLToPath(new URL("../",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-enhance-headings-reviewed.json",import.meta.url);
const SHA="8d17d4110028c6a2cd00f50bf3852e3419db70346894caffae87cf1367bc8755";
const {pageMetaSources,pageMetaRenderer}=await import("./helpers/chat-page-meta-runtime.mjs");
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const KEYS=["enhance.intro.kicker","enhance.intro.title","enhance.boundary.title","enhance.step.order.title","enhance.step.upscale.title","enhance.step.delivery.title"];
const COPY={
  vi:["Hướng dẫn chỉnh ảnh","Chỉnh màu và độ nét","Trước khi lưu ảnh","Thứ tự điều chỉnh","Giới hạn phóng ảnh","Tải ảnh sau khi xử lý"],
  en:["Image editing guide","Adjust color and sharpness","Before saving","Adjustment order","Enlargement limits","Download after processing"],
  zh:["图像编辑指南","调整色彩和锐度","保存之前","调整顺序","放大限制","处理后下载图像"]
};
const OLD={
  vi:["Tiện ích xử lý ảnh trên Web","Làm ảnh sạch, rõ và nhất quán — không hứa hẹn AI","Giới hạn trung thực","Thứ tự có thể kiểm tra","Nâng kích thước cơ bản có trần","Phát tệp riêng tư"],
  en:["Web image utility","Clean and clarify images without promising AI","Honest limits","Verifiable order","Bounded basic upscaling","Private delivery"],
  zh:["Web 图像工具","清洁并增强图像，不承诺 AI","真实边界","可验证顺序","受限的基础放大","私有交付"]
};
function inverse(source){
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const allOld=phases.every(([old,next])=>old===1&&next===0),allNew=phases.every(([old,next])=>old===0&&next===1);
  assert.ok(allOld||allNew,"Only six exact all-OLD/all-NEW reviewed heading rows are accepted");
  let result=source;if(allNew)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const sources=Object.fromEntries(Object.entries(pageMetaSources()).map(([key,source])=>[key,imageEditCustomerHistoricalSource(source,files[key])])),prior={...sources,i18n:inverse(sources.i18n)};
assert.equal(prior.portal,sources.portal);assert.equal(prior.pages,sources.pages);
const styles=Object.fromEntries(["portal.css","portal-theme.css"].map(file=>[file,fs.readFileSync(ROOT+"/static/portal/"+file)]));
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/edit",STATES=["guarded","loading","failed","empty","ready"],LOCALES=["vi","en","zh"];
const ID="11111111-1111-4111-8111-111111111111",PIN="22222222-2222-4222-8222-222222222222";
const CUSTOMER='CUSTOMER Facebook TikTok <img src=x onerror="literal">&',UNKNOWN="UNKNOWN Facebook TikTok <literal>&";
const customer=locale=>COPY[locale][1]+" / "+OLD[locale][1]+" / "+CUSTOMER;
const asset={id:ID,display_name:CUSTOMER,original_filename:CUSTOMER+".png",state:"active",extension:".png",content_type:"image/png",byte_size:1024};
function raw(state,locale){
  const allowed=state!=="guarded",read=["loading","failed"].includes(state)?state:"ready",name=customer(locale),selected={...asset,display_name:name,original_filename:name+".png"},items=state==="ready"?[selected]:[];
  assert.ok(("PINNED "+name+".png").length<=180,"Actual reference name limit is respected");
  return{profile:{locale:"en",displayName:CUSTOMER},title:"RAW TITLE MUST NOT REPLACE REVIEWED METADATA",
    capabilities:{"image-operation-view":allowed,"image-operation-enhance":allowed,"image-enhance-refresh":allowed},assetVaultEnabled:true,imageOperationsEnabled:true,imageEnhanceEnabled:true,
    assetVaultReadState:read,imageEnhanceOperationsReadState:read,imageOperationAssetReferenceReadState:read,
    imageOperationAssetReferences:{items,pinned:state==="ready"?[{...selected,id:PIN,display_name:"PINNED "+name}]:[],
      listing:{filters:{q:name},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}}},
    imageEnhanceOperations:state==="ready"?[COPY[locale][1],OLD[locale][1]].map((title,index)=>({id:index?PIN:ID,kind:"image_enhance",state:"completed",download_ready:true,
      original_filename:title,preset:UNKNOWN,source_width:800,source_height:600,target_width:1600,target_height:1200,
      settings:{brightness:1.11,contrast:1.22,saturation:1.33,sharpness:1.44,tone:"warm",basic_upscale:true}})):[]};
}
function result(renderer,locale,state){
  const input=raw(state,locale),saved=JSON.stringify(input),output=renderer(locale,ROUTE,input);assert.equal(JSON.stringify(input),saved,"Raw input stays literal");return output;
}
const one=(text,pattern,label)=>{const matches=[...text.matchAll(pattern)];assert.equal(matches.length,1,label);return matches[0];};
function sections(html,required){
  const intro=[...html.matchAll(/<section class="portal-document-operation-intro">([\s\S]*?)<\/section>/g)];
  const boundary=[...html.matchAll(/<aside class="portal-card portal-card-pad portal-document-operation-boundary">([\s\S]*?)<\/aside>/g)];
  assert.equal(intro.length,required?1:0,"Actual intro availability");assert.equal(boundary.length,required?1:0,"Actual boundary availability");
  return required?{intro:intro[0],boundary:boundary[0]}:null;
}
function slots(html,required=true){
  const parts=sections(html,required);if(!parts)return[];
  const found=[],add=(part,pattern,label,expectedCount)=>{
    const matches=[...part[1].matchAll(pattern)];assert.equal(matches.length,expectedCount,label);
    const offset=part.index+part[0].indexOf(part[1]);
    for(const match of matches)found.push({label,start:offset+match.index+match[1].length,value:match[2]});
  };
  add(parts.intro,/(<span class="portal-section-kicker">)([\s\S]*?)(<\/span>)/g,"intro kicker",1);
  add(parts.intro,/(<h2>)([\s\S]*?)(<\/h2>)/g,"intro title",1);
  add(parts.boundary,/(<h2 class="portal-card-title">)([\s\S]*?)(<\/h2>)/g,"boundary title",1);
  add(parts.boundary,/(<li><strong>)([\s\S]*?)(<\/strong>)/g,"ordered step titles",3);
  assert.equal(found.length,6);return found;
}
function bodies(html){
  const parts=sections(html,true),form=one(html,/<section class="portal-card portal-card-pad portal-document-operation-form">([\s\S]*?)<\/section>/g,"one Enhance form");
  return[one(parts.intro[1],/(<p>)([\s\S]*?)(<\/p>)/g,"intro body")[2],
    one(form[1],/(<p class="portal-card-subtitle">)([\s\S]*?)(<\/p>)/g,"form description")[2],
    one(parts.boundary[1],/(<p class="portal-card-subtitle">)([\s\S]*?)(<\/p>)/g,"boundary description")[2],
    ...[...parts.boundary[1].matchAll(/<li><strong>[\s\S]*?<\/strong><span>([\s\S]*?)<\/span>/g)].map(match=>match[1])];
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
function assertNewHeadings(output,locale,state){
  const shown=["empty","ready"].includes(state),nodes=slots(output.html,shown);if(!shown)return;
  assert.deepEqual(nodes.map(row=>row.value),COPY[locale].map((text,index)=>output.qa.safeText(index<3?text:(index-2)+". "+text)));
}
for(const locale of LOCALES){
  for(const state of STATES)test(`${locale}/${state}: actual fixed Enhance headings follow state availability and reviewed copy`,()=>assertNewHeadings(result(render,locale,state),locale,state));
  test(`${locale}: five states preserve whole HTML outside six fixed nodes, six bodies, controls, context, metadata and customer literals`,()=>{
    for(const state of STATES){
      const now=result(render,locale,state),old=result(before,locale,state),shown=["empty","ready"].includes(state);let projected=now.html;
      const next=slots(now.html,shown),previous=slots(old.html,shown);
      for(let index=next.length-1;index>=0;index--)projected=projected.slice(0,next[index].start)+previous[index].value+projected.slice(next[index].start+next[index].value.length);
      assert.equal(projected,old.html,"Only six exact Enhance heading node contents may differ, never global/customer strings");
      assert.deepEqual(controls(now.html),controls(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);
      assert.equal(now.title,old.title);assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      if(shown){assert.equal(bodies(now.html).length,6);assert.deepEqual(bodies(now.html),bodies(old.html));}
      if(state==="ready"){
        assert.ok(now.html.includes(now.qa.safeText(customer(locale))));assert.ok(now.html.includes(now.qa.safeText(UNKNOWN)));
        for(const title of [COPY[locale][1],OLD[locale][1]])assert.ok(projected.includes('<h2 class="portal-card-title">'+now.qa.safeText(title)+"</h2>"),"Identical old/new customer titles remain literal");
        assert.equal(now.html.includes("<img src=x"),false);
      }
    }
    for(const[file,bytes]of Object.entries(styles))assert.deepEqual(fs.readFileSync(ROOT+"/static/portal/"+file),bytes,"Font/layout source is not changed during rendering");
  });
}
test("same VM rerenders ready headings VI -> EN -> ZH -> VI without context or fixed-node replacement tricks",()=>{
  const output=result(render,"vi","ready"),saved=JSON.stringify(output.context);
  for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assertNewHeadings({...output,html:output.qa.renderPage(output.page,output.context)},locale,"ready");assert.equal(JSON.stringify(output.context),saved);}
});
test("canonical authority is exact R1 six count-one row substitutions in one i18n file with eighteen reviewed values",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);
  assert.equal(authority.review.specId,"IMAGE-ENHANCE-PLAIN-HEADINGS-20261118");assert.equal(authority.review.conversation,"424e9071-a3d6-436a-98a8-d2594edb0d33");
  assert.equal(proposal.specId,"IMAGE-ENHANCE-PLAIN-HEADINGS-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,6);
  for(const[index,edit]of edits.entries()){
    assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);
    assert.deepEqual(JSON.parse(edit.new.trim().replace(/,$/,"")),[KEYS[index],...LOCALES.map(locale=>COPY[locale][index])]);
    assert.deepEqual(JSON.parse(edit.old.trim().replace(/,$/,"")),[KEYS[index],...LOCALES.map(locale=>OLD[locale][index])]);
  }
});
test("finite six-row inverse accepts only full phases, rejects partial/unknown/duplicate rows and retains outside bytes",()=>{
  const old=edits.map(edit=>edit.old).join("\n"),next=edits.map(edit=>edit.new).join("\n");
  assert.equal(inverse(old),old);assert.equal(inverse(next),old);
  assert.equal(inverse("CUSTOMER Facebook TikTok\n"+sources.i18n+"\nOUTSIDE"),"CUSTOMER Facebook TikTok\n"+prior.i18n+"\nOUTSIDE");
  assert.throws(()=>inverse(old.replace(edits[0].old,edits[0].new)),/all-OLD\/all-NEW/);
  assert.throws(()=>inverse(next.replace(edits[0].new,"UNKNOWN")),/all-OLD\/all-NEW/);
  assert.throws(()=>inverse(old+"\n"+edits[0].old),/all-OLD\/all-NEW/);
});
