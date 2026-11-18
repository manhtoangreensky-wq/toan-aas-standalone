import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-enhance-headings-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"8d17d4110028c6a2cd00f50bf3852e3419db70346894caffae87cf1367bc8755");
const fixture=JSON.parse(raw),edits=fixture.proposal.changes,fail="Unreviewed Enhance plain headings",count=(source,part)=>source.split(part).length-1;
assert.equal(fixture.review.proposalExact,true);assert.equal(edits.length,6);
const rows=edits.map(edit=>{assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);const old=JSON.parse(edit.old.trim().replace(/,$/,"")),next=JSON.parse(edit.new.trim().replace(/,$/,""));assert.equal(old[0],next[0]);return{key:old[0],old,next};});
export function enhanceHeadingsHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);
  if(rows.every(row=>!source.includes('["'+row.key+'",')))return source;
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const old=phases.every(([a,b])=>a===1&&b===0),next=phases.every(([a,b])=>a===0&&b===1);
  assert.ok(old||next,fail+" partial/unknown/duplicate rows");
  const start=source.indexOf("  const IMAGE_OPERATION_COPY_ROWS = ["),end=source.indexOf("\n  ];",start);
  assert.ok(start>=0&&end>start,fail+" catalogue owner");let previous=start;
  for(const edit of edits){const point=source.indexOf(next?edit.new:edit.old);assert.ok(point>previous&&point<end,fail+" moved/reordered row");previous=point;}
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);
  return result;
}
export function enhanceHeadingsHistoricalSnapshot(entries,locale){
  const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");
  const keys=rows.map(row=>"imageOperationUi."+row.key),owned=entries.filter(([key])=>keys.includes(key));
  if(!owned.length)return entries;assert.equal(owned.length,6,fail+" partial/duplicate catalogue");
  const values=rows.map((row,i)=>{const found=owned.filter(([key])=>key===keys[i]);assert.equal(found.length,1,fail+" duplicate key");return found[0][1];});
  const old=values.every((value,i)=>value===rows[i].old[index]),next=values.every((value,i)=>value===rows[i].next[index]);
  assert.ok(old||next,fail+" mixed/unknown catalogue");if(old)return entries;
  const prior=new Map(rows.map((row,i)=>[keys[i],row.old[index]]));
  return entries.map(([key,value])=>prior.has(key)?[key,prior.get(key)]:[key,value]);
}
