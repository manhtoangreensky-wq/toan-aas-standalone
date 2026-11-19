import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
// Finite historical comparator only. Never pass its output to a current renderer.
const raw=fs.readFileSync(new URL("../fixtures/document-convert-customer-copy-reviewed.json",import.meta.url));
const fail="Unreviewed Document Convert customer copy",count=(source,part)=>source.split(part).length-1;
assert.equal(createHash("sha256").update(raw).digest("hex"),"e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63",fail+" authority hash");
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const portal="static/portal/portal.js",i18n="static/portal/portal-i18n.js",pages="copyfast_pages.py";
assert.equal(fixture.task,"DOCUMENT-CONVERT-CUSTOMER-COPY-20261119");assert.equal(fixture.base,"a589008be5d7be371789551ffc11e750db46270b");assert.equal(fixture.revision,"ROOT_REVIEWED_R1");
assert.equal(edits.length,13);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,28);assert.equal(new Set(keys).size,28);
assert.ok(keys.every(key=>/^docConvert(?:Fields|Images|Word)Ui[A-Za-z]+$/.test(key)));
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.revision,value.conversation,value.resultRawSha256]),[
 ["fields","R1","4016959a-13b1-4e7f-8289-56378a80fb0c","e45d1562702d5a273aebdf119f47477bdcf4b42d18e542a4007eb5b3ed2c1138"],
 ["images","R1","523ff7c6-8df9-4a1b-8aae-3ac0078bb922","40fe39546c9973a700cb5a6e230c53a0604be373c9b2f3b7e6a9bc8bfb0d7b6a"],
 ["word","R1","f5e057f5-c42e-4072-8794-27a4fd1da479","9dda1cdfb7c6117a12efacd4e5c8f87b34a5b24c11ac6bb246ea137efea19ca8"]]);
assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.applicationFailureCount===0&&value.applicationWrites===0&&value.verify==="NOT_RUN"));
const functions=edits.filter(edit=>edit.file===portal&&edit.old.startsWith("  function ")).map(edit=>{
 const name=edit.old.match(/^  function (\w+)\(/)?.[1];assert.ok(name);assert.ok(edit.new.startsWith("  function "+name+"("));
 return{...edit,name,marker:"  function "+name+"("};
});
const nextOwners={pdfToWordFormFields:"imageOcrFormFields",pdfToImagesFormFields:"imageToPdfFormFields",renderPdfToImages:"renderPdfToWord",renderPdfToWord:"renderImageOcr"};
assert.deepEqual(functions.map(edit=>edit.name),Object.keys(nextOwners));
const metadata=edits.filter(edit=>edit.file===portal&&!edit.old.startsWith("  function "));
const shell=edits.filter(edit=>edit.file===pages),catalogue=edits.find(edit=>edit.file===i18n);
assert.equal(metadata.length,4);assert.equal(shell.length,4);assert.ok(catalogue);
for(const edit of [...metadata,...shell]){assert.ok(edit.new.endsWith(edit.old));assert.ok(edit.new.length>edit.old.length);}
assert.equal(catalogue.old,"  verifyEqualKeysets();");assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];
assert.deepEqual(blocks.map(match=>match[1]),["vi","en","zh"]);
for(const[locale,index]of [["vi",1],["en",2],["zh",3]])assert.deepEqual(Object.entries(JSON.parse(blocks.find(match=>match[1]===locale)[2])),rows.map(row=>[row[0],row[index]]));
const addition=edit=>edit.new.slice(0,-edit.old.length);
const metadataOwner=edit=>edit.old.includes("Title")?"localizedPageTitle":"localizedPageDescription";
function ownerBounds(source,marker,endMarker){
 const start=source.indexOf(marker),end=source.indexOf(endMarker,start+marker.length);
 assert.equal(count(source,marker),1,fail+" owner count");assert.ok(start>=0&&end>start,fail+" owner bounds");return[start,end];
}
function exactAdded(source,group,bounds){
 let previous=-1;
 for(const edit of group){
  const added=addition(edit);assert.equal(count(source,edit.new),1,fail+" changed/partial/detached metadata");assert.equal(count(source,added),1,fail+" duplicate metadata");
  const point=source.indexOf(edit.new),[start,end]=bounds(edit);
  assert.ok(point>start&&point+edit.new.length<=end,fail+" metadata outside owner");assert.ok(point>previous,fail+" reordered metadata");previous=point;
 }
}
function catalogueDeclarations(source){
 return [...source.matchAll(/Object\.assign\(MESSAGES\.(?:vi|en|zh),\s*\{([\s\S]*?)\}\);/g)]
  .flatMap(match=>[...match[1].matchAll(/(?:^|,|\n)\s*["']?(docConvert[A-Za-z0-9_]*)["']?\s*:/g)].map(value=>value[1]));
}
export function documentConvertCustomerHistoricalSource(source,file){
 assert.equal(typeof source,"string",fail);
 if(file===i18n){
  const found=catalogueDeclarations(source),next=count(source,catalogue.new);
  if(!found.length){assert.equal(next,0,fail+" absent catalog");return source;}
  assert.equal(next,1,fail+" partial/changed/duplicate catalog");assert.equal(found.length,84,fail+" partial/unknown declarations");
  for(const key of keys)assert.equal(found.filter(value=>value===key).length,3,fail+" key count");
  assert.ok(found.every(key=>keys.includes(key)),fail+" unknown prefixed key");
  const point=source.indexOf(catalogue.new),freeze="  deepFreeze(MESSAGES);";
  assert.equal(count(source,catalogue.old),1,fail+" keyset anchor");assert.equal(count(source,freeze),1,fail+" freeze anchor");
  assert.ok(point<source.indexOf(freeze),fail+" post-freeze catalog");
  assert.ok(source.slice(point+catalogue.new.length).startsWith("\n\n  function deepFreeze(value) {"),fail+" detached catalog boundary");
  return source.replace(catalogue.new,()=>catalogue.old);
 }
 if(file===portal){
  const phases=functions.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const marked=/\buiText\(["']docConvert[A-Za-z0-9_]*["']/.test(source),next=phases.every(([a,b])=>a===0&&b===1);
  // Unowned OLD boundaries belong to older comparators, including their own malformed-vector errors.
  if(!marked)return source;
  assert.ok(next,fail+" partial/mixed/changed functions");let previous=-1;
  for(const edit of functions){
   assert.equal(count(source,edit.marker),1,fail+" missing/duplicate function owner");
   const point=source.indexOf(edit.new),nextMarker="  function "+nextOwners[edit.name]+"(";
   assert.equal(point,source.indexOf(edit.marker),fail+" detached complete function");assert.ok(point>previous,fail+" reordered functions");previous=point;
   assert.equal(count(source,nextMarker),1,fail+" next owner count");assert.ok(source.slice(point+edit.new.length).startsWith(nextMarker),fail+" immediate next owner");
  }
  const calls=[...source.matchAll(/\buiText\(["'](docConvert[A-Za-z0-9_]*)["']/g)].map(match=>match[1]);
  const declared=[...functions,...metadata].flatMap(edit=>[...edit.new.matchAll(/\buiText\(["'](docConvert[A-Za-z0-9_]*)["']/g)].map(match=>match[1]));
  assert.deepEqual(calls.slice().sort(),declared.slice().sort(),fail+" unknown/duplicate/partial owned calls");
  for(const owner of ["localizedPageTitle","localizedPageDescription"]){
   const group=metadata.filter(edit=>metadataOwner(edit)===owner),end=owner==="localizedPageTitle"?"  function documentTitle(":"  function initials(";
   exactAdded(source,group,()=>ownerBounds(source,"  function "+owner+"(",end));
  }
  let result=source;for(const edit of [...functions,...metadata].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 if(file===pages){
  const marked=/^    ["']\/documents\/pdf-to-(?:images|word)["']:\s*\{/m.test(source);if(!marked)return source;
  assert.equal([...source.matchAll(/^    ["']\/documents\/pdf-to-(?:images|word)["']:\s*\{/gm)].length,4,fail+" missing/duplicate shell entries");
  const title=shell.filter(edit=>!edit.old.includes("\n")),description=shell.filter(edit=>edit.old.includes("\n"));
  exactAdded(source,title,()=>ownerBounds(source,"_PORTAL_SHELL_TITLES = {","\n_PORTAL_SHELL_DESCRIPTIONS = {"));
  exactAdded(source,description,()=>ownerBounds(source,"_PORTAL_SHELL_DESCRIPTIONS = {","\ndef _safe_portal_build_id("));
  let result=source;for(const edit of [...shell].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 return source;
}
export function documentConvertCustomerHistoricalSnapshot(entries,locale){
 const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");assert.ok(Array.isArray(entries),fail+" entries");
 const owned=entries.filter(([key])=>typeof key==="string"&&key.startsWith("docConvert"));if(!owned.length)return entries;
 assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+" partial/changed/unknown/duplicate/reordered catalog");
 return entries.filter(([key])=>!keys.includes(key));
}
