// Physical-bundle unit QA only. No native, server, provider or final-output claim.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {documentOcrCustomerHistoricalSource} from "./helpers/document-ocr-customer-copy-snapshot.mjs";
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const BASE="a589008be5d7be371789551ffc11e750db46270b",count=(s,p)=>s.split(p).length-1;
const hash=x=>createHash("sha256").update(x).digest("hex"),lf=x=>x.replace(/\r\n/g,"\n"),plain=x=>JSON.parse(JSON.stringify(x));
const authorityRaw=fs.readFileSync(new URL("./fixtures/document-convert-customer-copy-reviewed.json",import.meta.url));
assert.equal(hash(authorityRaw),"e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63","Immutable approved three-worker authority");
const authority=JSON.parse(authorityRaw);assert.equal(authority.base,BASE);assert.equal(authority.task,"DOCUMENT-CONVERT-CUSTOMER-COPY-20261119");
const specs={approved:{changes:authority.canonicalChanges,rows:authority.rows}};
const rows=Object.values(specs).flatMap(spec=>spec.rows),keys=rows.map(row=>row[0]);
const words=(key,locale)=>{const row=rows.find(value=>value[0]===key);assert.ok(row,key);return row[["vi","en","zh"].indexOf(locale)+1];};
let loader=fs.readFileSync(path.join(ROOT,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
for(const[old,next]of [
 ["\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","\nconst root="+JSON.stringify(ROOT)+";"],
 ["supportTicketHeroSection,resolvePage,safeText,withUiText:","supportTicketHeroSection,resolvePage,safeText,pdfToImagesFormFields,pdfToWordFormFields,renderDocumentOperationCards,withUiText:"]
]){assert.equal(count(loader,old),1,"Exact test-local exposure");loader=loader.replace(old,()=>next);}
const{pageMetaSources,pageMetaRenderer}=await import("data:text/javascript;base64,"+Buffer.from(loader).toString("base64"));
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const current=pageMetaSources(),baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,lf(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))]));
// These two renderers receive complete physical and Git BASE sources, never a historical projection.
const actual=await pageMetaRenderer(current),before=await pageMetaRenderer(baseline);
const routes=[
 {name:"images",route:"/documents/pdf-to-images",action:"document-operation-pdf-to-images",kind:"pdf_to_images",flag:"pdfToImagesEnabled",field:"pdfToImagesFormFields",prefix:"docConvertImagesUi",help:"docConvertFieldsUiImagesHelp"},
 {name:"word",route:"/documents/pdf-to-word",action:"document-operation-pdf-to-word",kind:"pdf_to_word_text",flag:"pdfToWordEnabled",field:"pdfToWordFormFields",prefix:"docConvertWordUi",help:"docConvertFieldsUiWordHelp"}
];
const customer='CUSTOMER media studio provider CSRF Facebook TikTok <img src=x onerror="literal">&';
const ids=["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"];
const esc=s=>String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
function context(route,settings={}){
 const{view,run,refresh,size,enabled,operations}={view:true,run:true,refresh:true,size:2,enabled:true,operations:[],...settings};
 const asset=id=>({id,display_name:customer,original_filename:customer+".pdf",state:"active",extension:".pdf",content_type:"application/pdf",byte_size:1024});
 const value={path:route,profile:{locale:"en"},capabilities:{"document-operation-view":view,"document-operation-refresh":refresh,
  "document-operation-pdf-to-images":run,"document-operation-pdf-to-word":run},
  assetVaultReadState:"ready",documentOperationsReadState:"ready",documentAssetReferenceReadState:"ready",
  documentOperations:operations,documentAssetReferences:{pdf:ids.slice(0,size).map(asset),image:[],
   pdf_listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}},
   image_listing:{filters:{q:""},pagination:{offset:0,returned:0,has_more:false,previous_offset:null}}}};
 if(enabled!==undefined){value.pdfToImagesEnabled=enabled;value.pdfToWordEnabled=enabled;}
 return freeze(value);
}
function render(renderer,locale,route,settings={}){
 const raw=context(route,settings),snapshot=JSON.stringify(raw);let result;
 try{result=renderer(locale,route,raw);}catch(error){throw new Error((error.name+": "+error.message).slice(0,500));}
 assert.equal(JSON.stringify(raw),snapshot,"Frozen source/customer records must not be translated or mutated");
 return result;
}
const openingTags=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)]
 .map(match=>match[0].replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="DECLARED_COPY"')).sort();
const contains=(html,value,label)=>assert.ok(html.includes(esc(value)),label||value);
const presentText=html=>html.replaceAll(esc(customer),"[CUSTOMER]").replace(/<[^>]*>/g," ");
const shared={
 vi:{label:"PDF từ kho tệp",empty:"Chọn PDF",open:"Mở kho tệp",refresh:"Làm mới"},
 en:{label:"PDF from file library",empty:"Choose PDF",open:"Open file library",refresh:"Refresh"},
 zh:{label:"文件库中的 PDF",empty:"选择 PDF",open:"打开文件库",refresh:"刷新"}
};
for(const locale of ["vi","en","zh"]){
 test(locale+": both source selectors translate their actual labels/help without changing field contracts",()=>{
  for(const cfg of routes){
   const now=render(actual,locale,cfg.route),old=render(before,locale,cfg.route);
   const fields=plain(now.qa[cfg.field]()),prior=plain(old.qa[cfg.field]());assert.equal(fields.length,1);assert.equal(prior.length,1);
   assert.equal(fields[0].label,shared[locale].label);assert.equal(fields[0].emptyLabel,shared[locale].empty);assert.equal(fields[0].help,words(cfg.help,locale));
   for(const key of ["label","emptyLabel","help"]){delete fields[0][key];delete prior[0][key];}
   assert.deepEqual(fields,prior);assert.deepEqual(fields[0],{name:"source_asset_id",control:"select",optionsFrom:"pdfVaultAssets",referencePicker:"document-pdf",required:true});
  }
 });
 test(locale+": both pages expose useful localized form/history only and keep the moved file-library action",()=>{
  for(const cfg of routes){
   const now=render(actual,locale,cfg.route),html=now.html,p=cfg.prefix;
   for(const suffix of ["Title","Description","FormTitle","History","HistoryBody","Ready","EmptyTitle","EmptyBody"])contains(html,words(p+suffix,locale),cfg.name+" "+suffix);
   assert.equal(now.title,words(p+"Title",locale)+" · TOAN AAS");assert.equal(now.qa.localizedPageTitle(now.page,now.context),words(p+"Title",locale));
   assert.equal(now.qa.localizedPageDescription(now.page),words(p+"Description",locale));
   assert.ok(now.qa.renderHeader(now.page,now.context).includes('<span aria-current="page">'+esc(words(p+"Title",locale))+"</span>"),cfg.name+" localized header breadcrumb");
   assert.equal(count(html,'data-portal-confirm="'+esc(words(p+"Confirm",locale))+'"'),1);
   const form=html.match(/<form\b[\s\S]*?<\/form>/)?.[0];assert.ok(form,cfg.name+" retained form");
   assert.equal(count(html,'href="/asset-vault"'),1);assert.equal(count(form,'href="/asset-vault"'),1);contains(form,shared[locale].open);
   assert.equal(count(form,"<select "),1);assert.ok(form.includes('data-portal-action="'+cfg.action+'"'));assert.ok(form.includes('data-portal-route="'+cfg.route+'"'));
   contains(html,shared[locale].refresh);contains(html,customer);assert.ok(!html.includes("<img src=x"));
   assert.doesNotMatch(html,/<aside\b|portal-document-operation-intro|portal-panel-list|portal-notice|portal-state-meta/);
   assert.ok(html.includes("portal-document-operation-layout--single"));assert.doesNotMatch(html,/<(?:section|aside)\b[^>]*>\s*<\/(?:section|aside)>/);
   assert.doesNotMatch(presentText(html),/\b(?:Asset Vault|Web-native|Signed|signed|CSRF|ownership|hash-copy|parser|server-side|fallback|provider|render|storage|capability|Browser|Document Operations)\b/i);
   const empty=render(actual,locale,cfg.route,{size:0});contains(empty.html,words(p+"EmptyBody",locale));assert.ok(empty.html.match(/<button\b[^>]*type="submit"[^>]*>/)[0].includes(" disabled"));
  }
 });
 test(locale+": explicit rights/source/refresh/flag cases preserve complete control attributes and strict booleans",()=>{
  const cases=[
   ["ready",{}],["empty",{size:0}],["run-false",{run:false}],["run-string",{run:"true"}],
   ["view-false",{view:false}],["view-string",{view:"true"}],["view-absent",{view:undefined}],
   ["refresh-false",{refresh:false}],["refresh-string",{refresh:"true"}],
   ["flag-absent",{run:false,enabled:undefined}],["flag-string",{run:false,enabled:"true"}],["flag-false",{run:false,enabled:false}]
  ];
  for(const cfg of routes)for(const[id,settings]of cases){
   const now=render(actual,locale,cfg.route,settings),old=render(before,locale,cfg.route,settings),label=cfg.name+"/"+id+"/"+locale;
   assert.deepEqual(openingTags(now.html),openingTags(old.html),label+" control attributes");
   assert.equal(JSON.stringify(now.context),JSON.stringify(old.context),label+" normalized context");
   if(Object.hasOwn(settings,"view")&&settings.view!==true){
    assert.ok(!now.html.includes("<form"),label);contains(now.html,words(cfg.prefix+"GuardTitle",locale));contains(now.html,words(cfg.prefix+"GuardBody",locale));assert.ok(now.html.includes('data-state="guarded"'));
    assert.doesNotMatch(now.html,/portal-state-meta/);continue;
   }
   const run=Object.hasOwn(settings,"run")?settings.run:true,size=Object.hasOwn(settings,"size")?settings.size:2,refresh=Object.hasOwn(settings,"refresh")?settings.refresh:true;
   const submit=now.html.match(/<button\b[^>]*type="submit"[^>]*>/)?.[0],update=now.html.match(/<button\b[^>]*data-portal-action="document-operation-refresh"[^>]*>/)?.[0];
   assert.ok(submit&&update,label);assert.equal(submit.includes(" disabled"),run!==true||size===0,label);assert.equal(update.includes(" disabled"),refresh!==true,label);
   if(run!==true){const flag=Object.hasOwn(settings,"enabled")?settings.enabled:true;contains(now.html,words(cfg.prefix+(flag===true?"NoAccess":"Unavailable"),locale),label);}
   assert.equal(now.context[cfg.flag],old.context[cfg.flag],label+" existing missing/string flag semantics");
  }
 });
 test(locale+": completed and guarded history keeps exact shared cards, output links and filtered operation ownership",()=>{
  for(const cfg of routes){
   const own={id:ids[0],kind:cfg.kind,state:"completed",download_ready:true,original_filename:customer,source_page_count:1,output_page_count:1,byte_size:1024,completed_at:"2026-11-01T00:00:00Z"};
   const guarded={id:ids[1],kind:cfg.kind,state:"guarded",download_ready:false,original_filename:customer+" guarded",source_page_count:1,output_page_count:0,byte_size:0};
   const unrelated={...own,id:"33333333-3333-4333-8333-333333333333",kind:"pdf_split",original_filename:"UNRELATED_OPERATION"};
   const now=render(actual,locale,cfg.route,{operations:[own,guarded,unrelated]}),old=render(before,locale,cfg.route,{operations:[own,guarded,unrelated]});
   const cards=now.qa.renderDocumentOperationCards([own,guarded],now.context);
   assert.equal(cards,old.qa.renderDocumentOperationCards([own,guarded],old.context));assert.ok(now.html.includes(cards));assert.ok(old.html.includes(cards));
   assert.equal(count(now.html,'data-document-operation="'+ids[0]+'"'),1);assert.equal(count(now.html,'data-document-operation="'+ids[1]+'"'),1);assert.ok(!now.html.includes("UNRELATED_OPERATION"));
   assert.equal(count(cards,'href="/api/v1/document-operations/'+ids[0]+'/download"'),1);assert.equal(count(cards,'href="/api/v1/document-operations/'+ids[1]+'/download"'),0);
   contains(cards,customer);assert.ok(!cards.includes("<img src=x"));assert.deepEqual(openingTags(now.html),openingTags(old.html));
  }
 });
}
test("whole physical sources differ only by declared finite fragments and exact new catalog values; baseline does not block RED registration",()=>{
 // Only this historical source-comparator copy is staged; actual renderer still uses current physical bundles.
 const phase=[],comparison=Object.fromEntries(Object.entries(current).map(([key,source])=>[key,documentOcrCustomerHistoricalSource(source,files[key])]));
 for(const[key,file]of [["portal",files.portal],["pages",files.pages]]){
  let expected=baseline[key];
  for(const change of Object.values(specs).flatMap(spec=>spec.changes).filter(change=>change.file===file)){assert.equal(count(expected,change.old),1);expected=expected.replace(change.old,()=>change.new);}
  if(comparison[key]===baseline[key])phase.push(0);else{assert.equal(comparison[key],expected,file+" outside bytes");phase.push(1);}
 }
 const found=[],remove=[];
 for(const match of comparison.i18n.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);\n/g)){
  const entries=Object.entries(JSON.parse(match[2])),owned=entries.filter(([key])=>key.startsWith("docConvert"));
  if(!owned.length)continue;assert.equal(owned.length,entries.length,"No foreign entries in a new finite catalog block");
  for(const[key,value]of entries){assert.ok(keys.includes(key),"No undeclared new catalog key");assert.equal(value,words(key,match[1]));found.push([match[1],key]);}
  remove.push(match[0]);
 }
 let restored=comparison.i18n;for(const block of remove){assert.equal(count(restored,block),1);restored=restored.replace(block,"");}
 assert.equal(restored,baseline.i18n,"All catalog bytes outside exact declared blocks remain BASE");
 if(found.length){assert.equal(found.length,84);assert.equal(new Set(found.map(row=>row.join(":"))).size,84);phase.push(1);}else phase.push(0);
 assert.equal(new Set(phase).size,1,"Whole batch, never mixed source phases");
});
test("seven protected routes render byte-identically from full physical bundles in every locale",()=>{
 for(const route of ["/documents/compress","/documents/image-to-pdf","/documents/split","/documents/merge","/image/edit","/image/history","/image/resize"])for(const locale of ["vi","en","zh"]){
  const now=render(actual,locale,route),old=render(before,locale,route);assert.equal(now.html,old.html,route+"/"+locale);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
 }
});
test("new locale entries initialize together before immutable dictionaries and equal keysets",()=>{
 const result=render(actual,"vi",routes[0].route);assert.equal(keys.length,28);assert.equal(new Set(keys).size,28);
 for(const locale of ["vi","en","zh"]){assert.equal(Object.isFrozen(result.messages[locale]),true);for(const row of rows)assert.equal(result.messages[locale][row[0]],words(row[0],locale));}
 assert.deepEqual(Object.keys(result.messages.vi).sort(),Object.keys(result.messages.en).sort());assert.deepEqual(Object.keys(result.messages.vi).sort(),Object.keys(result.messages.zh).sort());
});
test("Word help visibly retains selectable-text-only, scan and layout/image/table/font limitations in all locales",()=>{
 const expected={
  vi:["Chỉ chuyển phần chữ có thể bôi chọn","PDF là ảnh chụp không chuyển được","hình ảnh, bảng, phông chữ và cách dàn trang không được giữ nguyên"],
  en:["Convert selectable text only","Scanned PDFs cannot be converted","images, tables, fonts and page layout are not retained"],
  zh:["仅转换可选择的文字","无法转换扫描版 PDF","图像、表格、字体和页面布局不会保留"]
 };
 for(const locale of ["vi","en","zh"]){const now=render(actual,locale,routes[1].route);for(const piece of expected[locale])contains(now.html,piece,locale+" honest Word limit");}
});
