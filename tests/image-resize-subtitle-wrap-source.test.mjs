import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {resizeSubtitleWrapHistoricalThemeSource as inverse} from "./helpers/image-resize-subtitle-wrap-snapshot.mjs";
import {vaultHintContrastHistoricalCss} from "./helpers/vault-hint-contrast-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-subtitle-wrap-reviewed.json",import.meta.url),"utf8")),[edit]=fixture.proposal.changes;
const base="979b80d22a90368ec97547937e219ccbd3a02deb",file="static/portal/portal-theme.css",lf=value=>value.replace(/\r\n/g,"\n");
// Source-only historical comparator copy; current CSS acceptance is independently pinned by the Vault hint suite.
const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:2e6})),current=vaultHintContrastHistoricalCss(lf(fs.readFileSync(file,"utf8")),file);
const baseCss=lf(execFileSync("git",["show",base+":static/portal/portal.css"],{encoding:"utf8",maxBuffer:2e6}));
assert.equal(before.split(edit.old).length-1,1);const expected=before.replace(edit.old,()=>edit.new);
test("Actual theme equals one accepted subtitle wrapping addition with every outside byte unchanged",()=>{
  assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
});
test("Wrapping authority scopes exactly two image routes and changes only four text overflow properties",()=>{
  assert.equal(fixture.proposal.specId,"IMAGE-RESIZE-SUBTITLE-READABILITY-20261118");assert.equal(fixture.review.conversation,"fd4ec668-6b48-4bbf-8726-848d3c2f37ee");assert.equal(fixture.proposal.revision,"R1");
  assert.equal(edit.count,1);assert.equal(edit.file,file);assert.equal(edit.new,edit.old+'\n\n/* Keep image result subtitles readable in Resize and history. */\n.portal-page:is(.portal-image-resize, .portal-image-operation-history) .portal-document-operation-card .portal-document-operation-title .portal-card-subtitle {\n  white-space: normal;\n  overflow-wrap: anywhere;\n  overflow: visible;\n  text-overflow: clip;\n}');
  assert.doesNotMatch(edit.new.slice(edit.old.length),/!important|opacity|font|display|width|height|position|transition|animation/);
  assert.ok(baseCss.includes(".portal-document-operation-title .portal-card-title, .portal-document-operation-title .portal-card-subtitle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }"));
});
test("Finite wrap inverse rejects changed partial duplicated and detached rules while retaining unknown outside text",()=>{
  const addition=edit.new.slice(edit.old.length),prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
  assert.equal(inverse(prefix+expected+suffix),prefix+before+suffix);
  for(const mutation of [expected+"\n"+addition,expected.replace(addition,addition.replace("normal","nowrap")),expected.replace(addition,addition.replace("anywhere","normal")),expected.replace(edit.new,edit.old)+"\n"+addition])assert.throws(()=>inverse(mutation),/Unreviewed Resize subtitle wrapping/);
  assert.equal(inverse(expected+suffix),before+suffix);assert.equal(inverse(before+suffix),before+suffix);
});
