import fs from "node:fs";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/image-resize-plain-copy-reviewed.json",import.meta.url),"utf8"));
const baseline=execFileSync("git",["show",fixture.base+":static/portal/portal-i18n.js"],{encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n");
const fail="Unreviewed Image Resize plain copy",locales=["vi","en","zh"],count=(s,p)=>s.split(p).length-1;
export const resizePlainChanges=fixture.rows.map(row=>{
  const lines=baseline.split("\n").filter(line=>line.trim().startsWith("["+JSON.stringify(row[0])+","));assert.equal(lines.length,1,fail+" BASE row");
  return{key:row[0],old:lines[0],new:"    ["+row.map(v=>JSON.stringify(v)).join(", ")+"],",oldRow:JSON.parse(lines[0].trim().replace(/,$/,"")),newRow:row};
});
assert.equal(resizePlainChanges.length,33);
export function resizePlainHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);
  const keys=resizePlainChanges.map(e=>count(source,'["'+e.key+'",'));
  if(keys.every(n=>n===0))return source;
  assert.ok(keys.every(n=>n===1),fail+" missing/duplicate row");
  const old=resizePlainChanges.every(e=>count(source,e.old)===1),next=resizePlainChanges.every(e=>count(source,e.new)===1);
  assert.ok(old||next,fail+" partial/unknown values");
  const start=source.indexOf("  const IMAGE_OPERATION_COPY_ROWS = ["),end=source.indexOf("\n  ];",start);
  assert.ok(start>=0&&end>start,fail+" array owner");
  const ordered=resizePlainChanges.toSorted((a,b)=>baseline.indexOf(a.old)-baseline.indexOf(b.old));
  const positions=ordered.map(e=>source.slice(start,end).indexOf(e[next?"new":"old"]));
  assert.ok(positions.every((n,i)=>n>=0&&(i===0||n>positions[i-1])),fail+" detached/reordered row");
  if(old)return source;
  return resizePlainChanges.reduce((text,e)=>text.replace(e.new,()=>e.old),source);
}
export function resizePlainHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");
  const index=locales.indexOf(locale)+1,keys=resizePlainChanges.map(e=>"imageOperationUi."+e.key);
  const found=keys.map(key=>entries.filter(([name])=>name===key));
  if(found.every(v=>v.length===0))return entries;
  assert.ok(found.every(v=>v.length===1),fail+" missing/duplicate key");
  const old=found.every((v,i)=>v[0][1]===resizePlainChanges[i].oldRow[index]),next=found.every((v,i)=>v[0][1]===resizePlainChanges[i].newRow[index]);
  assert.ok(old||next,fail+" partial/unknown catalogue values");
  if(old)return entries;
  return entries.map(([key,value])=>{const at=keys.indexOf(key);return[key,at<0?value:resizePlainChanges[at].oldRow[index]];});
}
