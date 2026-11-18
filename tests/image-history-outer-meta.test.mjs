import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {pathToFileURL,fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const {pageMetaSources,pageMetaRenderer}=await import(pathToFileURL(path.join(ROOT,"tests/helpers/chat-page-meta-runtime.mjs")));
const AUTHORITY=new URL("./fixtures/image-history-outer-meta-reviewed.json",import.meta.url);
const SHA="6ecd6c9c47a0c24c0f7d059e28034f112019e4bd54f066437a063db4b27eca54",SPEC="IMAGE-HISTORY-OUTER-META-20261119";
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const COPY={
  vi:{title:"Lịch sử ảnh",description:"Xem lại các lần chỉnh ảnh và tải ảnh đã hoàn tất."},
  en:{title:"Image history",description:"Review your image edits and download completed images."},
  zh:{title:"图像记录",description:"查看您的图像编辑记录并下载已完成的图像。"}
};
const files={"copyfast_pages.py":"pages","static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n"},sources=pageMetaSources(),prior={...sources};
// Prior is ONLY the inverse of the five reviewed finite ADDITIONS; never forward-project a candidate.
const additions=edits.map(edit=>{
  assert.equal(edit.count,1);assert.ok(Object.hasOwn(files,edit.file));const prefix=edit.new.startsWith(edit.old),suffix=edit.new.endsWith(edit.old);
  assert.ok(prefix!==suffix,"One finite addition around an unchanged prefix/suffix anchor");
  const chunk=prefix?edit.new.slice(edit.old.length):edit.new.slice(0,-edit.old.length);
  assert.ok(chunk.length);assert.equal(count(sources[files[edit.file]],edit.old),1,"Original anchor is held");return{key:files[edit.file],chunk,anchor:edit.old};
});
const present=additions.map(({key,chunk})=>count(sources[key],chunk));
assert.ok(present.every(n=>n===0)||present.every(n=>n===1),"All-OLD or all-NEW only, never partial/modified additions");
if(present.every(n=>n===1))for(const{key,chunk,anchor}of [...additions].reverse()){
  assert.equal(count(prior[key],chunk),1);const index=prior[key].indexOf(chunk);prior[key]=prior[key].slice(0,index)+prior[key].slice(index+chunk.length);assert.equal(count(prior[key],anchor),1);
}
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior),ROUTE="/image/history",STATES=["guarded","loading","failed","empty","full"];
const CUSTOMER='CUSTOMER Facebook TikTok <img src=x onerror="literal">&',UNKNOWN="UNKNOWN Facebook TikTok <literal>&",STAMP="2026-11-19T04:05:06Z";
const ids=[1,2,3,4].map(n=>`${n}${String(n).repeat(7)}-${String(n).repeat(4)}-4${String(n).repeat(3)}-8${String(n).repeat(3)}-${String(n).repeat(12)}`);
const oldTitles=Object.fromEntries(Object.keys(COPY).map(locale=>{const r=before(locale,ROUTE,{capabilities:{"image-operation-view":false}});return[locale,r.qa.localizedPageTitle(r.page,r.context)];}));
const asset={id:ids[0],display_name:CUSTOMER,original_filename:CUSTOMER+".png",state:"active",extension:".png",content_type:"image/png",byte_size:1024};
function raw(state,locale){
  const allowed=state!=="guarded",read=["loading","failed"].includes(state)?state:"ready",full=state==="full",names=[COPY[locale].title,oldTitles[locale],CUSTOMER,UNKNOWN];
  const items=full?names.map((name,index)=>({id:ids[index],source_asset_id:ids[0],kind:"image_resize",state:"failed",download_ready:false,original_filename:name,preset:index%2?UNKNOWN:"custom",fit_mode:"pad",source_width:640,source_height:480,target_width:1280,target_height:720,created_at:STAMP,updated_at:STAMP})): [];
  return{profile:{locale:"en",displayName:CUSTOMER},title:"SPOOFED SERVER TITLE MUST NOT OVERRIDE FIXED METADATA",capabilities:{"image-operation-view":allowed,"image-operation-refresh":allowed,"image-operation-resize":allowed,"image-operation-enhance":allowed,"image-enhance-refresh":allowed},
    assetVaultEnabled:true,imageOperationsEnabled:true,imageResizeEnabled:true,imageEnhanceEnabled:true,assetVaultReadState:read,imageOperationsReadState:read,imageEnhanceOperationsReadState:read,imageOperationAssetReferenceReadState:read,
    imageOperationAssetReferences:{items:full?[asset]:[],pinned:[],listing:{filters:{q:CUSTOMER},pagination:{offset:0,returned:full?1:0,has_more:false,next_offset:null,previous_offset:null}}},
    imageHistoryReadState:read,imageHistoryOperations:items,imageHistoryListing:{filters:{kind:""},pagination:{offset:0,limit:50,returned:items.length,has_more:full,next_offset:full?50:null,previous_offset:null}},imageOperations:[],imageEnhanceOperations:[]};
}
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function result(renderer,locale,state,route=ROUTE){const input=freeze(raw(state,locale)),saved=JSON.stringify(input),r=renderer(locale,route,input);assert.equal(JSON.stringify(input),saved,"Raw customer/source/rights data unchanged");return r;}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(row=>row[0]);
const patterns=[/<h1 class="portal-title">([\s\S]*?)<\/h1>/g,/<p class="portal-description">([\s\S]*?)<\/p>/g];
const node=(html,pattern)=>{const matches=[...html.matchAll(pattern)];assert.equal(matches.length,1,"One actual hero metadata node");return matches[0];};
for(const locale of Object.keys(COPY)){
  for(const state of STATES)test(`${locale}/${state}: physical History header/hero/document title/description`,()=>{
    const r=result(render,locale,state),copy=COPY[locale];assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy.title);assert.equal(r.qa.localizedPageDescription(r.page),copy.description);assert.equal(r.title,copy.title+" · TOAN AAS");
    assert.equal(node(r.html,patterns[0])[1],r.qa.safeText(copy.title));assert.equal(node(r.html,patterns[1])[1],r.qa.safeText(copy.description));assert.ok(r.qa.renderHeader(r.page,r.context).includes('<span aria-current="page">'+r.qa.safeText(copy.title)+"</span>"));
  });
  test(`${locale}: all five History states preserve entire HTML outside two fixed hero nodes`,()=>{
    for(const state of STATES){
      const now=result(render,locale,state),old=result(before,locale,state);let reverted=now.html;assert.deepEqual(controls(now.html),controls(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);
      for(const pattern of patterns){const next=node(reverted,pattern),previous=node(old.html,pattern);reverted=reverted.slice(0,next.index)+previous[0]+reverted.slice(next.index+next[0].length);}
      assert.equal(reverted,old.html,"No global replacement of customer or card text");assert.equal(now.html.includes("<img src=x"),false);assert.doesNotMatch(now.html,/<form\b/);
      if(state==="full"){assert.equal(count(now.html,'data-image-operation="'),4);for(const name of [COPY[locale].title,oldTitles[locale],CUSTOMER,UNKNOWN])assert.ok(reverted.includes('<h2 class="portal-card-title">'+now.qa.safeText(name)+"</h2>"));}
    }
  });
  test(`${locale}: neighboring Resize/Edit physical HTML, titles, headers and context unchanged`,()=>{
    for(const route of ["/image/resize","/image/edit"]){const now=result(render,locale,"full",route),old=result(before,locale,"full",route);assert.equal(now.html,old.html);assert.equal(now.title,old.title);assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));}
  });
}
for(const state of STATES)test(`${state}: same VM reads selected locale at each metadata call`,()=>{
  const r=result(render,"vi",state);
  for(const locale of ["en","zh","vi"]){r.setLocale(locale);const html=r.qa.renderPage(r.page,r.context),copy=COPY[locale];assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy.title);assert.equal(r.qa.localizedPageDescription(r.page),copy.description);assert.equal(r.qa.documentTitle(r.page,r.context),copy.title+" · TOAN AAS");assert.equal(node(html,patterns[0])[1],r.qa.safeText(copy.title));assert.equal(node(html,patterns[1])[1],r.qa.safeText(copy.description));assert.ok(r.qa.renderHeader(r.page,r.context).includes('<span aria-current="page">'+r.qa.safeText(copy.title)+"</span>"));}
});
test("metadata authority: exact five finite additions / three physical files / R1 / fixed VI EN ZH copy",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);assert.equal(authority.review.specId,SPEC);assert.equal(authority.review.conversation,"98527f67-e77f-47a1-95aa-521c06aa2c58");assert.equal(proposal.specId,SPEC);assert.equal(proposal.revision,"R1");assert.equal(edits.length,5);assert.deepEqual([...new Set(edits.map(row=>row.file))].sort(),Object.keys(files).sort());
  for(const key of ["imageHistoryMetaUiTitle","imageHistoryMetaUiDescription"])assert.equal(count(edits[4].new,key+":"),3);for(const copy of Object.values(COPY)){assert.ok(edits[4].new.includes(JSON.stringify(copy.title)));assert.ok(edits[4].new.includes(JSON.stringify(copy.description)));}
});
