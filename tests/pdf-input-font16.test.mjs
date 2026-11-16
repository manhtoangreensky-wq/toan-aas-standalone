import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {pdfInputFont16HistoricalCss as historicalCss} from "./helpers/pdf-input-font16-snapshot.mjs";
import {pdfMergeFieldsHistoricalPortalSource,pdfMergeFieldsHistoricalI18nSource} from "./helpers/pdf-merge-fields-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-input-font16-reviewed.json",import.meta.url),"utf8"));
assert.match(fixture.base,/^[a-f0-9]{40}$/,"Bind the actual delivered full 40-hex BASE before git; never use a guessed merge SHA");
const file="static/portal/portal-theme.css",hash=value=>createHash("sha256").update(value).digest("hex");
const count=(source,part)=>source.split(part).length-1;
// LF only at the source-read boundary, matching the campaign's reviewed cross-platform hashes.
const current=fs.readFileSync(file,"utf8").replace(/\r\n/g,"\n");
const readBase=file=>execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n");
const baseline=readBase(file),edit=fixture.changes[0];
const rule='/* Keep PDF text controls readable on small screens. */\n@media (max-width: 767px) {\n  .portal-page.portal-pdf-split .portal-document-operation-form :is(input, select, textarea),\n  .portal-page.portal-pdf-merge .portal-document-operation-form :is(input, select, textarea),\n  .portal-page.portal-pdf-optimize .portal-document-operation-form :is(input, select, textarea) {\n    font-size: 16px;\n  }\n}';
function once(source,old,next){assert.equal(count(source,old),1,"Exact reviewed CSS slot must occur once");return source.replace(old,()=>next);}
test("one exact reviewed replacement binds actual BASE/current CSS; a missing mobile rule is a real RED",()=>{
  assert.equal(fixture.changes.length,1);assert.equal(edit.file,file);assert.equal(edit.count,1);
  assert.equal(count(baseline,edit.old),1);assert.equal(count(current,edit.new),1);
  assert.equal(hash(baseline),fixture.binding.baselineTheme);assert.equal(hash(current),fixture.binding.candidateTheme);
  assert.equal(current,once(baseline,edit.old,edit.new));assert.equal(historicalCss(current),baseline);
});
test("the sole addition is the literal 767px media rule, three PDF form selectors and one 16px declaration",()=>{
  assert.equal(edit.new,edit.old+"\n\n"+rule);
  assert.equal(count(rule,"@media"),1);assert.equal(count(rule,"font-size:"),1);assert.equal(count(rule,"font-size: 16px;"),1);
  assert.deepEqual([...rule.matchAll(/\.portal-page[^{,\n]+:is\(input, select, textarea\)/g)].map(match=>match[0]),[
    ".portal-page.portal-pdf-split .portal-document-operation-form :is(input, select, textarea)",
    ".portal-page.portal-pdf-merge .portal-document-operation-form :is(input, select, textarea)",
    ".portal-page.portal-pdf-optimize .portal-document-operation-form :is(input, select, textarea)"
  ]);
  assert.doesNotMatch(rule,/!important|animation|transition|transform|color|background|opacity|display|grid|flex|margin|padding|gap|line-height|font-family|font-weight/);
  assert.equal(rule.slice(rule.lastIndexOf("{")+1,rule.indexOf("}",rule.lastIndexOf("{"))).trim(),"font-size: 16px;");
});
test("all prior desktop rules and every outside stylesheet byte remain intact, without simulated computed style",()=>{
  const position=baseline.indexOf(edit.old),suffix=position+edit.old.length;
  assert.ok(position>=0);assert.equal(current.slice(0,position),baseline.slice(0,position));
  assert.equal(current.slice(position+edit.new.length),baseline.slice(suffix));
  assert.equal(current.length,baseline.length+"\n\n".length+rule.length);
  assert.equal(once(current,edit.new,edit.old),baseline,"No pre-existing 15px/desktop/other-route rule is edited");
});
test("portal and i18n stay byte-identical to delivered BASE and their frozen candidate hashes",()=>{
  for(const [file,key]of [["static/portal/portal.js","candidatePortal"],["static/portal/portal-i18n.js","candidateI18n"]]){
    const inverse=file.endsWith("portal.js")?pdfMergeFieldsHistoricalPortalSource:pdfMergeFieldsHistoricalI18nSource;
    const raw=inverse(fs.readFileSync(file,"utf8").replace(/\r\n/g,"\n"));
    assert.equal(raw,readBase(file));assert.equal(hash(raw),fixture.binding[key]);
  }
});
test("the finite helper leaves old and earlier historical CSS unaltered, including mixed line endings",()=>{
  for(const source of [baseline,"","/* unrelated historical CSS */\r\n.other { font-size: 16px; }\n",baseline.replace(/\n/g,"\r\n")])
    assert.equal(historicalCss(source),source);
});
test("partial, unknown-size, breakpoint, selector or anchor mutations fail closed rather than disappearing",()=>{
  const cases=[
    once(current,edit.new,edit.old+"\n\n/* Keep PDF text controls readable on small screens. */"),
    once(current,edit.new,edit.new.replace("/* Keep PDF text controls readable on small screens. */\n","")),
    once(current,edit.new,edit.new.replace("font-size: 16px;","font-size: 17px;")),
    once(current,edit.new,edit.new.replace("max-width: 767px","max-width: 768px")),
    once(current,edit.new,edit.new.replace(".portal-page.portal-pdf-merge",".portal-page.portal-image-resize")),
    once(current,edit.new,edit.new.replace(":is(input, select, textarea)",":is(input, button)")),
    once(current,edit.new,edit.new.replace("font-size: 16px;","font-size: 16px !important;")),
    once(current,edit.new,edit.new.replace("var(--portal-muted)","red"))
  ];
  for(const source of cases)assert.throws(()=>historicalCss(source),/Unreviewed PDF input font16 CSS/);
});
test("duplicate rules/anchors and detached or interrupted additions are rejected",()=>{
  for(const source of [
    current+"\n"+edit.new,current+"\n\n"+rule,current+"\n"+edit.old,
    once(baseline,edit.old,edit.old+"\n/* UNKNOWN BETWEEN ANCHOR AND RULE */\n"+rule),
    once(baseline,edit.old,rule+"\n\n"+edit.old)
  ])assert.throws(()=>historicalCss(source),/Unreviewed PDF input font16 CSS/);
});
test("the exact inverse preserves unknown outside bytes instead of laundering unrelated edits",()=>{
  const prefix='\r\n/* CUSTOMER prefix */\r\n',suffix='\r\n.other-input { font-size: 19px; }\r\n/* CUSTOMER suffix */';
  assert.equal(historicalCss(prefix+current+suffix),prefix+baseline+suffix);
  const changed=prefix+current;assert.notEqual(historicalCss(changed),baseline);assert.ok(historicalCss(changed).startsWith(prefix));
  assert.equal(historicalCss(current+suffix),baseline+suffix);
});
// This suite proves source scope/provenance only. Font paint at 375/390/767/768/1440,
// iOS focus behavior, overflow, geometry and touch/keyboard remain root-owned native NOT_RUN gates.
