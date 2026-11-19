import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
// Historical-comparator leaf only; current renderers always receive physical sources.
const fail="Unreviewed History technical cleanup",count=(text,part)=>text.split(part).length-1;
const pins=[
  ["image-history-technical-notes-reviewed","4d5c30122cef5ba9098751350ae44084d7a2e71473d7ed814cceb1c0cbef99ab","IMAGE-HISTORY-TECHNICAL-NOTES-20261119","R1","83f531bf-39ef-4e4b-baf1-a76596166a52",1],
  ["image-history-state-meta-reviewed","d2960de5d5e263271fd2b9eb765abe25ccdbe6f421a9ab05813c5df51b20982b","IMAGE-HISTORY-STATE-META-20261119","R2","d43b069b-76b4-41e8-8e4c-f46bc0899e8d",3]
];
const edits=pins.flatMap(([name,wanted,spec,revision,conversation,total])=>{
  const raw=fs.readFileSync(new URL("../fixtures/"+name+".json",import.meta.url));assert.equal(createHash("sha256").update(raw).digest("hex"),wanted,fail+" authority hash");
  const value=JSON.parse(raw);assert.equal(value.review.schemaValid,true);assert.equal(value.review.proposalExact,true);assert.equal(value.review.specId,spec);assert.equal(value.review.conversation,conversation);assert.equal(value.proposal.specId,spec);assert.equal(value.proposal.revision,revision);assert.equal(value.proposal.changes.length,total);
  for(const edit of value.proposal.changes){assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);}return value.proposal.changes;
});
export function historyTechnicalCleanupHistoricalPortalSource(source){
  assert.equal(typeof source,"string",fail);
  const owner="  function renderImageOperationHistory(",boundary="  function renderImageBrandOverlay(page, context) {";
  if(!source.includes(owner))return source;
  assert.equal(count(source,owner),1,fail+" owner");assert.equal(count(source,boundary),1,fail+" boundary");
  const phases=edits.map(edit=>{const old=count(source,edit.old),next=count(source,edit.new)-old*count(edit.old,edit.new);assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/unknown/duplicate");return next;});
  assert.ok(phases.every(n=>n===0)||phases.every(n=>n===1),fail+" mixed four-edit set");
  const next=phases[0]===1,start=source.indexOf(owner),end=source.indexOf(boundary,start);
  assert.ok(end>start,fail+" owner order");assert.equal(source.indexOf("\n  function ",start+owner.length)+1,end,fail+" immediate next-function boundary");
  const notes=next?edits[0].new:edits[0].old,point=source.indexOf(notes);assert.ok(point>start&&point<end,fail+" notes owner");assert.equal(point+notes.length,end+boundary.length,fail+" suffix");
  let previous=start;for(const edit of edits.slice(1)){const text=next?edit.new:edit.old,point=source.indexOf(text);assert.ok(point>previous&&point+text.length<end,fail+" detached/reordered state");previous=point;}
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
