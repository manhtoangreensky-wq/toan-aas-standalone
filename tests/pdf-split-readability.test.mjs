import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {PDF_SPLIT_READABILITY_ADDITION as addition,pdfSplitReadabilityHistoricalCss} from "./helpers/pdf-split-readability-snapshot.mjs";
const file="static/portal/portal-theme.css",base=execFileSync("git",["show","44134931e2adb08fecb0cad68c4eac19a6903c7f:"+file],{encoding:"utf8",maxBuffer:3e6}).replace(/\r\n/g,"\n");
const source=fs.readFileSync(file,"utf8").replace(/\r\n/g,"\n");
test("Split label/help use light semantic colors only, every prior theme byte unchanged",()=>{
  assert.equal(source===base+addition,true,"Exact two-rule EOF append only");
  assert.equal(source.split(addition).length-1,1);
  assert.doesNotMatch(addition,/!important|font|background|padding|margin|border|opacity|display|visibility|transition|animation|transform/);
  assert.equal(pdfSplitReadabilityHistoricalCss(source),base);
});
test("finite CSS projection rejects duplicates/misplacement and never hides unknown values or outside mutations",()=>{
  assert.equal(pdfSplitReadabilityHistoricalCss(base+addition),base);
  assert.throws(()=>pdfSplitReadabilityHistoricalCss(base+addition+addition),/Unreviewed PDF split readability CSS/);
  assert.throws(()=>pdfSplitReadabilityHistoricalCss(base+addition+"\n/* UNKNOWN */"),/Unreviewed PDF split readability CSS/);
  const changed=addition.replace("var(--portal-muted)","red");
  assert.equal(pdfSplitReadabilityHistoricalCss(base+changed),base+changed);
  assert.ok(pdfSplitReadabilityHistoricalCss(base+"\n/* CUSTOMER */").endsWith("/* CUSTOMER */"));
});
// Actual colors, paint layers, controls, geometry, dark/sentinel equality and
// contrast are measured by the owned browser run; this source check is not AX.
