import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {resizeResultLabelHistoricalI18nSource as inverse,resizeResultLabelHistoricalSnapshot as snapshot} from "./helpers/image-resize-result-label-snapshot.mjs";
import {historyStateCopyHistoricalI18nSource} from "./helpers/image-history-state-copy-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-result-label-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const file="static/portal/portal-i18n.js",base="6a407cfcd0345be0b83c15b119c5e5b68bd3da05",lf=value=>value.replace(/\r\n/g,"\n");
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6})),current=historyStateCopyHistoricalI18nSource(lf(fs.readFileSync(file,"utf8")));
test("Physical i18n equals exactly two accepted result labels with every outside byte unchanged",()=>{
  assert.equal(fixture.proposal.specId,"IMAGE-RESIZE-PLAIN-RESULT-COPY-20261118");assert.equal(fixture.review.conversation,"fbea6cea-423c-4d42-8769-f1a05f865c24");
  let expected=before;for(const edit of edits){assert.equal(edit.file,file);assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Result-label inverse rejects partial changed duplicate detached reordered rows and preserves outside text",()=>{
  const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(current.replace(edit.new,edit.old)),/Unreviewed Resize result labels/);
    assert.throws(()=>inverse(current+"\n"+edit.new),/Unreviewed Resize result labels/);
    assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("result.","result.UNKNOWN."))),/Unreviewed Resize result labels/);
    assert.throws(()=>inverse(current.replace(edit.new,"")+"\n"+edit.new),/Unreviewed Resize result labels/);
  }
  const swapped=current.replace(edits[0].new,"@@OWNED@@").replace(edits[1].new,edits[0].new).replace("@@OWNED@@",edits[1].new);assert.throws(()=>inverse(swapped),/Unreviewed Resize result labels/);
});
test("Finite result catalogue inverse changes only two exact values and rejects partial mixed unknown duplicates",()=>{
  for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
    const rows=edits.map(edit=>({old:JSON.parse(edit.old.trim().replace(/,$/,"")),next:JSON.parse(edit.new.trim().replace(/,$/,""))}));
    const old=[["customer","literal"],...rows.map(row=>["imageOperationUi."+row.old[0],row.old[index]])],next=[old[0],...rows.map(row=>["imageOperationUi."+row.next[0],row.next[index]])];
    assert.deepEqual(snapshot(old,locale),old);assert.deepEqual(snapshot(next,locale),old);assert.deepEqual(snapshot([old[0]],locale),[old[0]]);
    for(const bad of [next.slice(0,-1),[...next,next[1]],next.map((row,i)=>i===1?old[i]:row),next.map((row,i)=>i===1?[row[0],"UNKNOWN"]:row)])assert.throws(()=>snapshot(bad,locale),/Unreviewed Resize result labels/);
  }
});
