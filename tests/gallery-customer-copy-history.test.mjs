import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {execFileSync} from "node:child_process";
import {galleryCustomerCopyHistoricalSource as project} from "./helpers/gallery-customer-copy-historical.mjs";
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
