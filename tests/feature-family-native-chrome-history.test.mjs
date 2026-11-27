import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {featureFamilyNativeChromeHistoricalSource as source,featureFamilyNativeChromeHistoricalSnapshot as snapshot} from "./helpers/feature-family-native-chrome-historical.mjs";
import {featureCatalogFullBundle135HistoricalSource} from "./helpers/feature-catalog-full-bundle135-historical.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const raw=fs.readFileSync(path.join(root,"tests/fixtures/feature-family-native-chrome.json"),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(raw).digest("hex"),"6da6b40e9a7a62b11363b3af067306e721fb51ddbdb6042b70ac5d601fc7cbff");
const fixture=JSON.parse(raw),failure=/Unreviewed feature-family native chrome/;
const before={},current={};
for(const pin of fixture.applicationSources){
  before[pin.file]=execFileSync("git",["show",fixture.base_sha+":"+pin.file],{cwd:root,encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n");
  current[pin.file]=before[pin.file];
  for(const row of fixture.records.filter(row=>row.file===pin.file)){
    assert.equal(current[pin.file].split(row.old).length-1,1);current[pin.file]=current[pin.file].replace(row.old,()=>row.new);
  }
  assert.equal(createHash("sha256").update(current[pin.file]).digest("hex"),pin.afterLfSha256);
}
for(const pin of fixture.applicationSources){
  test(`source leaf restores exact BASE and holds unknown outside bytes: ${pin.file}`,()=>{
    assert.equal(source(current[pin.file],pin.file),before[pin.file]);
    assert.equal(source(source(current[pin.file],pin.file),pin.file),before[pin.file]);
    assert.equal(source(before[pin.file],pin.file),before[pin.file]);
    assert.equal(source("/* CUSTOMER */\n"+current[pin.file]+"\n/* TAIL */",pin.file),"/* CUSTOMER */\n"+before[pin.file]+"\n/* TAIL */");
    assert.equal(source(current[pin.file],"customer/unrelated.js"),current[pin.file]);
  });
  for(const kind of["changed","partial","duplicate","detached","owner"])test(`source rejects ${kind}: ${pin.file}`,()=>{
    const rows=fixture.records.filter(row=>row.file===pin.file),row=rows[0];let bad;
    if(kind==="changed")bad=current[pin.file].replace(row.new,row.new.replace(pin.file.endsWith("portal-i18n.js")?"featureCatalog.":"family.heading",pin.file.endsWith("portal-i18n.js")?"UNREVIEWED.":"family.UNREVIEWED"));
    else if(kind==="partial")bad=current[pin.file].replace(row.new,row.old);
    else if(kind==="duplicate")bad=current[pin.file]+"\n"+row.new;
    else if(kind==="detached")bad=current[pin.file].replace(row.new,"")+"\n"+row.new;
    else{
      const owner=pin.file.endsWith("portal-i18n.js")?"  const FEATURE_CATALOG_MESSAGES = {":"  function renderFeatureFamily(page, context) {";
      bad=current[pin.file].replace(owner,owner+" UNREVIEWED");
    }
    // A single-record portal reverted wholly to OLD is a legitimate historical input.
    if(kind==="partial"&&rows.length===1)assert.equal(source(bad,pin.file),before[pin.file]);
    else assert.throws(()=>source(bad,pin.file),failure);
  });
}
for(const locale of["vi","en","zh"]){
  test(`source rejects reordered dictionary records: ${locale}`,()=>{
    const file="static/portal/portal-i18n.js",rows=fixture.records.filter(row=>row.file===file&&row.locale===locale);
    const bad=current[file].replace(rows[0].new,"__MOVE__").replace(rows[1].new,rows[0].new).replace("__MOVE__",rows[1].new);
    assert.throws(()=>source(bad,file),failure);
  });
  const old=fixture.copyRows.map(row=>[row.key,row.before[locale]]),now=fixture.copyRows.map(row=>[row.key,row.after[locale]]);
  test(`snapshot restores owned values and keeps unknown identity/order: ${locale}`,()=>{
    const unknown=["customer.unknown",{name:"CUSTOMER"}],input=[unknown,...now],saved=JSON.stringify(input);
    const actual=snapshot(input,locale);assert.deepEqual(actual,[unknown,...old]);
    assert.equal(actual[0],unknown);assert.equal(JSON.stringify(input),saved);
    assert.equal(snapshot(old,locale),old);
    assert.deepEqual(snapshot([...input].reverse(),locale),[unknown,...old].reverse());
  });
  test(`snapshot rejects changed/missing/duplicate owned data: ${locale}`,()=>{
    const changedIndex=fixture.copyRows.findIndex(row=>row.before[locale]!==row.after[locale]);
    const changed=now.map((row,index)=>index===changedIndex?[row[0],"UNREVIEWED"]:row);
    for(const bad of[changed,now.filter((_,index)=>index!==changedIndex),[...now,now[changedIndex]]]){
      assert.throws(()=>snapshot(bad,locale),failure);
    }
  });
}
test("snapshot rejects wrong locale/type; source preserves marker-free unrelated historical edits",()=>{
  for(const locale of["xx",null])assert.throws(()=>snapshot([],locale),failure);
  assert.throws(()=>snapshot({}, "vi"),failure);
  assert.equal(source("CUSTOMER_TEXT","static/portal/portal-i18n.js"),"CUSTOMER_TEXT");
});
test("composed historical source keeps the prior FBC owner-guard classification",()=>{
  const file="static/portal/portal-i18n.js";
  for(const marker of["  const FEATURE_CATALOG_MESSAGES = {","\n  // Media Studio follows"]){
    assert.throws(()=>featureCatalogFullBundle135HistoricalSource(current[file]+"\n"+marker,file),/Unreviewed full-bundle135 historical/);
  }
});
