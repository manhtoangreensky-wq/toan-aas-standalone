import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {resizeSubtitleHistoricalPortalSource as inverse} from "./helpers/image-resize-subtitle-snapshot.mjs";
const raw=fs.readFileSync(new URL("./fixtures/image-resize-subtitle-reviewed.json",import.meta.url)),fixture=JSON.parse(raw),edits=fixture.proposal.changes;
const base="979b80d22a90368ec97547937e219ccbd3a02deb",file="static/portal/portal.js",lf=value=>value.replace(/\r\n/g,"\n");
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6})),current=lf(fs.readFileSync(file,"utf8"));
test("Resize subtitle source equals exactly the two accepted inline substitutions with every outside byte unchanged",()=>{
  assert.equal(fixture.proposal.specId,"IMAGE-RESIZE-CUSTOM-SUBTITLE-20261118");assert.equal(fixture.review.conversation,"c9f5fcd9-c2aa-4200-a99c-0bd07455af77");
  let expected=before;
  for(const edit of edits){assert.equal(edit.file,file);assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Resize subtitle inverse rejects partial, duplicated, changed and cross-function edits and keeps unknown/customer bytes",()=>{
  const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
  assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);assert.equal(inverse(prefix),prefix);
  for(const edit of edits){
    assert.throws(()=>inverse(current.replace(edit.new,edit.old)),/Unreviewed Resize custom subtitle/);
    assert.throws(()=>inverse(current+"\n"+edit.new),/Unreviewed Resize custom subtitle/);
    assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("field.resize.preset.custom","field.resize.preset.UNKNOWN"))),/Unreviewed Resize custom subtitle/);
    assert.throws(()=>inverse(current.replace(edit.new,edit.old)+"\n"+edit.new),/Unreviewed Resize custom subtitle/);
  }
  const unknown=current.replace('common("checking", "Đang kiểm tra")','common("checking", "CUSTOMER outside")');
  assert.equal(inverse(unknown),before.replace('common("checking", "Đang kiểm tra")','common("checking", "CUSTOMER outside")'));
  const swapped=current.replace(edits[0].new,"@@OWNED@@").replace(edits[1].new,edits[0].new).replace("@@OWNED@@",edits[1].new);
  assert.throws(()=>inverse(swapped),/Unreviewed Resize custom subtitle/);
});
