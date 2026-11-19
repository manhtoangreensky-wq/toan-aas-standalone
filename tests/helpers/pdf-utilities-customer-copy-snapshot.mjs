import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {imageEditCustomerHistoricalSource,imageEditCustomerHistoricalSnapshot} from "./image-edit-customer-copy-snapshot.mjs";
// Historical-comparator leaf only. Current rendering/feature acceptance must keep physical bundles.
const raw=fs.readFileSync(new URL("../fixtures/pdf-utilities-customer-copy-reviewed.json",import.meta.url));
const SHA="fb1ffa41f9d924a11caf78b840d5ebc2a8e6a270eb49e91838868def71973870",fail="Unreviewed PDF utilities customer copy";
assert.equal(createHash("sha256").update(raw).digest("hex"),SHA,fail+" authority hash");
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,portal="static/portal/portal.js",i18n="static/portal/portal-i18n.js",count=(text,part)=>text.split(part).length-1;
assert.equal(fixture.base,"513557a9ece0f8fe049884868dc5fb3a1ac2339c");assert.equal(fixture.task,"PDF-UTILITIES-CUSTOMER-COPY-20261119");
assert.equal(edits.length,4);assert.deepEqual(edits.map(edit=>edit.file),[portal,portal,portal,i18n]);assert.ok(edits.every(edit=>edit.count===1));
assert.deepEqual(fixture.ownerOrder,["imageToPdfFormFields","renderPdfOptimize","renderImageToPdf"]);
assert.deepEqual(fixture.nextOwners,{imageToPdfFormFields:"validImageOperationId",renderPdfOptimize:"renderPdfToImages",renderImageToPdf:"renderImageOperationHistory"});
const functions=edits.slice(0,3).map(edit=>{const old=edit.old.match(/^  function (\w+)\(/),next=edit.new.match(/^  function (\w+)\(/);assert.ok(old&&next);assert.equal(old[1],next[1]);return{...edit,name:old[1],marker:"  function "+old[1]+"("};}).sort((a,b)=>fixture.ownerOrder.indexOf(a.name)-fixture.ownerOrder.indexOf(b.name));
assert.deepEqual(functions.map(edit=>edit.name),fixture.ownerOrder);
const rows=[...fixture.fieldsRows,...fixture.pageRows],keys=rows.map(row=>row[0]),catalogue=edits[3],namespace=key=>key.startsWith("docImageToPdf");
assert.equal(fixture.fieldsRows.length,6);assert.equal(fixture.pageRows.length,9);assert.equal(keys.length,15);assert.equal(new Set(keys).size,15);assert.ok(keys.every(namespace));
assert.equal(catalogue.old,"  verifyEqualKeysets();");assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];
assert.deepEqual(blocks.map(match=>match[1]),["vi","en","zh","vi","en","zh"]);
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
  const actual=blocks.filter(match=>match[1]===locale).flatMap(match=>Object.entries(JSON.parse(match[2])));
  assert.deepEqual(actual,rows.map(row=>[row[0],row[index]]),fail+" exact worker keys/values/order");
}
function ownedDeclarations(source){
  const found=[];for(const block of source.matchAll(/Object\.assign\(MESSAGES\.(?:vi|en|zh),\s*\{([\s\S]*?)\}\);/g))
    for(const key of block[1].matchAll(/(?:^|,|\n)\s*["']?(docImageToPdf[A-Za-z0-9_]*)["']?\s*:/g))found.push(key[1]);
  return found;
}
export function pdfUtilitiesCustomerHistoricalSource(source,file){
  assert.equal(typeof source,"string",fail);
  source=imageEditCustomerHistoricalSource(source,file);
  if(file!==portal&&file!==i18n)return source;
  if(file===i18n){
    const found=ownedDeclarations(source),next=count(source,catalogue.new);
    assert.ok(next<=1,fail+" duplicate catalogue");
    if(!found.length){assert.equal(next,0,fail+" missing owned catalogue");return source;}
    assert.equal(next,1,fail+" partial/changed/detached catalogue");
    assert.equal(count(source,catalogue.old),1,fail+" keyset anchor count");
    assert.equal(found.length,45,fail+" unknown/duplicate catalogue declaration");
    for(const key of keys)assert.equal(found.filter(value=>value===key).length,3,fail+" key count");
    assert.ok(found.every(key=>keys.includes(key)),fail+" unknown catalogue key");
    const point=source.indexOf(catalogue.new),verify=source.indexOf(catalogue.old),freeze="  deepFreeze(MESSAGES);";
    assert.equal(count(source,freeze),1,fail+" freeze anchor");
    assert.ok(point<verify&&verify<source.indexOf(freeze),fail+" catalogue must precede keyset and freeze");
    return source.slice(0,point)+catalogue.old+source.slice(point+catalogue.new.length);
  }
  const phases=functions.map(edit=>({edit,old:count(source,edit.old),next:count(source,edit.new)}));
  assert.ok(phases.every(value=>value.old<=1&&value.next<=1),fail+" duplicate complete function");
  const hasNew=phases.some(value=>value.next===1)||functions.some(edit=>{
    const start=source.indexOf(edit.marker),end=source.indexOf("\n  function ",start+edit.marker.length);
    return start>=0&&end>start&&/\bdocImageToPdf(?:Field|ReadyUi)/.test(source.slice(start,end));
  });
  // Older boundaries without any owned new marker are not projected or forced into this BASE.
  if(!hasNew&&!phases.every(value=>value.old===1))return source;
  const old=phases.every(value=>value.old===1&&value.next===0),next=phases.every(value=>value.old===0&&value.next===1);
  assert.ok(old||next,fail+" partial/changed/mixed function set");
  let previous=-1;
  for(const{edit}of phases){
    assert.equal(count(source,edit.marker),1,fail+" function owner count");const point=source.indexOf(next?edit.new:edit.old);
    assert.equal(point,source.indexOf(edit.marker),fail+" detached complete function");assert.ok(point>previous,fail+" reordered owner");previous=point;
    const text=next?edit.new:edit.old,nextMarker="  function "+fixture.nextOwners[edit.name]+"(";
    assert.equal(count(source,nextMarker),1,fail+" next owner count");
    assert.ok(source.slice(point+text.length).startsWith(nextMarker),fail+" immediate next owner");
  }
  if(old)return source;let result=source;
  for(const edit of [...functions].reverse())result=result.replace(edit.new,()=>edit.old);
  return result;
}
export function pdfUtilitiesCustomerHistoricalSnapshot(entries,locale){
  const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");assert.ok(Array.isArray(entries),fail+" entries");
  entries=imageEditCustomerHistoricalSnapshot(entries,locale);
  const owned=entries.filter(([key])=>typeof key==="string"&&namespace(key));if(!owned.length)return entries;
  assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+" partial/unknown/duplicate/reordered owned catalogue");
  return entries.filter(([key])=>!keys.includes(key));
}
