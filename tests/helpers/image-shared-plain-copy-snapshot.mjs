import fs from "node:fs";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/image-shared-plain-copy-reviewed.json",import.meta.url),"utf8"));
const base=file=>execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n");
const priorI18n=base("static/portal/portal-i18n.js"),priorPortal=base("static/portal/portal.js");
const fail="Unreviewed Image shared plain copy",locales=["vi","en","zh"];
const count=(source,part)=>source.split(part).length-1;
function region(source,marker){
  const start=source.indexOf(marker),end=source.indexOf(marker.includes("const ")?"\n  ];":"\n  function ",start+marker.length);
  assert.ok(start>=0&&end>start,fail+" owner");
  return {start,end,text:source.slice(start,end)};
}
const arrayMarker="  const IMAGE_OPERATION_COPY_ROWS = [",resizeMarker="  function renderImageResize(";
const oldArray=region(priorI18n,arrayMarker).text;
export const imageSharedChanges=fixture.rows.map(row=>{
  const found=oldArray.split("\n").filter(line=>line.trim().startsWith("["+JSON.stringify(row[0])+","));
  assert.equal(found.length,1,fail+" BASE row");
  return {key:row[0],old:found[0],new:"    ["+row.map(value=>JSON.stringify(value)).join(", ")+"],",
    oldRow:JSON.parse(found[0].trim().replace(/,$/,"")),newRow:row};
});
const chipEdits=region(priorPortal,resizeMarker).text.split("\n").filter(line=>line.includes('<div class="portal-state-meta">')).map(old=>{
  const matches=[...old.matchAll(/<div class="portal-state-meta">(?:<span>[\s\S]*?<\/span>){3}<\/div>/g)];
  assert.equal(matches.length,1,fail+" BASE div");
  return {old,new:old.replace(matches[0][0],"")};
});
assert.equal(imageSharedChanges.length,21);assert.equal(chipEdits.length,2);
function sourceBack(source,marker,edits){
  assert.equal(typeof source,"string",fail);
  if(!source.includes(marker))return source;
  const part=region(source,marker),old=edits.every(edit=>count(part.text,edit.old)===1),next=edits.every(edit=>count(part.text,edit.new)===1);
  assert.ok(old||next,fail+" missing/partial/unknown/duplicate chunk");
  const owner=region(marker===arrayMarker?priorI18n:priorPortal,marker).text;
  const ordered=edits.toSorted((a,b)=>owner.indexOf(a.old)-owner.indexOf(b.old));
  const positions=ordered.map(edit=>part.text.indexOf(edit[next?"new":"old"]));
  assert.ok(positions.every((n,i)=>n>=0&&(i===0||n>positions[i-1])),fail+" reordered chunk");
  const original=marker===arrayMarker?priorI18n:priorPortal;
  for(const edit of edits){
    assert.equal(count(source,edit.old),count(original,edit.old)-(next?1:0),fail+" detached/duplicate OLD");
    assert.equal(count(source,edit.new),count(original,edit.new)+(next?1:0),fail+" detached/duplicate NEW");
  }
  if(old)return source;
  let value=part.text;
  for(const edit of edits)value=value.replace(edit.new,()=>edit.old);
  return source.slice(0,part.start)+value+source.slice(part.end);
}
export const imageSharedHistoricalI18nSource=source=>sourceBack(source,arrayMarker,imageSharedChanges);
export const imageSharedHistoricalPortalSource=source=>sourceBack(source,resizeMarker,chipEdits);
export function imageSharedHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");
  const index=locales.indexOf(locale)+1,keys=imageSharedChanges.map(edit=>"imageOperationUi."+edit.key);
  const found=keys.map(key=>entries.filter(([name])=>name===key));
  if(found.every(values=>values.length===0))return entries;
  assert.ok(found.every(values=>values.length===1),fail+" missing/duplicate key");
  const old=found.every((value,i)=>value[0][1]===imageSharedChanges[i].oldRow[index]);
  const next=found.every((value,i)=>value[0][1]===imageSharedChanges[i].newRow[index]);
  assert.ok(old||next,fail+" partial/unknown catalogue");
  if(old)return entries;
  return entries.map(([key,value])=>{const at=keys.indexOf(key);return [key,at<0?value:imageSharedChanges[at].oldRow[index]];});
}
