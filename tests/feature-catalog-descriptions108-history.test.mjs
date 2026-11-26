import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {nativeLabelRecoveryHistoricalSource as project} from "./helpers/native-label-recovery-historical.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const fixture=JSON.parse(fs.readFileSync(path.join(root,"tests/fixtures/feature-catalog-descriptions108.json"),"utf8"));
const file=fixture.applicationFile;
const show=sha=>execFileSync("git",["show",sha+":"+file],{cwd:root,encoding:"utf8",maxBuffer:5e6}).replace(/\r\n/g,"\n");
const before=show(fixture.base_sha),legacy=show("ccf824a1482ef3ae7fd2d4187932902e36ddbc14");
let current=before;
for(const row of fixture.records){assert.equal(current.split(row.old).length-1,1);current=current.replace(row.old,()=>row.new);}
const representatives=["vi","en","zh"].flatMap(locale=>{
  const rows=fixture.records.filter(row=>row.locale===locale);
  return[rows[0],rows[Math.floor(rows.length/2)],rows.at(-1)];
});
const fail=/Unreviewed catalogue descriptions108 historical source/;

test("the historical entry reverses the exact322 descriptions before the nine older CVN additions",()=>{
  assert.equal(project(current,file),legacy);
  assert.equal(project(project(current,file),file),legacy);
});
test("legitimate OLD, older unowned source and unrelated targets remain valid",()=>{
  assert.equal(project(before,file),legacy);
  assert.equal(project(legacy,file),legacy);
  assert.equal(project("/* older source without reviewed additions */",file),"/* older source without reviewed additions */");
  assert.equal(project(current,"customer/unrelated.js"),current);
});
test("outside bytes and old wrapper mutations remain visible to the original golden pins",()=>{
  const prefix="/* owner text */\n",suffix="\n/* owner suffix */";
  assert.equal(project(prefix+current+suffix,file),prefix+legacy+suffix);
  const old="display: none !important;",next="display: block !important;";
  assert(current.includes(old)&&legacy.includes(old));
  assert.equal(project(current.replace(old,next),file),legacy.replace(old,next));
});
test("a missing record at each locale boundary or middle is rejected",()=>{
  for(const row of representatives)assert.throws(()=>project(current.replace(row.new,()=>row.old),file),fail);
});
test("an altered reviewed description is rejected at each locale boundary or middle",()=>{
  for(const row of representatives){
    const old=JSON.stringify(fixture.copy[row.locale][row.key].description);
    assert.throws(()=>project(current.replace(row.new,row.new.replace(old,'"UNREVIEWED_VALUE"')),file),fail);
  }
});
test("duplicate and detached records cannot disappear in a historical read",()=>{
  for(const row of representatives){
    assert.throws(()=>project(current+"\n"+row.new,file),fail);
    assert.throws(()=>project(current.replace(row.new,()=>row.old)+"\n"+row.new,file),fail);
  }
});
test("whole-record order changes are rejected without changing unrelated text",()=>{
  for(const locale of["vi","en","zh"]){
    const rows=fixture.records.filter(row=>row.locale===locale),first=rows[0],last=rows.at(-1),marker="@@UNREVIEWED_ORDER@@";
    assert.throws(()=>project(current.replace(first.new,marker).replace(last.new,()=>first.new).replace(marker,()=>last.new),file),fail);
  }
});
test("historical reads never write the physical file used by current CD108 acceptance",()=>{
  const original=fs.readFileSync(path.join(root,file));
  project(current,file);
  assert.deepEqual(fs.readFileSync(path.join(root,file)),original);
});
