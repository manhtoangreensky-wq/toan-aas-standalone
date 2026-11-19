// Full actual bundle UI tests only; never an OCR execution or engine-readiness claim.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
Error.stackTraceLimit=0;
const R=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="8ba0d0452f86dcc3d72e5087351134902eb4e659";
const authorityRaw=fs.readFileSync(new URL("./fixtures/document-ocr-customer-copy-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(authorityRaw).digest("hex"),"2784e5ec2bf31f4921f4d39fd495175dbb9871f860947d1c9b363218a453839f");
const authority=JSON.parse(authorityRaw);
// Route contracts copied literally from the reviewed design; visible words come only from approved worker rows.
const design={base:authority.base,allRows:authority.rows,configs:[
 {name:"image",owner:"renderImageOcr",next:"renderPdfOcr",route:"/documents/ocr",className:"portal-image-ocr",prefix:"docOcrImageUi",formFactory:"imageOcrFormFields",kind:"image_ocr",flag:"imageOcrEnabled",action:"document-operation-ocr-image",sourceKind:"image"},
 {name:"pdf",owner:"renderPdfOcr",next:"renderPdfOcrToWord",route:"/documents/pdf-ocr",className:"portal-pdf-ocr",prefix:"docOcrPdfUi",formFactory:"pdfOcrFormFields",kind:"pdf_ocr",flag:"pdfOcrEnabled",action:"document-operation-ocr-pdf",sourceKind:"pdf"},
 {name:"word",owner:"renderPdfOcrToWord",next:"renderImageToPdf",route:"/documents/pdf-ocr-to-word",className:"portal-pdf-ocr-to-word",prefix:"docOcrWordUi",formFactory:"pdfOcrWordFormFields",kind:"pdf_ocr_word",flag:"pdfOcrWordEnabled",action:"document-operation-pdf-ocr-to-word",sourceKind:"pdf"}
]},words=(key,locale)=>design.allRows.find(row=>row[0]===key)[["vi","en","zh"].indexOf(locale)+1];
assert.equal(design.base,BASE);assert.equal(design.allRows.length,36);
let loader=fs.readFileSync(path.join(R,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
for(const[old,next]of [["\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","\nconst root="+JSON.stringify(R)+";"],
 ["supportTicketHeroSection,resolvePage,safeText,withUiText:","supportTicketHeroSection,resolvePage,safeText,imageOcrFormFields,pdfOcrFormFields,pdfOcrWordFormFields,renderDocumentOperationCards,withUiText:"]]){
 assert.equal(loader.split(old).length-1,1);loader=loader.replace(old,()=>next);
}
const{pageMetaSources,pageMetaRenderer}=await import("data:text/javascript;base64,"+Buffer.from(loader).toString("base64"));
const physical=pageMetaSources(),files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,execFileSync("git",["show",BASE+":"+file],{cwd:R,encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n")]));
const actual=await pageMetaRenderer(physical),before=await pageMetaRenderer(baseline);
const customer='CUSTOMER media studio provider CSRF Facebook TikTok <img src=x onerror="literal">&',id="11111111-1111-4111-8111-111111111111";
const esc=s=>String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
function raw(cfg,settings={}){
 const{view=true,run=true,refresh=true,enabled=true,size=2,operations=[]}=settings;
 const asset=(suffix,kind)=>({id:id.slice(0,-1)+suffix,display_name:customer,original_filename:customer+(kind==="image"?".png":".pdf"),state:"active",extension:kind==="image"?".png":".pdf",content_type:kind==="image"?"image/png":"application/pdf",byte_size:1024});
 return freeze({path:cfg.route,capabilities:{"document-operation-view":view,"document-operation-refresh":refresh,[cfg.action]:run},[cfg.flag]:enabled,
  assetVaultReadState:"ready",documentOperationsReadState:"ready",documentAssetReferenceReadState:"ready",documentOperations:operations,
  documentAssetReferences:{image:["1","2"].slice(0,size).map(s=>asset(s,"image")),pdf:["1","2"].slice(0,size).map(s=>asset(s,"pdf")),
   image_listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}},
   pdf_listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}}}});
}
function render(renderer,locale,cfg,settings={}){
 const value=raw(cfg,settings),snapshot=JSON.stringify(value),result=renderer(locale,cfg.route,value);
 assert.equal(JSON.stringify(value),snapshot,"Customer/input state must not be mutated");return result;
}
const tags=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(m=>m[0].replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="DECLARED_COPY"')).sort();
for(const locale of ["vi","en","zh"])for(const cfg of design.configs){
 const p=cfg.prefix,w=suffix=>words(p+suffix,locale);
 test(locale+"/"+cfg.name+": actual two fields translate labels/help/options and retain exact public codes",()=>{
  const now=render(actual,locale,cfg),old=render(before,locale,cfg),fields=JSON.parse(JSON.stringify(now.qa[cfg.formFactory]())),prior=JSON.parse(JSON.stringify(old.qa[cfg.formFactory]()));
  assert.equal(fields.length,2);assert.equal(fields[1].label,words("docOcrSharedUiLanguageLabel",locale));
  assert.deepEqual(fields[1].options,["auto","vi","en"].map((code,index)=>[code,words("docOcrSharedUiLanguage"+["Auto","Vi","En"][index],locale)]));
  assert.equal(fields[1].help,words("docOcrSharedUiLanguageHelp",locale));
  const help="docOcrSharedUi"+({image:"Image",pdf:"Pdf",word:"Word"}[cfg.name])+"SourceHelp";assert.equal(fields[0].help,words(help,locale));
  assert.equal(fields[0].label,cfg.name==="image"?words("docOcrSharedUiImageSourceLabel",locale):({vi:"PDF từ kho tệp",en:"PDF from file library",zh:"文件库中的 PDF"})[locale]);
  for(let index=0;index<2;index++){for(const key of ["label","emptyLabel","help"]){delete fields[index][key];delete prior[index][key];}if(index===1){fields[index].options=fields[index].options.map(row=>row[0]);prior[index].options=prior[index].options.map(row=>row[0]);}assert.deepEqual(fields[index],prior[index]);}
  assert.deepEqual(fields.map(field=>[field.name,field.control,field.required]),[["source_asset_id","select",true],["language","select",true]]);
 });
 test(locale+"/"+cfg.name+": page/header/confirm/history are plain and localized without redundant panels or blank replacements",()=>{
  const now=render(actual,locale,cfg),html=now.html;
  assert.equal(now.title,w("Title")+" · TOAN AAS");assert.equal(now.qa.localizedPageDescription(now.page),w("Description"));
  for(const key of ["Title","Description","FormTitle","HistoryTitle","EmptyTitle","EmptyBody"])assert.ok(html.includes(esc(w(key))),key);
  assert.ok(now.qa.renderHeader(now.page,now.context).includes('<span aria-current="page">'+esc(w("Title"))+"</span>"));
  assert.ok(html.includes('data-portal-confirm="'+esc(w("Confirm"))+'"'));
  assert.doesNotMatch(html,/<aside\b|portal-document-operation-intro|portal-notice|portal-panel-list|portal-state-meta/);
  assert.ok(html.includes("portal-document-operation-layout--single"));assert.doesNotMatch(html,/<(?:section|aside)\b[^>]*>\s*<\/(?:section|aside)>/);
  const form=html.match(/<form\b[\s\S]*?<\/form>/)?.[0];assert.ok(form);assert.equal((form.match(/<select /g)||[]).length,2);
  assert.equal((html.match(/href="\/asset-vault"/g)||[]).length,1);assert.ok(form.includes('href="/asset-vault"'));
  const formHeader=html.slice(html.indexOf('portal-document-operation-form'),html.indexOf("<form"));assert.ok(!formHeader.includes("portal-card-subtitle"),"No duplicate form-header description");
  const visible=html.replaceAll(esc(customer),"[CUSTOMER]").replace(/<[^>]*>/g," ");assert.doesNotMatch(visible,/\b(?:Asset Vault|Web-native|CSRF|ownership|hash-copy|parser|server-side|fallback|provider|renderer|Browser|Document Operations|OCR|scan|private|guarded)\b/i);
  assert.ok(html.includes(esc(customer)));assert.ok(!html.includes("<img src=x"));
  for(const settings of [{view:false},{enabled:false},{enabled:"true"}]){const guarded=render(actual,locale,cfg,settings);assert.ok(!guarded.html.includes("<form"));assert.ok(guarded.html.includes(esc(words("docOcrSharedUiGuardBody",locale))));}
  const empty=render(actual,locale,cfg,{size:0});assert.ok(empty.html.includes(esc(w("EmptyBody"))));
 });
 test(locale+"/"+cfg.name+": strict flags/rights, source thresholds, draft default and retained controls remain BASE-equivalent",()=>{
  for(const settings of [{},{size:0},{view:false},{view:"true"},{enabled:false},{enabled:"true"},{run:false},{run:"true"},{refresh:false},{refresh:"true"}]){
   const now=render(actual,locale,cfg,settings),old=render(before,locale,cfg,settings);assert.deepEqual(tags(now.html),tags(old.html));assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
   const allowed=(!Object.hasOwn(settings,"view")||settings.view===true)&&(!Object.hasOwn(settings,"enabled")||settings.enabled===true);
   if(!allowed){assert.ok(!now.html.includes("<form"));continue;}
   const submit=now.html.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0];assert.ok(submit);
   assert.equal(submit.includes(" disabled"),(Object.hasOwn(settings,"run")&&settings.run!==true)||settings.size===0);
   assert.ok(now.html.includes('<option value="auto" selected'));assert.ok(now.html.includes('data-portal-action="'+cfg.action+'"'));
   const refresh=now.html.match(/<button\b[^>]*data-portal-action="document-operation-refresh"[^>]*>/)[0];assert.equal(refresh.includes(" disabled"),Object.hasOwn(settings,"refresh")&&settings.refresh!==true);
  }
 });
}
test("all previously accepted PDF conversion/edit/history/resize routes remain whole-HTML/title/context exact in every locale",()=>{
 for(const route of ["/documents/pdf-to-images","/documents/pdf-to-word","/documents/compress","/documents/image-to-pdf","/documents/split","/documents/merge","/image/edit","/image/history","/image/resize"])for(const locale of ["vi","en","zh"]){
  const cfg={route,action:"document-operation-pdf-to-images",flag:"pdfToImagesEnabled"},a=render(actual,locale,cfg),b=render(before,locale,cfg);assert.equal(a.html,b.html);assert.equal(a.title,b.title);assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
 }
});
for(const cfg of design.configs)test(cfg.name+": completed/guarded history retains exact cards, downloads and operation-kind filtering in every locale",()=>{
 for(const locale of ["vi","en","zh"]){
  const completed={id,kind:cfg.kind,state:"completed",download_ready:true,original_filename:customer,source_page_count:1,output_page_count:1,byte_size:1024,language:"en"};
  const guarded={...completed,id:"22222222-2222-4222-8222-222222222222",state:"guarded",download_ready:false};
  const foreign={...completed,id:"33333333-3333-4333-8333-333333333333",kind:"pdf_split",original_filename:"UNRELATED_OPERATION"};
  const now=render(actual,locale,cfg,{operations:[completed,guarded,foreign]}),old=render(before,locale,cfg,{operations:[completed,guarded,foreign]});
  const cards=now.qa.renderDocumentOperationCards([completed,guarded],now.context);assert.equal(cards,old.qa.renderDocumentOperationCards([completed,guarded],old.context));
  assert.ok(now.html.includes(cards));assert.ok(old.html.includes(cards));assert.ok(!now.html.includes("UNRELATED_OPERATION"));assert.deepEqual(tags(now.html),tags(old.html));
  assert.equal((cards.match(new RegExp('href="/api/v1/document-operations/'+id+'/download"',"g"))||[]).length,1);
  assert.ok(!cards.includes('/22222222-2222-4222-8222-222222222222/download'));assert.ok(cards.includes(esc(customer)));assert.ok(!cards.includes("<img src=x"));
 }
});
test("render-only UI stays behind the throwing network guard and does not claim engine readiness or final OCR output",()=>{
 // The actual shared VM renderer throws on any fetch; no product action is submitted or OCR runtime imported.
 for(const cfg of design.configs)for(const settings of [{},{view:false}])assert.doesNotThrow(()=>render(actual,"vi",cfg,settings));
 assert.equal(authority.engineRuntimeReadiness,"NOT_TESTED");assert.equal(authority.finalOcrOutput,"NOT_TESTED");
});
