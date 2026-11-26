import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {nativeLabelRecoveryHistoricalSource as project} from "./helpers/native-label-recovery-historical.mjs";
import {featureCatalogDescriptions108HistoricalSource} from "./helpers/feature-catalog-descriptions108-historical.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const file="static/portal/portal-feature-catalog-copy.js";
const fixture=JSON.parse(fs.readFileSync(path.join(root,"tests/fixtures/feature-catalog-video-native.json"),"utf8"));
const current=featureCatalogDescriptions108HistoricalSource(fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n"),file);
const before=execFileSync("git",["show",fixture.base_sha+":"+file],{cwd:root,encoding:"utf8",maxBuffer:5e6}).replace(/\r\n/g,"\n");
const rows=fixture.records,fail=/Unreviewed catalogue video historical source/;
assert.equal(rows.length,9);

test("the newest historical entry reverses only the exact nine reviewed data insertions",()=>{
  assert.equal(project(current,file),before);
  assert.equal(project(project(current,file),file),before);
});
test("legitimate OLD, older unowned text and unrelated files remain untouched",()=>{
  assert.equal(project(before,file),before);
  assert.equal(project("/* older source without these keys */",file),"/* older source without these keys */");
  assert.equal(project(current,"customer/unrelated.js"),current);
});
test("unknown outside bytes and changed old data are preserved for the original pin comparator",()=>{
  const prefix="/* owner unreviewed text */\n",suffix="\n/* outside mutation */";
  assert.equal(project(prefix+current+suffix,file),prefix+before+suffix);
  const oldTitle=fixture.beforeCopy.vi.dashboard.title;
  assert.equal(project(current.replace(JSON.stringify(oldTitle),'"OWNER_UNREVIEWED"'),file),
    before.replace(JSON.stringify(oldTitle),'"OWNER_UNREVIEWED"'));
});
test("a missing insertion is rejected instead of being treated as historical OLD",()=>{
  for(const row of rows)assert.throws(()=>project(current.replace(row.new,()=>row.old),file),fail);
});
test("an altered native value is never removed as an approved insertion",()=>{
  for(const row of rows){
    const prefix=row.new.slice(0,-row.old.length),value=JSON.parse("{"+prefix.replace(/,\s*$/,"")+"}");
    const first=Object.values(value)[0].title;
    assert.throws(()=>project(current.replace(row.new,row.new.replace(JSON.stringify(first),'"UNREVIEWED_VALUE"')),file),fail);
  }
});
test("duplicate insertions cannot disappear through the historical reader",()=>{
  for(const row of rows)assert.throws(()=>project(current+"\n"+row.new,file),fail);
});
test("detached or reordered row blocks do not satisfy the exact record boundary",()=>{
  for(const row of rows){
    const prefix=row.new.slice(0,-row.old.length);
    assert.throws(()=>project(current.replace(row.new,()=>row.old)+"\n"+prefix,file),fail);
    const keys=[...prefix.matchAll(/^    "([a-z0-9_]+)": \{/gm)].map(match=>match[1]);
    const changed=prefix.replace('"'+keys[0]+'"','"@@SWAP_KEY@@"').replace('"'+keys[1]+'"','"'+keys[0]+'"').replace('"@@SWAP_KEY@@"','"'+keys[1]+'"');
    assert.throws(()=>project(current.replace(row.new,()=>changed+row.old),file),fail);
  }
  const first=rows[0],second=rows[3],marker="@@UNREVIEWED_ROW_SWAP@@";
  assert.throws(()=>project(current.replace(first.new,marker).replace(second.new,()=>first.new).replace(marker,()=>second.new),file),fail);
  const row=rows[0],prefix=row.new.slice(0,-row.old.length);
  assert.throws(()=>project(current.replace(row.new,()=>prefix+"\n/* detached anchor */\n"+row.old),file),fail);
});
test("historical reads leave physical bytes unchanged and restore the original CVN candidate",()=>{
  const original=fs.readFileSync(path.join(root,file));
  project(current,file);
  assert.deepEqual(fs.readFileSync(path.join(root,file)),original);
  assert.equal(createHash("sha256").update(current).digest("hex"),fixture.afterLfSha256);
});
