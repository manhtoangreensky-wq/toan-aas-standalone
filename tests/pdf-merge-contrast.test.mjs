import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {pdfMergeContrastHistoricalCss as inverse} from "./helpers/pdf-merge-contrast-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-merge-contrast-reviewed.json",import.meta.url),"utf8"));
assert.match(fixture.base,/^[a-f0-9]{40}$/,"Bind the delivered full BASE before any git show");
const file="static/portal/portal-theme.css",edit=fixture.changes[0],lf=value=>value.replace(/\r\n/g,"\n");
const raw=lf(fs.readFileSync(file,"utf8")),before=lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:12e6}));
const hash=value=>createHash("sha256").update(value).digest("hex"),count=(value,part)=>value.split(part).length-1;
const addition='\n\n/* Keep PDF merge field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-merge .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-merge .portal-field-help {\n  color: var(--portal-muted);\n}';
function once(value,old,next){assert.equal(count(value,old),1,"Unique reviewed Merge contrast slot");return value.replace(old,()=>next);}
test("actual raw CSS contains exactly the reviewed Merge foreground addition; missing addition is RED",()=>{
  assert.equal(fixture.changes.length,1);assert.equal(count(before,edit.old),1);assert.equal(count(raw,edit.new),1);
  assert.equal(edit.new,edit.old+addition);assert.equal(raw,once(before,edit.old,edit.new));assert.equal(inverse(raw),before);
  assert.equal(hash(before),fixture.binding.baselineTheme);assert.equal(hash(raw),fixture.binding.candidateTheme);
});
test("only two Merge light text selectors and semantic foreground declarations are added",()=>{
  assert.equal((addition.match(/html:not\(\[data-portal-theme="dark"\]\)/g)||[]).length,2);
  assert.equal((addition.match(/color:/g)||[]).length,2);assert.ok(addition.includes("color: var(--portal-text);"));assert.ok(addition.includes("color: var(--portal-muted);"));
  assert.doesNotMatch(addition,/!important|font|line-height|margin|padding|gap|opacity|animation|transition|transform|background|display|position|width|height|visibility/);
  assert.equal((addition.match(/\.portal-page\.portal-pdf-merge /g)||[]).length,2);
});
test("all font16, desktop, controls, dark and outside stylesheet bytes remain unchanged",()=>{
  const start=before.indexOf(edit.old);assert.ok(start>=0);assert.equal(raw.slice(0,start),before.slice(0,start));
  assert.equal(raw.slice(start+edit.new.length),before.slice(start+edit.old.length));assert.equal(raw.length,before.length+addition.length);
  assert.equal(once(raw,edit.new,edit.old),before);
});
test("portal and locale catalogue stay byte-identical to delivered BASE",()=>{
  for(const[file,key]of [["static/portal/portal.js","candidatePortal"],["static/portal/portal-i18n.js","candidateI18n"]]){
    const current=lf(fs.readFileSync(file,"utf8")),base=lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:12e6}));
    assert.equal(current,base);assert.equal(hash(current),fixture.binding[key]);
  }
});
test("finite inverse rejects partial, changed, duplicated, detached or residual rules",()=>{
  for(const mutation of [
    edit.new.replace("var(--portal-text)","red"),edit.new.replace("var(--portal-muted)","black"),
    edit.new.replace('html:not([data-portal-theme="dark"])','html[data-portal-theme="dark"]'),
    edit.new.replace("color: var(--portal-muted);","color: var(--portal-muted); font-size: 20px;"),
    edit.old+addition.slice(0,addition.indexOf("\nhtml:not",100)),edit.old+"\n/* UNKNOWN */"+addition
  ])assert.throws(()=>inverse(once(raw,edit.new,mutation)),/Unreviewed Merge contrast CSS/);
  assert.throws(()=>inverse(raw+"\n"+edit.new),/Unreviewed Merge contrast CSS/);
  assert.throws(()=>inverse(raw+"\n"+addition),/Unreviewed Merge contrast CSS/);
});
test("old historical styles and unknown outside bytes including CRLF remain visible to comparisons",()=>{
  const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n.other { color: rebeccapurple; }\r\n";
  assert.equal(inverse(before),before);assert.equal(inverse(prefix),prefix);assert.equal(inverse(prefix+raw+suffix),prefix+before+suffix);
  assert.notEqual(inverse(raw+suffix),before);assert.equal(inverse(""),"");
});
// Source scope only; numeric foreground/background paint-chain contrast and geometry are separate native gates.
