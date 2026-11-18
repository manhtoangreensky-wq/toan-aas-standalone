import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-resize-subtitle-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"32a2ba6daa567d9e9aee9513de21fcaa3b509fb435f3e18715cedd3319332695");
const fixture=JSON.parse(raw),edits=fixture.proposal.changes,fail="Unreviewed Resize custom subtitle",count=(source,part)=>source.split(part).length-1;
assert.equal(fixture.review.proposalExact,true);assert.equal(edits.length,2);
const owners=["  function renderImageOperationCards(","  function renderImageHistoryOperationCards("],prefixes=["preset: `${fitLabel} · ${String(item.preset || ","preset: `${resizeLabel} · ${String(item.preset || "];
for(const edit of edits){assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);}
export function resizeSubtitleHistoricalPortalSource(source){
  assert.equal(typeof source,"string",fail);const found=edits.map(edit=>count(source,edit.new));
  if(found.every(value=>value===0)){
    for(const[index,edit]of edits.entries())if(source.includes(prefixes[index]))assert.equal(count(source,edit.old),1,fail+" changed/partial interpolation");
    return source;
  }
  assert.ok(found.every(value=>value===1),fail+" partial/duplicate substitution");
  let previous=-1;
  for(const[index,edit]of edits.entries()){
    const start=source.indexOf(owners[index]),end=source.indexOf("\n  function ",start+owners[index].length),point=source.indexOf(edit.new);
    assert.ok(start>=0&&end>start&&point>start&&point<end&&point>previous,fail+" misplaced/changed owner");
    assert.equal(count(source.slice(start,end),edit.old),0,fail+" old/new coexistence");previous=point;
  }
  let result=source;
  for(const edit of edits)result=result.replace(edit.new,()=>edit.old);
  for(const[index,edit]of edits.entries())assert.equal(count(result,edit.old),1,fail+" inverse count "+index);
  return result;
}
