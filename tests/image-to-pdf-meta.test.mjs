import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
const authorityRaw=fs.readFileSync(new URL("./fixtures/image-to-pdf-meta-reviewed.json",import.meta.url));
const digest=value=>createHash("sha256").update(value).digest("hex");
assert.equal(digest(authorityRaw),"6168254dabd2ba87f5364368ea3bf6383bb1a00cb3d746bb9250af913516c08f");
const authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
assert.equal(authority.review.proposalExact,true);assert.equal(edits.length,5);
const COPY={
  vi:{title:"Ảnh thành PDF",description:"Chọn ảnh và ghép thành một tệp PDF. Ảnh gốc được giữ nguyên."},
  en:{title:"Images to PDF",description:"Choose images and combine them into one PDF file. The original images stay unchanged."},
  zh:{title:"图像转 PDF",description:"选择图像并合成为一个 PDF 文件。原图像保持不变。"}
};
const files={"static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n","copyfast_pages.py":"pages"};
const sources=pageMetaSources(),prior={...sources},count=(text,part)=>text.split(part).length-1;
// Exactly five reviewed inverses in RAM only; no historical adapter stack, proposal replay or file write.
const present=edits.map(edit=>count(sources[files[edit.file]],edit.new));
assert.ok(present.every(value=>value===0)||present.every(value=>value===1),"Partial/duplicated metadata proposal is not an accepted phase");
if(present.every(value=>value===1))for(const edit of [...edits].reverse()){
  assert.equal(edit.count,1);const key=files[edit.file];assert.ok(key);
  assert.equal(count(prior[key],edit.new),1);prior[key]=prior[key].replace(edit.new,()=>edit.old);
}
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior);
const ROUTE="/documents/image-to-pdf",ID="11111111-1111-4111-8111-111111111111";
const CUSTOMER='CUSTOMER IMAGE Facebook TikTok <img src=x onerror="literal">&';
const asset={id:ID,display_name:CUSTOMER,original_filename:CUSTOMER+".png",state:"active",extension:".png",content_type:"image/png",byte_size:1024};
function raw(state){
  const allowed=state!=="guarded",items=state==="ready"?[asset]:[];
  return {profile:{locale:"en",displayName:CUSTOMER},title:"FIXED SERVER TITLE MUST NOT OVERRIDE LOCALE",
    capabilities:{"document-operation-view":allowed,"document-operation-image-to-pdf":allowed,"document-operation-refresh":allowed},
    documentOperationsEnabled:true,imageToPdfEnabled:true,documentOperationsReadState:["loading","failed"].includes(state)?state:"ready",
    documentAssetReferenceReadState:["loading","failed","guarded"].includes(state)?state:"ready",
    documentAssetReferences:{image:items,image_listing:{filters:{q:CUSTOMER,reference_kind:"image"},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}}},
    documentOperations:[]};
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const extract=(html,pattern)=>{const match=pattern.exec(html);assert.ok(match,"Actual metadata node missing");return match[1];};
function result(renderer,locale,state,route=ROUTE){
  const input=raw(state),saved=JSON.stringify(input),session=renderer(locale,route,input);
  assert.equal(JSON.stringify(input),saved,"Customer/source input must stay literal");
  return session;
}
for(const locale of ["vi","en","zh"]){
  for(const state of ["guarded","loading","failed","empty","ready"]){
    test(`${locale}/${state}: actual Images-to-PDF header/hero/title/description`,()=>{
      const r=result(render,locale,state),copy=COPY[locale],esc=value=>r.qa.safeText(value);
      assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy.title);
      assert.equal(r.qa.localizedPageDescription(r.page),copy.description);
      assert.equal(r.title,copy.title+" · TOAN AAS");
      assert.equal(extract(r.html,/<h1 class="portal-title">([\s\S]*?)<\/h1>/),esc(copy.title));
      assert.equal(extract(r.html,/<p class="portal-description">([\s\S]*?)<\/p>/),esc(copy.description));
      assert.ok(r.qa.renderHeader(r.page,r.context).includes('<span aria-current="page">'+esc(copy.title)+"</span>"));
    });
  }
  test(`${locale}: five actual state inputs preserve all controls/source/customer text`,()=>{
    for(const state of ["guarded","loading","failed","empty","ready"]){
      const now=result(render,locale,state),old=result(before,locale,state);
      assert.deepEqual(controls(now.html),controls(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
      let projected=now.html;
      for(const pattern of [/<h1 class="portal-title">[\s\S]*?<\/h1>/,/<p class="portal-description">[\s\S]*?<\/p>/]){
        const next=pattern.exec(projected),previous=pattern.exec(old.html);assert.ok(next&&previous);
        projected=projected.replace(next[0],()=>previous[0]);
      }
      assert.equal(projected,old.html,"Full renderer outside the exact two hero metadata nodes stays byte-identical");
      assert.equal(now.html.includes('<img src=x'),false);
      if(state==="guarded"){assert.match(now.html,/data-state="guarded"/);assert.doesNotMatch(now.html,/<form\b/);}
      else{
        assert.match(now.html,/data-portal-action="document-operation-image-to-pdf"/);
        for(let position=1;position<=8;position++)assert.match(now.html,new RegExp('name="source_asset_id_'+position+'"'));
        assert.match(now.html,/data-portal-action="document-operation-refresh"/);
        assert.match(now.html,/href="\/asset-vault"/);
        if(state==="ready")assert.ok(now.html.includes(now.qa.safeText(CUSTOMER)),"Owned source customer text must remain escaped and exact");
      }
    }
  });
  test(`${locale}: physical neighboring routes and headers remain unchanged`,()=>{
    for(const route of ["/documents","/documents/split","/documents/merge","/documents/compress","/image/edit","/image/resize","/dashboard"]){
      const now=result(render,locale,"ready",route),old=result(before,locale,"ready",route);
      assert.equal(now.html,old.html);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
    }
  });
}
test("reviewed metadata authority stays exactly five count-one edits in three allowed sources",()=>{
  assert.equal(proposal.specId,"IMAGE-TO-PDF-OUTER-META-20261118");assert.equal(proposal.revision,"R1");
  assert.ok(edits.every(edit=>edit.count===1&&Object.hasOwn(files,edit.file)));
  assert.deepEqual([...new Set(edits.map(edit=>edit.file))].sort(),Object.keys(files).sort());
});
