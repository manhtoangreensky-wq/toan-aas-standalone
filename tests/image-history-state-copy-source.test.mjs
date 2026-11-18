import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {historyStateCopyHistoricalI18nSource as inverse,historyStateCopyHistoricalSnapshot as snapshot} from "./helpers/image-history-state-copy-snapshot.mjs";
import {historyCustomerCleanupHistoricalSource} from "./helpers/image-history-customer-cleanup-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-history-state-copy-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const file="static/portal/portal-i18n.js",base="d0a2ba128df320230141a65da2a455490f599294",lf=value=>value.replace(/\r\n/g,"\n");
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6})),current=historyCustomerCleanupHistoricalSource(lf(fs.readFileSync(file,"utf8")),file);
test("Physical i18n equals exactly six accepted History state rows with every outside byte unchanged",()=>{
  assert.equal(fixture.proposal.specId,"IMAGE-HISTORY-PLAIN-STATE-COPY-20261118");assert.equal(fixture.review.conversation,"c48dbd20-b769-452f-9ecb-ed98578c853d");
  let expected=before;for(const edit of edits){assert.equal(edit.file,file);assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("History state inverse rejects partial changed duplicate detached reordered rows and preserves outside text",()=>{
  const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(current.replace(edit.new,edit.old)),/Unreviewed History state copy/);
    assert.throws(()=>inverse(current+"\n"+edit.new),/Unreviewed History state copy/);
    assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("history.","history.UNKNOWN."))),/Unreviewed History state copy/);
    assert.throws(()=>inverse(current.replace(edit.new,"")+"\n"+edit.new),/Unreviewed History state copy/);
  }
  const swapped=current.replace(edits[0].new,"@@OWNED@@").replace(edits[1].new,edits[0].new).replace("@@OWNED@@",edits[1].new);assert.throws(()=>inverse(swapped),/Unreviewed History state copy/);
});
test("Finite History state catalogue inverse owns six exact values and rejects partial mixed unknown duplicates",()=>{
  for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
    const rows=edits.map(edit=>({old:JSON.parse(edit.old.trim().replace(/,$/,"")),next:JSON.parse(edit.new.trim().replace(/,$/,""))}));
    const old=[["customer","literal"],...rows.map(row=>["imageOperationUi."+row.old[0],row.old[index]])],next=[old[0],...rows.map(row=>["imageOperationUi."+row.next[0],row.next[index]])];
    assert.deepEqual(snapshot(old,locale),old);assert.deepEqual(snapshot(next,locale),old);assert.deepEqual(snapshot([old[0]],locale),[old[0]]);
    for(const bad of [next.slice(0,-1),[...next,next[1]],next.map((row,i)=>i===1?old[i]:row),next.map((row,i)=>i===1?[row[0],"UNKNOWN"]:row)])assert.throws(()=>snapshot(bad,locale),/Unreviewed History state copy/);
  }
});
