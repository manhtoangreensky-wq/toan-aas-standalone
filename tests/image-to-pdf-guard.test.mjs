import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
const authority=fs.readFileSync(new URL("./fixtures/image-to-pdf-guard-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(authority).digest("hex"),"57528c5cd1d37175cad203c9e40c30f816c4313f8589df776c3b572f0e7e21a3");
const reviewed=JSON.parse(authority),[edit]=reviewed.proposal.changes;
const count=(source,part)=>source.split(part).length-1,fail="Unreviewed Image-to-PDF guard";
function inverse(source){
  assert.equal(typeof source,"string",fail);
  const start=source.indexOf("  function renderImageToPdf(page, context) {");
  const end=source.indexOf("\n  function renderImageOperationHistory(",start);
  assert.ok(start>=0&&end>start,fail+" owner");
  const owner=source.slice(start,end),old=count(source,edit.old),next=count(source,edit.new);
  assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/changed/duplicate");
  const selected=next?edit.new:edit.old;
  assert.equal(count(owner,selected),1,fail+" detached");
  return next?source.replace(edit.new,()=>edit.old):source;
}
const physical=pageMetaSources(),prior={...physical,portal:inverse(physical.portal)};
const render=await pageMetaRenderer(physical),before=await pageMetaRenderer(prior);
const ROUTE="/documents/image-to-pdf",ID="11111111-1111-4111-8111-111111111111";
const CUSTOMER='CUSTOMER Facebook TikTok <img src=x onerror="literal">&';
const COPY={
  vi:["Chưa mở được công cụ PDF","Không thể tải công cụ lúc này. Vui lòng tải lại trang."],
  en:["PDF tool could not be opened","The tool could not be loaded right now. Please reload the page."],
  zh:["无法打开 PDF 工具","目前无法加载工具，请重新加载页面。"]
};
function raw({view=true,run=true,refresh=true,items=true}={}){
  const image={id:ID,display_name:CUSTOMER,original_filename:CUSTOMER+".png",state:"active",extension:".png",content_type:"image/png",byte_size:1024};
  return{capabilities:{"document-operation-view":view,"document-operation-image-to-pdf":run,"document-operation-refresh":refresh},
    documentOperationsEnabled:true,imageToPdfEnabled:true,documentOperationsReadState:"ready",documentAssetReferenceReadState:"ready",
    documentAssetReferences:{image:items?[image]:[],image_listing:{filters:{q:"",reference_kind:"image"},pagination:{offset:0,returned:items?1:0,has_more:false,next_offset:null,previous_offset:null}}},
    documentOperations:[]};
}
function result(renderer,locale,input){
  const saved=JSON.stringify(input),output=renderer(locale,ROUTE,input);
  assert.equal(JSON.stringify(input),saved,"Raw customer/source/capability inputs remain unchanged");
  return output;
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const stateContent=html=>{const match=html.match(/<div class="portal-state" data-state="guarded">([\s\S]*?)<\/section>/);assert.ok(match,"Actual guarded panel exists");return match[1];};
for(const locale of ["vi","en","zh"]){
  test(`${locale}: Image-to-PDF guarded panel uses localized title/body without redundant chips`,()=>{
    const sample=result(render,locale,raw({view:false})),panel=stateContent(sample.html);
    const [title,body]=COPY[locale];
    assert.ok(panel.includes("<h2>"+sample.qa.safeText(title)+"</h2>"));
    assert.ok(panel.includes("<p>"+sample.qa.safeText(body)+"</p>"));
    assert.equal(count(panel,"<h2>"),1);assert.equal(count(panel,"<p>"),1);
    assert.doesNotMatch(panel,/portal-state-meta|Signed session|Storage riêng|Document Operations|Asset Vault|fallback|provider/);
    assert.doesNotMatch(sample.html,/<form\b|data-portal-action="document-operation-image-to-pdf"/);
    assert.doesNotMatch(panel,/<div(?:\s[^>]*)?>\s*<\/div>/);
    assert.equal(sample.context.capabilities["document-operation-view"],false);
  });
  test(`${locale}: Image-to-PDF ready/disabled/empty forms retain whole HTML, controls and customer content`,()=>{
    for(const options of [{},{run:false},{items:false}]){
      const input=raw(options),now=result(render,locale,input),old=result(before,locale,input);
      assert.equal(now.html,old.html);assert.deepEqual(controls(now.html),controls(old.html));
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
      assert.match(now.html,/data-portal-action="document-operation-image-to-pdf" data-portal-route="\/documents\/image-to-pdf"/);
      assert.match(now.html,/data-portal-action="document-operation-refresh" data-portal-route="\/documents\/image-to-pdf"/);
      for(let position=1;position<=8;position++)assert.match(now.html,new RegExp('name="source_asset_id_'+position+'"'));
      assert.doesNotMatch(now.html,/<img src=x/);
      if(options.items!==false)assert.ok(now.html.includes(now.qa.safeText(CUSTOMER)));
    }
  });
}
test("Image-to-PDF view gate remains strict even when run/refresh capabilities are true or absent",()=>{
  for(const locale of ["vi","en","zh"])for(const omitted of [false,true]){
    const input=raw({view:false,run:true,refresh:true});
    if(omitted)delete input.capabilities["document-operation-view"];
    const now=result(render,locale,input),old=result(before,locale,input);
    assert.match(now.html,/data-state="guarded"/);assert.doesNotMatch(now.html,/<form\b/);
    assert.deepEqual(controls(now.html),controls(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
  }
});
test("One guard inverse rejects changed/partial/duplicate/detached return and preserves outside bytes",()=>{
  const current=physical.portal,prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* Facebook TikTok customer */";
  assert.equal(inverse(prefix+current+suffix),prefix+prior.portal+suffix);
  const active=count(current,edit.new)?edit.new:edit.old;
  assert.throws(()=>inverse(current+"\n"+active),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse(current.replace(active,active.replace("<h2>","<h2 data-unknown>"))),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse(current.replace(active,"")+"\n"+active),/Unreviewed Image-to-PDF guard/);
});
test("Reviewed authority permits exactly one guarded return with unchanged ready branch and locale keys",()=>{
  assert.equal(reviewed.review.proposalExact,true);assert.equal(reviewed.proposal.specId,"IMAGE-TO-PDF-GUARD-CUSTOMER-COPY-20261118");
  assert.equal(reviewed.proposal.changes.length,1);assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);
  assert.deepEqual(reviewed.proposal.deviations,[]);
  assert.ok(edit.new.includes('uiText("docPdfGuardUiTitle"'));assert.ok(edit.new.includes('uiText("docPdfGuardUiBody"'));
  assert.equal(count(edit.new,"portal-state-meta"),0);
});
