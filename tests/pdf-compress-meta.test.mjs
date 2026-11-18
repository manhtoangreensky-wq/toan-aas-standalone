import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
const authority=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-compress-meta-reviewed.json",import.meta.url),"utf8"));
const digest=value=>createHash("sha256").update(value).digest("hex");
const expectedRaw=Buffer.from(authority.expectedRaw,"utf8"),proposalRaw=Buffer.from(authority.proposalRaw,"utf8");
assert.equal(digest(expectedRaw),"b3d1bd271b4d2ae39a7873d9906c6aa20429da68eea4f5ddee624781d7632ab2");
assert.equal(digest(proposalRaw),"225227707e2b7179359e62614a33b956d4b0439f426f955577522cfedb33506b");
const edits=JSON.parse(expectedRaw),proposal=JSON.parse(proposalRaw);
assert.deepEqual(proposal.changes,edits);assert.equal(edits.length,5);
const COPY={
  vi:{title:"Nén PDF",description:"Giảm dung lượng PDF khi có thể. Tệp gốc được giữ nguyên."},
  en:{title:"Compress PDF",description:"Reduce a PDF's file size where possible. The original stays unchanged."},
  zh:{title:"压缩 PDF",description:"在可行时减小 PDF 文件大小。原文件将保持不变。"}
};
const files={"static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n","copyfast_pages.py":"pages"};
const sources=pageMetaSources(),prior={...sources},count=(text,part)=>text.split(part).length-1;
// Exactly five reviewed inverses in RAM only; no historical adapter stack, proposal replay or file write.
// New metadata may share an insertion anchor; match only the five owned additions.
const ownedAddition=edit=>edit.file.endsWith("portal-i18n.js")?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length);
const present=edits.map(edit=>count(sources[files[edit.file]],ownedAddition(edit)));
assert.ok(present.every(value=>value===0)||present.every(value=>value===1),"Partial/duplicated metadata proposal is not an accepted phase");
if(present.every(value=>value===1))for(const edit of [...edits].reverse()){
  assert.equal(edit.count,1);const key=files[edit.file];assert.ok(key);
  const addition=ownedAddition(edit);
  assert.equal(count(prior[key],addition),1);prior[key]=prior[key].replace(addition,"");
}
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior);
const ROUTE="/documents/compress",ID="11111111-1111-4111-8111-111111111111";
const CUSTOMER='CUSTOMER PDF Facebook TikTok <img src=x onerror="literal">&';
const asset={id:ID,display_name:CUSTOMER,original_filename:CUSTOMER+".pdf",state:"active",extension:".pdf",content_type:"application/pdf",byte_size:1024};
function raw(state){
  const allowed=state!=="guarded",items=state==="ready"?[asset]:[];
  return {profile:{locale:"en",displayName:CUSTOMER},title:"FIXED SERVER TITLE MUST NOT OVERRIDE LOCALE",
    capabilities:{"document-operation-view":allowed,"document-operation-pdf-optimize":allowed,"document-operation-refresh":allowed},
    documentOperationsEnabled:true,pdfOptimizeEnabled:true,documentOperationsReadState:["loading","failed"].includes(state)?state:"ready",
    documentAssetReferenceReadState:["loading","failed","guarded"].includes(state)?state:"ready",
    documentAssetReferences:{pdf:items,pdf_listing:{filters:{q:CUSTOMER,reference_kind:"pdf"},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}}},
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
    test(`${locale}/${state}: actual Compress PDF header/hero/title/description`,()=>{
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
        assert.match(now.html,/data-portal-action="document-operation-pdf-optimize"/);
        assert.match(now.html,/name="source_asset_id"/);assert.match(now.html,/data-portal-action="document-operation-refresh"/);
        assert.match(now.html,/href="\/asset-vault"/);
        if(state==="ready")assert.ok(now.html.includes(now.qa.safeText(CUSTOMER)),"Owned source customer text must remain escaped and exact");
      }
    }
  });
  test(`${locale}: physical neighboring routes and headers remain unchanged`,()=>{
    for(const route of ["/documents","/documents/split","/documents/merge","/image/resize","/dashboard"]){
      const now=result(render,locale,"ready",route),old=result(before,locale,"ready",route);
      assert.equal(now.html,old.html);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
    }
  });
}
test("reviewed metadata authority stays exactly five count-one edits in three allowed sources",()=>{
  assert.equal(proposal.specId,"PDF-COMPRESS-OUTER-META-20261117");assert.equal(proposal.revision,"R1");
  assert.ok(edits.every(edit=>edit.count===1&&Object.hasOwn(files,edit.file)));
  assert.deepEqual([...new Set(edits.map(edit=>edit.file))].sort(),Object.keys(files).sort());
});
