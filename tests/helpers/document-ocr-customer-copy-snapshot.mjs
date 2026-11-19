import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {vaultCustomerHistoricalSource,vaultCustomerHistoricalSnapshot} from "./vault-customer-copy-snapshot.mjs";
// Newest finite historical leaf only; current renderer inputs must remain physical.
const raw=fs.readFileSync(new URL("../fixtures/document-ocr-customer-copy-reviewed.json",import.meta.url));
const fail="Unreviewed Document OCR customer copy",count=(source,part)=>source.split(part).length-1;
assert.equal(createHash("sha256").update(raw).digest("hex"),"2784e5ec2bf31f4921f4d39fd495175dbb9871f860947d1c9b363218a453839f",fail+" authority");
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const portal="static/portal/portal.js",i18n="static/portal/portal-i18n.js",pages="copyfast_pages.py";
assert.equal(fixture.task,"DOCUMENT-OCR-CUSTOMER-COPY-20261119");assert.equal(fixture.base,"8ba0d0452f86dcc3d72e5087351134902eb4e659");assert.equal(fixture.revision,"ROOT_REVIEWED_R1");
assert.equal(edits.length,19);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,36);assert.equal(new Set(keys).size,36);
assert.ok(keys.every(key=>/^docOcr(?:Shared|Image|Pdf|Word)Ui[A-Za-z]+$/.test(key)));assert.equal(fixture.engineRuntimeReadiness,"NOT_TESTED");assert.equal(fixture.finalOcrOutput,"NOT_TESTED");
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.revision,value.conversation,value.resultRawSha256]),[
 ["fields","R1","e848b31b-be36-4038-8801-e3bd569b6b29","87f4e7041cc8a92ffec0bcd13e193d03b4ccd694dcd8aac8d64e289d88ebdbc8"],
 ["image","R1","3b569dc8-863e-47ca-a578-c0665a76b3c9","220fe68db72cf3727f73e98d0bc9bd871e6486ed748a0e6b0e90cfd0b062ee43"],
 ["pdf","R1","569bac41-0255-4a3a-af0f-a46b54d013ae","a93d146a7b3bc65afcaeec608ac5190b0034c15a1b70821d4178f8a933ad37e3"],
 ["word","R1","c37404c0-ba40-47b9-8a8e-acede81796f5","eef2c0188026b68b944d080e70fd30468d7f272827c654fcff01025cf1205ebe"]]);
assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.applicationFailureCount===0&&value.applicationWrites===0&&value.verify==="NOT_RUN"));
const functions=edits.filter(edit=>edit.file===portal&&edit.old.startsWith("  function ")).map(edit=>{
 const name=edit.old.match(/^  function (\w+)\(/)?.[1];assert.ok(name);assert.ok(edit.new.startsWith("  function "+name+"("));return{...edit,name,marker:"  function "+name+"("};
});
const nextOwners={imageOcrFormFields:"pdfToImagesFormFields",pdfOcrFormFields:"pdfOcrWordFormFields",pdfOcrWordFormFields:"storyboardGridFormValues",renderImageOcr:"renderPdfOcr",renderPdfOcr:"renderPdfOcrToWord",renderPdfOcrToWord:"renderImageToPdf"};
assert.deepEqual(functions.map(edit=>edit.name),Object.keys(nextOwners));
const metadata=edits.filter(edit=>edit.file===portal&&!edit.old.startsWith("  function ")),shell=edits.filter(edit=>edit.file===pages),catalogue=edits.find(edit=>edit.file===i18n);
assert.equal(metadata.length,6);assert.equal(shell.length,6);assert.ok(catalogue);
for(const edit of [...metadata,...shell]){assert.ok(edit.new.endsWith(edit.old));assert.ok(edit.new.length>edit.old.length);}
assert.equal(catalogue.old,"  verifyEqualKeysets();");assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];
assert.deepEqual(blocks.map(match=>match[1]),["vi","en","zh"]);
for(const[locale,index]of [["vi",1],["en",2],["zh",3]])assert.deepEqual(Object.entries(JSON.parse(blocks.find(match=>match[1]===locale)[2])),rows.map(row=>[row[0],row[index]]));
const addition=edit=>edit.new.slice(0,-edit.old.length);
function ownerBounds(source,marker,endMarker){
 const start=source.indexOf(marker),end=source.indexOf(endMarker,start+marker.length);
 assert.equal(count(source,marker),1,fail+" owner count");assert.ok(start>=0&&end>start,fail+" owner bounds");return[start,end];
}
function exactAdded(source,group,bounds){
 let previous=-1;
 for(const edit of group){
  assert.equal(count(source,edit.new),1,fail+" changed/partial/detached metadata");assert.equal(count(source,addition(edit)),1,fail+" duplicate metadata");
  const point=source.indexOf(edit.new),[start,end]=bounds(edit);assert.ok(point>start&&point+edit.new.length<=end,fail+" metadata owner");assert.ok(point>previous,fail+" reordered metadata");previous=point;
 }
}
function catalogueDeclarations(source){
 return [...source.matchAll(/Object\.assign\(MESSAGES\.(?:vi|en|zh),\s*\{([\s\S]*?)\}\);/g)]
  .flatMap(match=>[...match[1].matchAll(/(?:^|,|\n)\s*["']?(docOcr[A-Za-z0-9_]*)["']?\s*:/g)].map(value=>value[1]));
}
export function documentOcrCustomerHistoricalSource(source,file){
 assert.equal(typeof source,"string",fail);
 source=vaultCustomerHistoricalSource(source,file);
 if(file===i18n){
  const found=catalogueDeclarations(source),next=count(source,catalogue.new);if(!found.length){assert.equal(next,0,fail+" absent catalog");return source;}
  assert.equal(next,1,fail+" partial/changed/duplicate catalog");assert.equal(found.length,108,fail+" partial/unknown declarations");
  for(const key of keys)assert.equal(found.filter(value=>value===key).length,3,fail+" key count");assert.ok(found.every(key=>keys.includes(key)),fail+" unknown prefixed key");
  const point=source.indexOf(catalogue.new),freeze="  deepFreeze(MESSAGES);";assert.equal(count(source,catalogue.old),1,fail+" keyset anchor");assert.equal(count(source,freeze),1,fail+" freeze anchor");
  assert.ok(point<source.indexOf(freeze),fail+" post-freeze catalog");assert.ok(source.slice(point+catalogue.new.length).startsWith("\n\n  function deepFreeze(value) {"),fail+" detached catalog");
  return source.replace(catalogue.new,()=>catalogue.old);
 }
 if(file===portal){
  if(!/\buiText\(["']docOcr[A-Za-z0-9_]*["']/.test(source))return source;
  assert.ok(functions.every(edit=>count(source,edit.old)===0&&count(source,edit.new)===1),fail+" partial/mixed/changed complete functions");let previous=-1;
  for(const edit of functions){
   assert.equal(count(source,edit.marker),1,fail+" function owner");const point=source.indexOf(edit.new),nextMarker="  function "+nextOwners[edit.name]+"(";
   assert.equal(point,source.indexOf(edit.marker),fail+" detached function");assert.ok(point>previous,fail+" reordered functions");previous=point;
   assert.equal(count(source,nextMarker),1,fail+" next owner");assert.ok(source.slice(point+edit.new.length).startsWith(nextMarker),fail+" immediate next owner");
  }
  const calls=source=>[...source.matchAll(/\buiText\(["'](docOcr[A-Za-z0-9_]*)["']/g)].map(match=>match[1]);
  assert.deepEqual(calls(source).sort(),[...functions,...metadata].flatMap(edit=>calls(edit.new)).sort(),fail+" unknown/duplicate owned call");
  for(const owner of ["localizedPageTitle","localizedPageDescription"]){
   const group=metadata.filter(edit=>edit.old.includes("Title")===(owner==="localizedPageTitle")),end=owner==="localizedPageTitle"?"  function documentTitle(":"  function initials(";
   exactAdded(source,group,()=>ownerBounds(source,"  function "+owner+"(",end));
  }
  let result=source;for(const edit of [...functions,...metadata].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 if(file===pages){
  const declaration=/^    ["']\/documents\/(?:ocr|pdf-ocr|pdf-ocr-to-word)["']:\s*\{/gm;
  const found=[...source.matchAll(declaration)];if(!found.length)return source;assert.equal(found.length,6,fail+" partial/duplicate shell entries");
  exactAdded(source,shell.filter(edit=>!edit.old.includes("\n")),()=>ownerBounds(source,"_PORTAL_SHELL_TITLES = {","\n_PORTAL_SHELL_DESCRIPTIONS = {"));
  exactAdded(source,shell.filter(edit=>edit.old.includes("\n")),()=>ownerBounds(source,"_PORTAL_SHELL_DESCRIPTIONS = {","\ndef _safe_portal_build_id("));
  let result=source;for(const edit of [...shell].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 return source;
}
export function documentOcrCustomerHistoricalSnapshot(entries,locale){
 const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");assert.ok(Array.isArray(entries),fail+" entries");
 entries=vaultCustomerHistoricalSnapshot(entries,locale);
 const owned=entries.filter(([key])=>typeof key==="string"&&key.startsWith("docOcr"));if(!owned.length)return entries;
 assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+" partial/changed/unknown/duplicate/reordered catalog");return entries.filter(([key])=>!keys.includes(key));
}
