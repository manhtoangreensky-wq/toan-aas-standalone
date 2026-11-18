import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pageMetaSources,pageMetaRenderer} from "./helpers/chat-page-meta-runtime.mjs";

const AUTHORITY=new URL("./fixtures/image-enhance-meta-reviewed.json",import.meta.url);
const SHA="10b19e6677caea6c2f70b213aab524580321dcd07e6dbf6a4c48b0d41199d83e";
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const digest=value=>createHash("sha256").update(value).digest("hex"),count=(text,part)=>text.split(part).length-1;
const COPY={
  vi:{title:"Chỉnh ảnh",description:"Chọn ảnh đã lưu, chỉnh màu và độ nét rồi tải bản PNG mới. Tệp gốc được giữ nguyên."},
  en:{title:"Edit images",description:"Choose a saved image, adjust color and sharpness, then download a new PNG. The original file stays unchanged."},
  zh:{title:"调整图像",description:"选择已保存的图像，调整色彩和锐度，然后下载新的 PNG 文件。原文件保持不变。"}
};
const files={"copyfast_pages.py":"pages","static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n"};
const sources=pageMetaSources(),prior={...sources};
// Invert owned ADDITIONS only: adjacent unrelated metadata shares the original anchors.
const additions=edits.map(edit=>{
  assert.equal(edit.count,1);assert.ok(Object.hasOwn(files,edit.file));
  const prefix=edit.new.startsWith(edit.old),suffix=edit.new.endsWith(edit.old);
  assert.ok(prefix!==suffix,"Each edit adds one finite chunk around its unchanged anchor");
  const chunk=prefix?edit.new.slice(edit.old.length):edit.new.slice(0,-edit.old.length);
  assert.ok(chunk.length>0);return{key:files[edit.file],chunk};
});
const present=additions.map(({key,chunk})=>count(sources[key],chunk));
assert.ok(present.every(value=>value===0)||present.every(value=>value===1),"Only all-OLD or all-NEW additions are accepted");
if(present.every(value=>value===1))for(const{key,chunk}of [...additions].reverse()){
  assert.equal(count(prior[key],chunk),1);const index=prior[key].indexOf(chunk);
  prior[key]=prior[key].slice(0,index)+prior[key].slice(index+chunk.length);
}
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior);
const ROUTE="/image/edit",STATES=["guarded","loading","failed","empty","ready"],ID="11111111-1111-4111-8111-111111111111",PIN="22222222-2222-4222-8222-222222222222";
const CUSTOMER='CUSTOMER Facebook TikTok <img src=x onerror="literal">&',UNKNOWN="UNKNOWN Facebook TikTok <literal>&";
const asset={id:ID,display_name:CUSTOMER,original_filename:CUSTOMER+".png",state:"active",extension:".png",content_type:"image/png",byte_size:1024};
function raw(state,locale){
  const allowed=state!=="guarded",read=["loading","failed"].includes(state)?state:"ready",items=state==="ready"?[asset]:[];
  return{profile:{locale:"en",displayName:CUSTOMER},title:"SPOOFED SERVER TITLE MUST NOT OVERRIDE REVIEWED METADATA",
    capabilities:{"image-operation-view":allowed,"image-operation-enhance":allowed,"image-enhance-refresh":allowed},
    assetVaultEnabled:true,imageOperationsEnabled:true,imageEnhanceEnabled:true,assetVaultReadState:read,
    imageEnhanceOperationsReadState:read,imageOperationAssetReferenceReadState:read,
    imageOperationAssetReferences:{items,pinned:state==="ready"?[{...asset,id:PIN,display_name:"PINNED "+CUSTOMER}]:[],
      listing:{filters:{q:CUSTOMER},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}}},
    imageEnhanceOperations:state==="ready"?[{id:ID,kind:"image_enhance",state:"completed",download_ready:true,
      original_filename:COPY[locale].title,preset:UNKNOWN,source_width:800,source_height:600,target_width:1600,target_height:1200,
      settings:{brightness:1.11,contrast:1.22,saturation:1.33,sharpness:1.44,tone:"warm",basic_upscale:true}}]:[]};
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const patterns=[/<h1 class="portal-title">([\s\S]*?)<\/h1>/g,/<p class="portal-description">([\s\S]*?)<\/p>/g];
const node=(html,pattern)=>{const matches=[...html.matchAll(pattern)];assert.equal(matches.length,1,"One actual fixed hero metadata node");return matches[0];};
function result(renderer,locale,state,route=ROUTE){
  const input=raw(state,locale),saved=JSON.stringify(input),output=renderer(locale,route,input);
  assert.equal(JSON.stringify(input),saved,"Raw customer/source inputs must remain literal");return output;
}
for(const locale of ["vi","en","zh"]){
  for(const state of STATES)test(`${locale}/${state}: actual Enhance header, hero, document title and description`,()=>{
    const r=result(render,locale,state),copy=COPY[locale];
    assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy.title);assert.equal(r.qa.localizedPageDescription(r.page),copy.description);
    assert.equal(r.title,copy.title+" · TOAN AAS");
    assert.equal(node(r.html,patterns[0])[1],r.qa.safeText(copy.title));assert.equal(node(r.html,patterns[1])[1],r.qa.safeText(copy.description));
    assert.ok(r.qa.renderHeader(r.page,r.context).includes('<span aria-current="page">'+r.qa.safeText(copy.title)+"</span>"));
  });
  test(`${locale}: five states preserve whole HTML outside two fixed hero nodes, controls, help, sources and context`,()=>{
    for(const state of STATES){
      const now=result(render,locale,state),old=result(before,locale,state);let projected=now.html;
      assert.deepEqual(controls(now.html),controls(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);
      for(const pattern of patterns){const next=node(projected,pattern),previous=node(old.html,pattern);projected=projected.slice(0,next.index)+previous[0]+projected.slice(next.index+next[0].length);}
      assert.equal(projected,old.html,"Only two exact fixed hero nodes may differ; customer copies are never globally replaced");
      assert.equal(now.html.includes("<img src=x"),false);
      if(["guarded","loading","failed"].includes(state)){
        assert.doesNotMatch(now.html,/<form\b/);assert.match(now.html,state==="loading"?/data-state="processing"/:/data-state="guarded"/);
      }else{
        assert.match(now.html,/data-portal-action="image-operation-enhance"/);assert.match(now.html,/data-portal-action="image-enhance-refresh"/);
        for(const name of ["source_asset_id","preset","brightness","contrast","saturation","sharpness","tone","basic_upscale"])assert.ok(now.html.includes('name="'+name+'"'));
        assert.match(now.html,/href="\/asset-vault"/);assert.equal(count(now.html,'<ol class="portal-project-steps">'),1);
        if(state==="ready"){
          assert.ok(now.html.includes(now.qa.safeText(CUSTOMER)));assert.ok(now.html.includes(now.qa.safeText(UNKNOWN)));
          assert.ok(projected.includes('<h2 class="portal-card-title">'+now.qa.safeText(COPY[locale].title)+"</h2>"),"Identical customer title stays literal");
          const select=now.html.match(/<select\b[^>]*name="source_asset_id"[^>]*>([\s\S]*?)<\/select>/);
          assert.deepEqual([...select[1].matchAll(/<option value="([^"]*)"/g)].map(match=>match[1]),["",PIN,ID]);
        }
      }
    }
  });
  test(`${locale}: neighboring physical routes, titles and headers keep preceding metadata`,()=>{
    for(const route of ["/documents/image-to-pdf","/documents/compress","/documents/split","/image/resize","/dashboard","/image/history"]){
      const now=result(render,locale,"ready",route),old=result(before,locale,"ready",route);
      assert.equal(now.html,old.html);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
    }
  });
}
test("canonical metadata authority is exactly five count-one additions, three files, R1 and two VI/EN/ZH keys",()=>{
  assert.equal(digest(authorityRaw),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);
  assert.equal(authority.review.specId,"IMAGE-ENHANCE-OUTER-META-20261118");assert.equal(authority.review.conversation,"92163194-4b60-4827-bdaa-436b0f8cfdf4");
  assert.equal(proposal.specId,"IMAGE-ENHANCE-OUTER-META-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,5);
  assert.deepEqual([...new Set(edits.map(edit=>edit.file))].sort(),Object.keys(files).sort());
  for(const key of ["imageEnhanceMetaUiTitle","imageEnhanceMetaUiDescription"])assert.equal(count(edits[4].new,key+":"),3);
  for(const copy of Object.values(COPY)){assert.ok(edits[4].new.includes(JSON.stringify(copy.title)));assert.ok(edits[4].new.includes(JSON.stringify(copy.description)));}
});
