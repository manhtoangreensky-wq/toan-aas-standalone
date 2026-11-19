import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {historyTechnicalCleanupHistoricalPortalSource as inverse} from "./helpers/image-history-technical-cleanup-snapshot.mjs";
const file="static/portal/portal.js",base="bb3c5657845e5eabc495706a20148230386b699c",lf=value=>value.replace(/\r\n/g,"\n");
const names=["image-history-technical-notes-reviewed","image-history-state-meta-reviewed"],edits=names.flatMap(name=>JSON.parse(fs.readFileSync(new URL("./fixtures/"+name+".json",import.meta.url))).proposal.changes);
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6})),current=lf(fs.readFileSync(file,"utf8"));
test("Physical portal equals only four accepted History technical removals, every outside byte held",()=>{
  assert.equal(edits.length,4);let expected=before;for(const edit of edits){assert.equal(edit.file,file);assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Finite four-removal leaf rejects mixed unknown duplicate detached reordered edits and keeps customer bytes",()=>{
  const prefix="\r\n/* CUSTOMER Trạng thái tích hợp Facebook TikTok */\r\n",suffix="\r\n/* unrelated */";
  assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(before.replace(edit.old,()=>edit.new)),/Unreviewed History technical cleanup/);
    assert.throws(()=>inverse(before.replace(edit.old,"UNKNOWN")),/Unreviewed History technical cleanup/);
    assert.throws(()=>inverse(before+"\n"+edit.old),/Unreviewed History technical cleanup/);
    assert.throws(()=>inverse(before.replace(edit.old,"")+"\n"+edit.old),/Unreviewed History technical cleanup/);
  }
  const[a,b]=edits.slice(1,3),marker="@@OWNED@@";assert.throws(()=>inverse(before.replace(a.old,marker).replace(b.old,()=>a.old).replace(marker,()=>b.old)),/Unreviewed History technical cleanup/);
  const unknown=current.replace("  function renderImageBrandOverlay(page, context) {","  function UNKNOWN(page, context) {");assert.throws(()=>inverse(unknown),/Unreviewed History technical cleanup/);
});
