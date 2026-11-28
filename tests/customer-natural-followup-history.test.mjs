import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {customerNaturalHistoricalSource as inverse,customerNaturalHistoricalSnapshot as snapshot} from "./helpers/customer-natural-followup-historical.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/customer-natural-followup-history.json",import.meta.url),"utf8"));
const lf=value=>value.replace(/\r\n/g,"\n");
const baseline=file=>lf(execFileSync("git",["show",fixture.base_sha+":"+file],{encoding:"utf8",maxBuffer:30e6}));
for(const row of fixture.records){
  const raw=lf(fs.readFileSync(new URL("../"+row.file,import.meta.url),"utf8")),base=baseline(row.file);
  test(row.file+": finite inverse exactly recovers immutable source and preserves unknown bytes",()=>{
    assert.equal(raw,base.replace(row.before,()=>row.after));
    assert.equal(inverse(raw,row.file),base);
    assert.equal(inverse(base,row.file),base);
    assert.equal(inverse(inverse(raw,row.file),row.file),base);
    const extra="\n/* customer 自由 <b>& literal */\n";
    assert.equal(inverse(raw+extra,row.file),base+extra);
    assert.equal(inverse(raw.replace(/\n/g,"\r\n"),row.file),base.replace(/\n/g,"\r\n"));
  });
  test(row.file+": missing, changed and duplicate owned records cannot pass as approved history",()=>{
    const changed=row.file.endsWith("portal.js")?row.after.replace("mfaTitle","mfaTitleChanged"):row.after.replace("Ứng dụng liên kết","Nhãn đã bị đổi");
    for(const replacement of [changed,row.after+row.after,row.after.slice(0,-1)]){
      assert.throws(()=>inverse(raw.replace(row.after,()=>replacement),row.file),/Unreviewed customer/);
    }
  });
}
for(const locale of ["vi","en","zh"])test(locale+": restores only exact existing values and preserves key order and foreign customer data",()=>{
  const read=source=>{const box=vm.createContext({});vm.runInContext(source,box);return JSON.parse(JSON.stringify(Object.entries(box.TOANAASI18n.messages[locale])));};
  const before=read(baseline("static/portal/portal-i18n.js"));
  const after=read(fs.readFileSync(new URL("../static/portal/portal-i18n.js",import.meta.url),"utf8"));
  assert.deepEqual(snapshot(after,locale),before);
  assert.deepEqual(snapshot(before,locale),before);
  const customer=["CUSTOMER","QA metadata Studio Facebook TikTok"];
  assert.deepEqual(snapshot([...after,customer],locale),[...before,customer]);
  const owned=new Set(fixture.values.map(row=>row.key)),first=after.findIndex(row=>owned.has(row[0]));
  assert.throws(()=>snapshot(after.filter((_,index)=>index!==first),locale),/Unreviewed customer/);
  assert.throws(()=>snapshot([...after,after[first]],locale),/Unreviewed customer/);
  assert.throws(()=>snapshot(after.map((row,index)=>index===first?[row[0],row[1]+"!"]:row),locale),/Unreviewed customer/);
});
