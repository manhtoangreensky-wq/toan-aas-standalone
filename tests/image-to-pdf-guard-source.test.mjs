import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageToPdfGuardHistoricalPortalSource as inverse} from "./helpers/image-to-pdf-guard-snapshot.mjs";
import {imageToPdfMetaHistoricalPortalSource} from "./helpers/image-to-pdf-meta-snapshot.mjs";
const authority=JSON.parse(fs.readFileSync(new URL("./fixtures/image-to-pdf-guard-reviewed.json",import.meta.url),"utf8"));
const [edit]=authority.proposal.changes,base="6c8e2b227ba635d81dc713f6c25c77d260002e61";
const lf=value=>value.replace(/\r\n/g,"\n");
const source=imageToPdfMetaHistoricalPortalSource(lf(fs.readFileSync(edit.file,"utf8")));
test("Image-to-PDF source equals exactly one reviewed guarded return and preserves every outside byte",()=>{
  const before=lf(execFileSync("git",["show",base+":"+edit.file],{encoding:"utf8",maxBuffer:12e6}));
  assert.equal(before.split(edit.old).length-1,1);
  assert.equal(source,before.replace(edit.old,()=>edit.new));
  assert.equal(inverse(source),before);assert.equal(inverse(before),before);
});
test("Image-to-PDF historical inverse rejects unknown/duplicate/detached returns and preserves customer bytes",()=>{
  const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside content */";
  assert.equal(inverse(prefix+source+suffix),prefix+inverse(source)+suffix);
  assert.equal(inverse(prefix),prefix);
  assert.throws(()=>inverse(edit.new),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse('/* portal-page portal-image-to-pdf */'),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse(source+"\n"+edit.new),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse(source.replace(edit.new,edit.new.replace("<h2>","<h2 data-unknown>"))),/Unreviewed Image-to-PDF guard/);
  assert.throws(()=>inverse(source.replace(edit.new,"")+"\n"+edit.new),/Unreviewed Image-to-PDF guard/);
});
