import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageEnhanceHelpHistoricalI18nSource as inverse,imageEnhanceHelpHistoricalSnapshot as snapshot} from "./helpers/image-enhance-help-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-enhance-help-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const base="39a3fb9ebda84f5fed7b582839040ada54b1cc0e",file="static/portal/portal-i18n.js",lf=value=>value.replace(/\r\n/g,"\n");
const source=lf(fs.readFileSync(file,"utf8"));
test("Enhance help source equals exactly six reviewed rows with every outside byte unchanged",()=>{
  const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6}));let expected=before;
  for(const edit of edits){assert.equal(edit.count,1);assert.equal(edit.file,file);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(source,expected);assert.equal(inverse(source),before);assert.equal(inverse(before),before);
});
test("Enhance finite inverses reject partial/changed/duplicate/detached rows and keep unknown customer bytes",()=>{
  const [first,second]=edits,prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
  assert.equal(inverse(prefix+source+suffix),prefix+inverse(source)+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(source.replace(edit.new,edit.old)),/Unreviewed Image Enhance help/);
    assert.throws(()=>inverse(source.replace(edit.new,"")),/Unreviewed Image Enhance help/);
    assert.throws(()=>inverse(source.replace(edit.new,edit.new.replace('],',' ,"UNKNOWN"],'))),/Unreviewed Image Enhance help/);
  }
  assert.throws(()=>inverse(source+"\n"+first.new),/Unreviewed Image Enhance help/);
  assert.throws(()=>inverse(source.replace(first.new,"")+"\n"+first.new),/Unreviewed Image Enhance help/);
  assert.throws(()=>inverse(source.replace(first.new,"@@ROW@@").replace(second.new,first.new).replace("@@ROW@@",second.new)),/Unreviewed Image Enhance help/);
  for(const[at,locale]of ["vi","en","zh"].entries()){
    const rows=edits.map(edit=>JSON.parse(edit.new.trim().replace(/,$/,""))),old=edits.map(edit=>JSON.parse(edit.old.trim().replace(/,$/,"")));
    const entries=[["CUSTOMER","Facebook TikTok"],...rows.map(row=>["imageOperationUi."+row[0],row[at+1]])];
    assert.deepEqual(snapshot(entries,locale),[entries[0],...old.map(row=>["imageOperationUi."+row[0],row[at+1]])]);
    assert.throws(()=>snapshot(entries.slice(0,-1),locale),/Unreviewed Image Enhance help/);
  }
});
