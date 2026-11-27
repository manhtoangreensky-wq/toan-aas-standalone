import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {execFileSync} from "node:child_process";
import {galleryCustomerCopyHistoricalSource as project,galleryCustomerCopyHistoricalSnapshot as snapshot} from "./helpers/gallery-customer-copy-historical.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/gallery-customer-copy.json",import.meta.url),"utf8"));
const fail=/Unreviewed Gallery customer copy/;
for(const pin of fixture.applicationSources){
  const before=execFileSync("git",["show",fixture.base_sha+":"+pin.file],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n");
  const records=fixture.records.filter(row=>row.file===pin.file);let current=before;
  for(const row of records){assert.equal(current.split(row.old).length-1,1);current=current.replace(row.old,()=>row.new);}
  test(pin.file+" finite Gallery inverse restores BASE and keeps unknown/outside bytes",()=>{
    assert.equal(project(current,pin.file),before);assert.equal(project(project(current,pin.file),pin.file),before);
    assert.equal(project(before,pin.file),before);assert.equal(project(current,"customer/unrelated.js"),current);
    assert.equal(project("/* CUSTOMER */\r\n"+current+"\r\n/* TAIL */",pin.file),"/* CUSTOMER */\r\n"+before+"\r\n/* TAIL */");
    const internal=current.replace("\n","\n/* UNKNOWN */\n");
    assert.equal(project(internal,pin.file),before.replace("\n","\n/* UNKNOWN */\n"));
  });
  for(const kind of["changed","partial","duplicate","detached","owner","reordered"])test(pin.file+" finite Gallery inverse rejects "+kind,()=>{
    const row=records[Math.floor(records.length/2)];let bad;
    if(kind==="changed")bad=current.replace(row.new,row.new.replace("freePromptGallery","UNREVIEWED"));
    if(kind==="partial")bad=current.replace(row.new,row.old);
    if(kind==="duplicate")bad=current+"\n"+row.new;
    if(kind==="detached")bad=current.replace(row.new,"")+"\n"+row.new;
    if(kind==="owner")bad=current.replace(row.kind==="copy"?"  const "+row.owner+" = {":"  function "+row.owner+"(",
      row.kind==="copy"?"  const UNKNOWN = {":"  function UNKNOWN(");
    if(kind==="reordered"){const other=records.find(value=>value!==row);assert(other);bad=current.replace(row.new,"__GPC_SWAP__").replace(other.new,row.new).replace("__GPC_SWAP__",other.new);}
    assert.notEqual(bad,current);assert.throws(()=>project(bad,pin.file),fail);
  });
}
const copyByKey=new Map(fixture.copyRows.map(row=>[row.key,row]));
const orderedKeys=["shellNav.freePromptGallery",...fixture.copyRows.filter(row=>row.key!=="shellNav.freePromptGallery").map(row=>row.key)];
for(const locale of["vi","en","zh"]){
  const current=orderedKeys.map(key=>[key,copyByKey.get(key).after[locale]]);
  const before=orderedKeys.map(key=>[key,copyByKey.get(key).before[locale]]);
  test(`Gallery ${locale} snapshot restores only reviewed values, is idempotent, and retains outside row identity`,()=>{
    const unknown=["CUSTOMER_UNRELATED","CUSTOMER & <safe>"],rows=[unknown,...current];
    const saved=JSON.stringify(rows),result=snapshot(rows,locale);
    assert.equal(JSON.stringify(rows),saved);assert.equal(result[0],unknown);
    assert.deepEqual(result,[unknown,...before]);assert.deepEqual(snapshot(result,locale),result);
    assert.equal(snapshot(before,locale),before);assert.equal(snapshot([unknown],locale)[0],unknown);
  });
  for(const kind of["partial","changed","duplicate","reordered","wrong-locale","mixed","shape"])test(`Gallery ${locale} snapshot rejects ${kind} without masking historical differences`,()=>{
    let bad=current.map(row=>[...row]);
    if(kind==="partial")bad.pop();
    if(kind==="changed")bad[1][1]="UNREVIEWED_COPY";
    if(kind==="duplicate")bad.push([...bad[1]]);
    if(kind==="reordered")[bad[0],bad[1]]=[bad[1],bad[0]];
    if(kind==="wrong-locale")bad=orderedKeys.map(key=>[key,copyByKey.get(key).after[locale==="vi"?"en":"vi"]]);
    if(kind==="mixed")bad[1][1]=copyByKey.get(bad[1][0]).before[locale];
    if(kind==="shape")bad[1].push("UNREVIEWED_EXTRA");
    assert.throws(()=>snapshot(bad,locale),fail);
  });
}
test("Gallery snapshot rejects invalid locale or non-array input",()=>{
  assert.throws(()=>snapshot([],"ar"),fail);assert.throws(()=>snapshot({},"vi"),fail);
});
