import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {galleryReadabilityHistoricalSource} from "./helpers/gallery-readability-historical.mjs";
const file="static/portal/portal-theme.css",base="363d6ca55081eea4089ebf489cd183b09ba1aa96";
// FCR now reads its historical input; the GPR acceptance reads physical CSS.
const read=()=>galleryReadabilityHistoricalSource(fs.readFileSync(file,"utf8").replace(/\r\n/g,"\n"),file);
const before=execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:8e6}).replace(/\r\n/g,"\n");
const scope='[data-portal-main][data-portal-presentation-route="default"] > .portal-page:has(> .portal-feature-jumps)';
const selectors=[
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-feature-jumps a.portal-feature-jump:is(:hover, :focus-visible)',
  'html[data-portal-theme="dark"] '+scope+' > .portal-feature-jumps .portal-feature-jump--current',
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-feature-catalog > .portal-empty p',
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-hero .portal-eyebrow'
];
const ids=["FCR-LINK","FCR-CURRENT","FCR-EMPTY","FCR-EYEBROW"];
const blocks=selectors.map(selector=>selector+" {\n  color: var(--portal-text);\n}");
export const familyReadabilityAddition="\n/* Keep family-directory text readable without changing surfaces or motion. */\n"+blocks.join("\n")+"\n";
for(const[index,id]of ids.entries())test(id+" has only the scoped semantic foreground override",()=>{
  const source=read();
  assert.equal(source.split(blocks[index]).length-1,1,id+" reviewed foreground rule missing/duplicated");
  assert.equal(source.split(selectors[index]).length-1,1,id+" unique owner");
});
test("family readability preserves every prior CSS byte, background, focus outline, geometry and motion",()=>{
  assert.equal(read()===before+familyReadabilityAddition,true,"Only the four reviewed color declarations may be appended");
  assert.equal((familyReadabilityAddition.match(/color:/g)||[]).length,4);
  assert.doesNotMatch(familyReadabilityAddition,/!important|opacity|display:|visibility|font|padding|margin|transition:|animation:|transform:|background:|outline:|border:/);
});
// Physical-source scope only. Measured paint-chain contrast, root-route exclusion,
// hover/Tab behavior and protected geometry are proved by the HTTP Chrome gate.
