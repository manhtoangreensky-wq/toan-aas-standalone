// Finite inverse for historical test inputs only; never app rendering.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {customerNaturalHistoricalSource,customerNaturalHistoricalSnapshot} from "./customer-natural-followup-historical.mjs";
const fail="Unreviewed document natural-copy history";
const sha=s=>createHash("sha256").update(s).digest("hex");
const raw=fs.readFileSync(new URL("../fixtures/document-natural-copy-history.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(sha(raw),"743eea1bfe1b7ae9a192f57f9a153d93007d9097c830b9fd110ec53d8a258098",fail+" fixture");
const fixture=JSON.parse(raw),locales=["vi","en","zh"];
assert.equal(fixture.base_sha,"cf94b23e6a26010e88ebcd33b36623204c784c9a",fail+" BASE");
assert.equal(fixture.records.length,60,fail+" records");
const files=new Set(["static/portal/portal.js","static/portal/integration.js","static/portal/portal-i18n.js"]);
for(const row of fixture.records){
  assert(files.has(row.file)&&row.before.length&&row.after.length,fail+" record shape");
  assert.equal(sha(row.before),row.before_sha256,fail+" before");
  assert.equal(sha(row.after),row.after_sha256,fail+" after");
}
const keys=fixture.snapshots.vi.map(row=>row[0]),owned=new Set(keys);
assert.equal(keys.length,304);assert.equal(owned.size,304);
for(const locale of locales)assert.deepEqual(fixture.snapshots[locale].map(row=>row[0]),keys,fail+" locale keys");
export function documentNaturalHistoricalSource(source,file){
  assert.equal(typeof source,"string",fail+" source");
  source=customerNaturalHistoricalSource(source,file);
  if(!files.has(file)||!source.includes("docPlain"))return source;
  const ending=source.includes("\r\n")?"\r\n":"\n";
  for(const row of [...fixture.records].reverse().filter(row=>row.file===file)){
    const after=row.after.replace(/\n/g,ending),before=row.before.replace(/\n/g,ending);
    assert.equal(source.split(after).length-1,1,fail+" missing/changed/duplicate owned record");
    source=source.replace(after,()=>before);
  }
  assert(!source.includes("docPlain"),fail+" unknown/partial owned source");
  return source;
}
export function documentNaturalHistoricalSnapshot(entries,locale){
  assert(Array.isArray(entries)&&locales.includes(locale),fail+" snapshot input");
  entries=customerNaturalHistoricalSnapshot(entries,locale);
  const found=entries.filter(row=>Array.isArray(row)&&owned.has(row[0]));
  if(!found.length)return entries;
  assert.deepEqual(found,fixture.snapshots[locale],fail+" complete exact ordered values");
  return entries.filter(row=>!owned.has(row[0]));
}
