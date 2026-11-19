// Current physical-bundle acceptance. No historical normalization, browser or product submission.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
const R=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="f8932643c1408d6565a0f1574f9bdd47ffac267b";
const hash=x=>createHash("sha256").update(x).digest("hex"),count=(s,p)=>s.split(p).length-1;
const authorityRaw=fs.readFileSync(path.join(R,"tests/fixtures/image-edit-customer-copy-reviewed.json"));
assert.equal(hash(authorityRaw),"7032192534419999f7528e3a6dbf08151b5db6ed96b3c49c7ecb300a6434007f");
const authority=JSON.parse(authorityRaw);assert.equal(authority.base,BASE);assert.equal(authority.workerApplicationTakeover,false);
assert.equal(authority.sourceAuthorities.length,3);
const specs=[{rows:authority.fieldsRows},{rows:authority.pageRows},{changes:authority.mobileCss}];
const changes=authority.canonicalChanges,rows=[...specs[0].rows,...specs[1].rows];
assert.equal(changes.length,22);assert.equal(rows.length,20);
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",css:"static/portal/portal.css",pages:"copyfast_pages.py"};
const current=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,fs.readFileSync(path.join(R,file),"utf8").replace(/\r\n/g,"\n")]));
const beforeSource=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,execFileSync("git",["show",BASE+":"+file],{cwd:R,encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n")]));
const restored={...current},phases=[];
for(const edit of changes){
 const key=Object.keys(files).find(key=>files[key]===edit.file);assert.ok(key);
 const next=count(restored[key],edit.new),old=count(restored[key],edit.old);
 assert.ok(next===1||(next===0&&old===1),"Each canonical slot exact OLD or NEW");
 if(next){assert.equal(old,count(edit.new,edit.old));restored[key]=restored[key].replace(edit.new,()=>edit.old);}
 phases.push(next);
}
assert.ok(phases.every(value=>value===0)||phases.every(value=>value===1),"No partial batch");
const digests=value=>Object.fromEntries(Object.entries(value).map(([key,text])=>[key,hash(text)]));
assert.deepEqual(digests(restored),digests(beforeSource),"Complete source outside22changes is BASE-exact");
let loader=fs.readFileSync(path.join(R,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
for(const[old,next]of [
 ["\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","\nconst root="+JSON.stringify(R)+";"],
 ["supportTicketHeroSection,resolvePage,safeText,withUiText:","supportTicketHeroSection,resolvePage,safeText,imageEnhanceFormFields,imageEnhancePresetLabel,renderImageEnhanceOperationCards,renderImageWorkspaceNavigation,withUiText:"]
]){assert.equal(count(loader,old),1);loader=loader.replace(old,()=>next);}
const{pageMetaRenderer}=await import("data:text/javascript;base64,"+Buffer.from(loader).toString("base64"));
const actual=await pageMetaRenderer(current),prior=await pageMetaRenderer(beforeSource);
const customer='CUSTOMER Preset Cinematic LANCZOS CSRF Facebook TikTok <img src=x onerror="literal">&';
const esc=value=>String(value).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const plain=value=>JSON.parse(JSON.stringify(value));
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){for(const item of Object.values(value))freeze(item);Object.freeze(value);}return value;}
function context({view=true,run=true,refresh=true,state="ready",size=1}={}){
 const image={id:"11111111-1111-4111-8111-111111111111",display_name:customer,original_filename:customer+".png",extension:".png",content_type:"image/png",state:"active",byte_size:1024};
 return freeze({path:"/image/edit",capabilities:{"image-operation-view":view,"image-operation-enhance":run,"image-enhance-refresh":refresh},assetVaultEnabled:true,imageEnhanceEnabled:true,
  assetVaultReadState:state,imageEnhanceOperationsReadState:state,imageOperationAssetReferenceReadState:state,
  imageOperationAssetReferences:{items:size?[image]:[],pinned:[],listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}}},
  imageEnhanceOperations:[],imageEnhanceOperationListing:{filters:{kind:"image_enhance"},pagination:{offset:0,returned:0,has_more:false,previous_offset:null}}});
}
function render(renderer,locale,settings,route="/image/edit"){
 const input=context(settings),saved=JSON.stringify(input);let result;
 try{result=renderer(locale,route,input);}catch(error){throw new Error((error.name+": "+error.message).slice(0,500));}
 assert.equal(JSON.stringify(input),saved);return result;
}
const tags=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(match=>match[0]).sort();
for(const locale of ["vi","en","zh"]){
 const index=["vi","en","zh"].indexOf(locale)+1;
 test(locale+": actual20catalogue rows use customer copy and keep keysets frozen",()=>{
  const result=render(actual,locale);
  for(const row of rows)assert.equal(result.messages[locale]["imageOperationUi."+row[0]],row[index],row[0]);
  for(const language of ["vi","en","zh"])assert.ok(Object.isFrozen(result.messages[language]));
  assert.deepEqual(Object.keys(result.messages.vi).sort(),Object.keys(result.messages.en).sort());
  assert.deepEqual(Object.keys(result.messages.vi).sort(),Object.keys(result.messages.zh).sort());
 });
 test(locale+": fixed field descriptions and cinematic result label change without field contracts",()=>{
  const now=render(actual,locale),old=render(prior,locale);
  for(const preset of ["custom","photo_clear_detail","product_clean","cinematic_warm","fresh_blue","food_vivid"]){
   const fields=plain(now.qa.imageEnhanceFormFields({preset})),earlier=plain(old.qa.imageEnhanceFormFields({preset}));assert.equal(fields.length,8);
   for(let i=0;i<fields.length;i++){
    for(const key of ["label","help","placeholder"]){delete fields[i][key];delete earlier[i][key];}
    for(const field of [fields[i],earlier[i]])if(field.options)field.options=field.options.map(option=>({value:option.value}));
    assert.deepEqual(fields[i],earlier[i],"Names/required/disabled/number bounds/options/codes retained");
   }
  }
  assert.equal(now.qa.imageEnhancePresetLabel("cinematic_warm"),specs[0].rows.find(row=>row[0]==="result.preset.cinematic_warm")[index]);
  assert.equal(now.qa.imageEnhancePresetLabel(customer),old.qa.imageEnhancePresetLabel(customer),"Unknown customer preset unchanged");
 });
 test(locale+": ready editor keeps useful form/history/navigation and no technical panels or blank replacement",()=>{
  const now=render(actual,locale),old=render(prior,locale);
  assert.doesNotMatch(now.html,/<aside\b|class="portal-document-operation-intro"|class="portal-panel-list"|portal-notice/);
  assert.ok(now.html.includes("portal-document-operation-layout--single"));assert.equal(count(now.html,'href="/asset-vault"'),1);
  const form=now.html.match(/<form\b[\s\S]*?<\/form>/)?.[0];assert.ok(form?.includes('href="/asset-vault"'));
  assert.deepEqual(tags(now.html),tags(old.html));assert.ok(now.html.includes(esc(customer)));assert.ok(!now.html.includes("<img src=x"));
  assert.equal(now.qa.renderImageWorkspaceNavigation(now.page),old.qa.renderImageWorkspaceNavigation(old.page));
  if(locale==="vi")assert.doesNotMatch(now.html.replaceAll(esc(customer),"CUSTOMER"),/\b(?:Preset|Cinematic|LANCZOS|UnsharpMask|CSRF|canonical)\b/);
 });
 test(locale+": protected guards actions data source thresholds and card factories stay intact",()=>{
  for(const view of [true,false,"true"])for(const run of [true,false,"true"])for(const refresh of [true,false])for(const state of ["ready","loading","failed"])for(const size of [0,1]){
   const settings={view,run,refresh,state,size},now=render(actual,locale,settings),old=render(prior,locale,settings);
   assert.deepEqual(tags(now.html),tags(old.html));assert.equal(now.title,old.title);assert.equal(now.attributes,old.attributes);
   assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(count(now.html,'class="portal-state-meta"'),0);
   assert.equal(now.qa.renderImageEnhanceOperationCards([],now.context),old.qa.renderImageEnhanceOperationCards([],old.context));
   if(view!==true||state!=="ready"){assert.ok(!now.html.includes("<form"));continue;}
   const submit=now.html.match(/<button\b[^>]*type="submit"[^>]*>/)[0];assert.equal(submit.includes(" disabled"),run!==true||size===0);
   const button=now.html.match(/<button\b[^>]*data-portal-action="image-enhance-refresh"[^>]*>/)[0];assert.equal(button.includes(" disabled"),!refresh);
  }
 });
}
test("full physical source outside22edits and unrelated route HTML remain protected",()=>{
 assert.deepEqual(digests(restored),digests(beforeSource));
 for(const locale of ["vi","en","zh"])for(const route of ["/documents/compress","/documents/image-to-pdf","/image/resize","/image/history"]){
  const now=render(actual,locale,{},route),old=render(prior,locale,{},route);
  assert.equal(now.html,old.html);assert.equal(now.title,old.title);assert.equal(now.attributes,old.attributes);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
 }
});
test("mobile navigation uses exact scoped max700px CSS while HTML destinations and desktop bytes stay held",()=>{
 const edit=specs[2].changes[0];assert.equal(count(current.css,edit.new),1);
 const addition=edit.new.slice(edit.old.length);assert.ok(addition.includes("@media (max-width: 700px)"));
 assert.ok(addition.includes("min-height: 44px"));assert.ok(addition.includes(".portal-image-enhance .portal-image-create-mode-card"));
 for(const locale of ["vi","en","zh"]){
  const now=render(actual,locale),old=render(prior,locale);
  assert.equal(now.qa.renderImageWorkspaceNavigation(now.page),old.qa.renderImageWorkspaceNavigation(old.page));
  for(const href of ["/image/create","/image-studio","/image/transform","/image/edit"])assert.equal(count(now.qa.renderImageWorkspaceNavigation(now.page),'href="'+href+'"'),1);
 }
});
