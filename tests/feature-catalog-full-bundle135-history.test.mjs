import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {nativeLabelRecoveryHistoricalSource as project,nativeLabelRecoveryHistoricalSnapshot as snapshot} from "./helpers/native-label-recovery-historical.mjs";
import {fullBundleI18n} from "./helpers/feature-catalog-full-bundle135-render.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const fixture=JSON.parse(fs.readFileSync(path.join(root,"tests/fixtures/feature-catalog-full-bundle135.json"),"utf8"));
const file=fixture.applicationFile,show=sha=>execFileSync("git",["show",sha+":"+file],{cwd:root,encoding:"utf8",maxBuffer:10e6}).replace(/\r\n/g,"\n");
const before=show(fixture.base_sha),legacy=show("1a57e62152855b1cff39956d43ad0ccfd5f3d5cb");
let current=before;
for(const row of fixture.records){assert.equal(current.split(row.old).length-1,1);current=current.replace(row.old,()=>row.new);}
const actual=fullBundleI18n(current),oldApi=fullBundleI18n(legacy);
const replacements=fixture.records.filter(row=>row.kind==="replace");
const selected=["vi","en","zh"].flatMap(locale=>{
  const rows=replacements.filter(row=>row.locale===locale);
  return[rows[0],rows[Math.floor(rows.length/2)],rows.at(-1)];
});
const insertions=fixture.records.filter(row=>row.kind==="insert");
const fail=/Unreviewed full-bundle135 historical/;

test("newest historical source reverses exactly289 records before the older NLR layer",()=>{
  assert.equal(project(current,file),legacy);
  assert.equal(project(project(current,file),file),legacy);
});
test("legitimate OLD and unrelated source remain unchanged by the new historical layer",()=>{
  assert.equal(project(before,file),legacy);assert.equal(project(legacy,file),legacy);
  assert.equal(project("/* older unowned text */",file),"/* older unowned text */");
  assert.equal(project(current,"customer/unrelated.js"),current);
});
test("unknown prefix suffix and unrelated internal bytes remain visible to original pins",()=>{
  const prefix="/* Owner outside */\n",suffix="\n/* Owner tail */";
  assert.equal(project(prefix+current+suffix,file),prefix+legacy+suffix);
  const unknown=text=>text.replace("\n","\n/* Owner unrelated internal */\n");
  assert.equal(project(unknown(current),file),unknown(legacy));
});
test("partial insertions or changed-description application are rejected",()=>{
  for(const row of[...insertions,...selected])assert.throws(()=>project(current.replace(row.new,()=>row.old),file),fail);
});
test("changed approved source values are not removed as reviewed data",()=>{
  for(const row of selected){
    const changed=row.new.replace(/:\s*"(?:[^"\\]|\\.)*",$/,': "UNREVIEWED",');
    assert.notEqual(changed,row.new);
    assert.throws(()=>project(current.replace(row.new,()=>changed),file),fail);
  }
});
test("duplicate or detached exact records are rejected including the last locale",()=>{
  for(const row of[...insertions,...selected]){
    assert.throws(()=>project(current+"\n"+row.new,file),fail);
    assert.throws(()=>project(current.replace(row.new,()=>row.old)+"\n"+row.new,file),fail);
  }
});
test("whole-record swaps keep the original failure rather than disappearing",()=>{
  for(const locale of["vi","en","zh"]){
    const rows=replacements.filter(row=>row.locale===locale),first=rows[0],last=rows.at(-1),marker="@@UNREVIEWED_FBC_ORDER@@";
    assert.throws(()=>project(current.replace(first.new,marker).replace(last.new,()=>first.new).replace(marker,()=>last.new),file),fail);
  }
});
test("historical source projection never writes current physical application input",()=>{
  const original=fs.readFileSync(path.join(root,file));project(current,file);
  assert.deepEqual(fs.readFileSync(path.join(root,file)),original);
});

for(const locale of["vi","en","zh"]){
  const prefix="featureCatalog.entry.";
  const owned=Object.entries(actual.messages[locale]).filter(([key])=>key.startsWith(prefix));
  const prior=Object.entries(fixture.beforeCatalog[locale]);
  test(`${locale}: exact snapshot restores192oldfields and preserves unrelated entry identity/order`,()=>{
    const first=Object.freeze(["customer.first","Facebook TikTok media studio <safe>"]);
    const last=Object.freeze(["featureCatalog.entry.future_owner.title","Owner literal"]);
    const entries=Object.freeze([first,...owned.map(row=>Object.freeze(row)),last]);
    const result=snapshot(entries,locale);
    assert.deepEqual(result,[first,...prior,last]);assert.strictEqual(result[0],first);assert.strictEqual(result.at(-1),last);
    const held=entries.find(([key])=>key==="featureCatalog.entry.dashboard.title");
    assert.strictEqual(result.find(([key])=>key===held[0]),held);
    assert.deepEqual(snapshot(result,locale),result);
    assert.equal(entries.length,272);
  });
  test(`${locale}: OLD/unowned snapshots preserve the original array and customer text`,()=>{
    assert.strictEqual(snapshot(prior,locale),prior);
    const unknown=[["customer.unknown","signed provider media studio"]];
    assert.strictEqual(snapshot(unknown,locale),unknown);
  });
  test(`${locale}: partial changed duplicate and reordered owned snapshots fail closed`,()=>{
    const missing=prefix+fixture.missingKeys[0]+".title";
    const changed=fixture.changedExisting.find(row=>row.locale===locale).key;
    const invalid=[
      owned.filter(([key])=>key!==missing),
      [...owned,owned[0]],
      owned.map(([key,value])=>[key,key===missing?"UNREVIEWED":value]),
      owned.map(([key,value])=>[key,key===changed?"UNREVIEWED":value]),
      [owned[1],owned[0],...owned.slice(2)]
    ];
    for(const entries of invalid)assert.throws(()=>snapshot(entries,locale),fail);
  });
  test(`${locale}: full dictionary projection composes with NLR and retains every other message`,()=>{
    assert.deepEqual(snapshot(Object.entries(actual.messages[locale]),locale),Object.entries(oldApi.messages[locale]));
  });
}
test("original NLR array and locale validation precedes the new finite snapshot leaf",()=>{
  for(const[entries,locale]of[[null,"vi"],[[],"fr"]]){
    assert.throws(()=>snapshot(entries,locale),error=>!fail.test(error.message));
  }
});
