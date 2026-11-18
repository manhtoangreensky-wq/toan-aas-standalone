import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {enhanceStepColorHistoricalThemeSource as inverse} from "./helpers/image-enhance-step-color-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-enhance-step-color-reviewed.json",import.meta.url),"utf8"));
const [edit]=fixture.proposal.changes,file="static/portal/portal-theme.css",base="c1fdd4bf35c8563d8dd15dc27619022d3e1b7350";
const lf=value=>value.replace(/\r\n/g,"\n"),before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:2e6}));
assert.equal(before.split(edit.old).length-1,1);
const expected=before.replace(edit.old,()=>edit.new),current=lf(fs.readFileSync(file,"utf8"));
test("Actual theme equals the sole reviewed light Enhance step color addition and preserves every outside byte",()=>{
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Color authority is one exact light/default-light scoped rule without layout, font, dark or other-route changes",()=>{
  assert.equal(fixture.review.conversation,"0ec097d5-5b46-48d8-9147-dfec771bdc07");
  assert.equal(fixture.proposal.specId,"IMAGE-ENHANCE-LIGHT-STEP-COLOR-20261118");assert.equal(fixture.proposal.revision,"R1");
  assert.equal(fixture.review.tests,"NOT_RUN");assert.equal(fixture.review.newFailures,"UNKNOWN");
  assert.equal(edit.new,edit.old+'\n\n/* Keep Enhance step text readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-image-enhance .portal-project-steps strong,\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-image-enhance .portal-project-steps span {\n  color: var(--portal-ink);\n}');
});
test("Finite color inverse rejects changed, partial, duplicate and detached additions without masking outside bytes",()=>{
  // Expected text is used only to test the inverse, never as the acceptance renderer/current source.
  const addition=edit.new.slice(edit.old.length),prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
  assert.equal(inverse(prefix+expected+suffix),prefix+before+suffix);
  assert.throws(()=>inverse(expected+"\n"+addition),/Unreviewed Enhance step color/);
  assert.throws(()=>inverse(expected.replace(addition,addition.replace("var(--portal-ink)","var(--UNKNOWN)"))),/Unreviewed Enhance step color/);
  assert.throws(()=>inverse(expected.replace(addition,addition.replace(/strong,\n/,"strong {\n"))),/Unreviewed Enhance step color/);
  assert.throws(()=>inverse(expected.replace(edit.new,edit.old)+"\n"+addition),/Unreviewed Enhance step color/);
  const outside=expected.replace(edit.old,edit.old.replace("align-content: start","align-content: center"));
  assert.throws(()=>inverse(outside),/Unreviewed Enhance step color/,"Changed owner is not normalized");
  assert.equal(inverse(expected+suffix),before+suffix);
});
