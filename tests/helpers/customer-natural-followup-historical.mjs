// Exact finite inverse for old test inputs; never used by the application.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
const fail="Unreviewed customer natural-copy history";
const sha=value=>createHash("sha256").update(value).digest("hex");
const raw=fs.readFileSync(new URL("../fixtures/customer-natural-followup-history.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(sha(raw),"d74a68658d1dedb5dc986debc874f45dfe50355175414e64f1d4fff68bb68eb6",fail+" fixture");
const fixture=JSON.parse(raw),locales=["vi","en","zh"];
assert.equal(fixture.base_sha,"469f70063217814522b674272185227d93c8a08c",fail+" base");
assert.equal(fixture.records.length,2);
assert.equal(fixture.values.length,413);
assert.equal(new Set(fixture.values.map(row=>row.key)).size,413);
for(const row of fixture.records){
  assert(["static/portal/portal.js","static/portal/portal-i18n.js"].includes(row.file));
  assert.equal(sha(row.before),row.before_sha256,fail+" before");
  assert.equal(sha(row.after),row.after_sha256,fail+" after");
}
export function customerNaturalHistoricalSource(source,file){
  assert.equal(typeof source,"string");
  const row=fixture.records.find(record=>record.file===file);
  if(!row)return source;
  const ending=source.includes("\r\n")?"\r\n":"\n";
  const before=row.before.replace(/\n/g,ending),after=row.after.replace(/\n/g,ending);
  if(file.endsWith("portal.js")){
    if(!source.includes(row.owner)&&!source.includes(after))return source;
    if(source.split(before).length-1===1&&!source.includes(after))return source;
  }else if(!source.includes("Natural customer wording; behavior and data remain unchanged.")
    &&!source.includes('"summary.companion": "Ứng dụng liên kết"'))return source;
  assert.equal(source.split(after).length-1,1,fail+" missing, changed or duplicate owned record");
  return source.replace(after,()=>before);
}
export function customerNaturalHistoricalSnapshot(entries,locale){
  assert(Array.isArray(entries)&&locales.includes(locale));
  const owned=new Map(fixture.values.map(row=>[row.key,row]));
  const found=entries.filter(row=>Array.isArray(row)&&owned.has(row[0]));
  if(!found.length)return entries;
  assert.equal(found.length,413,fail+" incomplete values");
  assert.equal(new Set(found.map(row=>row[0])).size,413,fail+" duplicate values");
  if(found.every(([key,value])=>value===owned.get(key).before[locale]))return entries;
  for(const[key,value]of found)assert.equal(value,owned.get(key).after[locale],fail+" changed value");
  return entries.map(row=>owned.has(row[0])?[row[0],owned.get(row[0]).before[locale]]:row);
}
