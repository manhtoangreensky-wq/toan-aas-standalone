import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-enhance-help-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"8e6babf0753c2a4455b3264cedd3efddef99e11ca9e411621e835e8e9ec03c3a");
const fixture=JSON.parse(raw),edits=fixture.proposal.changes;
assert.equal(fixture.review.proposalExact,true);assert.equal(edits.length,6);
const rows=edits.map(edit=>({...edit,oldRow:JSON.parse(edit.old.trim().replace(/,$/,"")),newRow:JSON.parse(edit.new.trim().replace(/,$/,""))}));
const fail="Unreviewed Image Enhance help",marker="  const IMAGE_OPERATION_COPY_ROWS = [",count=(source,part)=>source.split(part).length-1;
export function imageEnhanceHelpHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);
  if(!source.includes(marker)){
    assert.ok(rows.every(row=>count(source,row.old)===0&&count(source,row.new)===0),fail+" detached");
    return source;
  }
  assert.equal(count(source,marker),1,fail+" duplicate owner");
  const start=source.indexOf(marker),end=source.indexOf("\n  ];",start);
  assert.ok(end>start,fail+" owner");
  const part=source.slice(start,end),old=rows.every(row=>count(part,row.old)===1),next=rows.every(row=>count(part,row.new)===1);
  assert.ok(old||next,fail+" partial/changed");
  const positions=rows.map(row=>part.indexOf(row[next?"new":"old"]));
  assert.ok(positions.every((value,index)=>value>=0&&(index===0||value>positions[index-1])),fail+" order");
  for(const row of rows){
    assert.equal(count(source,row.old),next?0:1,fail+" detached/duplicate OLD");
    assert.equal(count(source,row.new),next?1:0,fail+" detached/duplicate NEW");
  }
  if(old)return source;
  let result=source;
  for(const row of rows)result=result.replace(row.new,()=>row.old);
  return result;
}
export function imageEnhanceHelpHistoricalSnapshot(entries,locale){
  const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");
  const keys=rows.map(row=>"imageOperationUi."+row.key),found=keys.map(key=>entries.filter(([name])=>name===key));
  if(found.every(value=>value.length===0))return entries;
  assert.ok(found.every(value=>value.length===1),fail+" missing/duplicate catalogue");
  const old=found.every((value,at)=>value[0][1]===rows[at].oldRow[index]),next=found.every((value,at)=>value[0][1]===rows[at].newRow[index]);
  assert.ok(old||next,fail+" partial/unknown catalogue");if(old)return entries;
  return entries.map(([key,value])=>{const at=keys.indexOf(key);return[key,at<0?value:rows[at].oldRow[index]];});
}
