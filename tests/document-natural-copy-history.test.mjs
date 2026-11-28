import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {documentNaturalHistoricalSource as inverse,documentNaturalHistoricalSnapshot as snapshot} from "./helpers/document-natural-copy-historical.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/document-natural-copy-history.json",import.meta.url),"utf8"));
const files=["static/portal/portal.js","static/portal/integration.js","static/portal/portal-i18n.js"];
for(const file of files){
  const source=fs.readFileSync(new URL("../"+file,import.meta.url),"utf8").replace(/\r\n/g,"\n");
  const base=execFileSync("git",["show",fixture.base_sha+":"+file],{encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n");
  test(`${file}: finite inverse equals immutable baseline while raw current source differs`,()=>{
    assert.notEqual(source,base);assert.equal(inverse(source,file),base);assert.equal(inverse(base,file),base);
  });
  const candidates=fixture.records.filter(row=>row.file===file&&source.split(row.after).length-1===1);
  assert(candidates.length>0);
  const selected=[...new Set([candidates[0],candidates[Math.floor(candidates.length/2)],candidates.at(-1)])];
  for(const [index,row] of selected.entries())test(`${file}/${index}: partial, changed and duplicate reviewed input is rejected`,()=>{
    for(const replacement of [row.after.slice(0,-1),row.after+" ",row.after+row.after]){
      const changed=source.replace(row.after,()=>replacement);
      if(replacement===row.after+" "){
        // Unknown bytes outside the approved span must survive, never vanish.
        const restored=inverse(changed,file);assert.notEqual(restored,base);assert.ok(restored.includes(" "));
      }else assert.throws(()=>inverse(changed,file),/Unreviewed document/);
    }
  });
  test(`${file}: an unrelated appended change is preserved`,()=>{
    const extra="\n// UNKNOWN_CUSTOMER_CHANGE\n";
    assert.equal(inverse(source+extra,file),base+extra);
  });
}
for(const locale of ["vi","en","zh"])test(`${locale}: exact new values only, unknown customer entries survive`,()=>{
  const rows=fixture.snapshots[locale],foreign=["CUSTOMER","QA metadata studio Facebook TikTok"];
  assert.deepEqual(snapshot([...rows,foreign],locale),[foreign]);
  assert.throws(()=>snapshot(rows.slice(1),locale),/Unreviewed document/);
  assert.throws(()=>snapshot([...rows,rows[0]],locale),/Unreviewed document/);
  assert.throws(()=>snapshot(rows.map((row,i)=>i===0?[row[0],row[1]+"!"]:row),locale),/Unreviewed document/);
  assert.deepEqual(snapshot([foreign],locale),[foreign]);
});
