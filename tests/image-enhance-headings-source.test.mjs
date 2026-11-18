import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {enhanceHeadingsHistoricalI18nSource as inverse,enhanceHeadingsHistoricalSnapshot as snapshot} from "./helpers/image-enhance-headings-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-enhance-headings-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const file="static/portal/portal-i18n.js",base="be8015ad908a87535cb644243d43ba81f37ffdcc",lf=value=>value.replace(/\r\n/g,"\n");
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6})),current=lf(fs.readFileSync(file,"utf8"));
test("Physical i18n equals exactly six accepted heading rows with every outside byte unchanged",()=>{
  let expected=before;
  for(const edit of edits){assert.equal(edit.file,file);assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Heading source inverse rejects partial changed duplicate detached reordered rows and preserves outside text",()=>{
  const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
  assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(current.replace(edit.new,edit.old)),/Unreviewed Enhance plain headings/);
    assert.throws(()=>inverse(current+"\n"+edit.new),/Unreviewed Enhance plain headings/);
    assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("enhance.","enhance.UNKNOWN."))),/Unreviewed Enhance plain headings/);
    assert.throws(()=>inverse(current.replace(edit.new,"")+"\n"+edit.new),/Unreviewed Enhance plain headings/);
  }
  const swapped=current.replace(edits[0].new,"@@OWNED@@").replace(edits[1].new,edits[0].new).replace("@@OWNED@@",edits[1].new);
  assert.throws(()=>inverse(swapped),/Unreviewed Enhance plain headings/);
});
test("Finite catalogue inverse changes only six exact owned values and rejects partial mixed unknown duplicates",()=>{
  for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
    const rows=edits.map(edit=>({old:JSON.parse(edit.old.trim().replace(/,$/,"")),next:JSON.parse(edit.new.trim().replace(/,$/,""))}));
    const old=[["customer","literal"],...rows.map(row=>["imageOperationUi."+row.old[0],row.old[index]])],next=[old[0],...rows.map(row=>["imageOperationUi."+row.next[0],row.next[index]])];
    assert.deepEqual(snapshot(old,locale),old);assert.deepEqual(snapshot(next,locale),old);assert.deepEqual(snapshot([old[0]],locale),[old[0]]);
    assert.throws(()=>snapshot(next.slice(0,-1),locale),/Unreviewed Enhance plain headings/);
    assert.throws(()=>snapshot([...next,next[1]],locale),/Unreviewed Enhance plain headings/);
    assert.throws(()=>snapshot(next.map((row,i)=>i===1?old[i]:row),locale),/Unreviewed Enhance plain headings/);
    assert.throws(()=>snapshot(next.map((row,i)=>i===1?[row[0],"UNKNOWN"]:row),locale),/Unreviewed Enhance plain headings/);
  }
});
