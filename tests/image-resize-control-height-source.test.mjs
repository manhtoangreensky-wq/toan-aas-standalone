import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {resizeControlHeightHistoricalThemeSource as inverse} from "./helpers/image-resize-control-height-snapshot.mjs";
import {enhanceStepColorHistoricalThemeSource} from "./helpers/image-enhance-step-color-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-control-height-reviewed.json",import.meta.url),"utf8"));
const file="static/portal/portal-theme.css",current=enhanceStepColorHistoricalThemeSource(fs.readFileSync(file,"utf8").replace(/\r\n/g,"\n"));
const before=execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:2e6}).replace(/\r\n/g,"\n");
const hash=value=>createHash("sha256").update(value).digest("hex"),[edit]=fixture.changes;
test("Resize height style equals the one worker addition and every other theme byte stays BASE",()=>{
  assert.equal(hash(before),fixture.baselineThemeLfSha256);
  assert.equal(hash(current),fixture.candidateThemeLfSha256);
  assert.equal(before.split(edit.old).length-1,1);
  assert.equal(current,before.replace(edit.old,()=>edit.new));
  assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Resize height inverse rejects duplicate/partial/changed/moved rule and retains outside bytes",()=>{
  const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* Facebook TikTok customer */";
  assert.equal(inverse(prefix+current+suffix),prefix+before+suffix);
  assert.throws(()=>inverse(current+"\n"+edit.new),/Unreviewed Resize control height/);
  assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("align-content: start;","align-content: center;"))),/Unreviewed Resize control height/);
  const addition=edit.new.slice(edit.old.length);
  assert.throws(()=>inverse(current.replace(edit.new,edit.old)+addition),/Unreviewed Resize control height/);
  const changed=current.replace(edit.new,edit.new.replace("var(--portal-text)","var(--UNKNOWN)"));
  assert.equal(inverse(changed),before.replace(edit.old,edit.old.replace("var(--portal-text)","var(--UNKNOWN)")),
    "Retain a protected older-rule mutation for its original comparator rather than mask it");
  assert.equal(inverse(current+"\n"+edit.old),before+"\n"+edit.old,
    "An older-rule duplicate remains visible to its original comparator");
});
