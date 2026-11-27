import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {FAMILY_READABILITY_ADDITION as addition,featureFamilyReadabilityHistoricalSource as project} from "./helpers/feature-family-readability-historical.mjs";
import {featureCatalogFullBundle135HistoricalSource as composed} from "./helpers/feature-catalog-full-bundle135-historical.mjs";
const file="static/portal/portal-theme.css",fail=/Unreviewed feature-family readability/;
const before=execFileSync("git",["show","363d6ca55081eea4089ebf489cd183b09ba1aa96:"+file],{encoding:"utf8",maxBuffer:8e6}).replace(/\r\n/g,"\n");
const current=before+addition;
test("finite CSS inverse restores BASE, is idempotent and is composed into old source readers",()=>{
  assert.equal(project(current,file),before);assert.equal(project(project(current,file),file),before);
  assert.equal(composed(current,file),before);
});
test("historical old/unknown/outside bytes and unrelated files are preserved",()=>{
  const prefix="/* CUSTOMER */\r\n",suffix="\r\n.other {color:rebeccapurple}";
  assert.equal(project(before,file),before);assert.equal(project(prefix+current+suffix,file),prefix+before+suffix);
  const internal=current.replace(":root {",":root {\n/* UNKNOWN */");
  assert.equal(project(internal,file),before.replace(":root {",":root {\n/* UNKNOWN */"));
  assert.equal(project(current,"other.css"),current);assert.equal(project("",file),"");
});
const mutations={
  changedColor:source=>source.replace("color: var(--portal-text);\n}\nhtml[data-portal-theme","color: red;\n}\nhtml[data-portal-theme"),
  changedTheme:source=>source.replace(addition,addition.replace('html[data-portal-theme="dark"]','html:not([data-portal-theme="dark"])')),
  partial:source=>source.slice(0,-40),
  duplicate:source=>source+addition,
  detached:source=>source.replace(addition,"")+addition.replace(/^\n/,"\n/* UNKNOWN */\n"),
  reordered:source=>source.replace(addition,addition.replace(/(html[^\n]+\{\n  color: var\(--portal-text\);\n\})\n(html[^\n]+\{\n  color: var\(--portal-text\);\n\})/,"$2\n$1")),
  extraDeclaration:source=>source.replace(addition,addition.replace("color: var(--portal-text);","color: var(--portal-text); opacity: .5;")),
  markerless:source=>source.replace("Keep family-directory text readable without changing surfaces or motion.","UNKNOWN"),
  extraOwner:source=>source+"\n[data-portal-main][data-portal-presentation-route=\"default\"] > .portal-page:has(> .portal-feature-jumps) {color:red}",
  changedAncestor:source=>source.replace(addition,addition.replace('data-portal-presentation-route="default"','data-portal-presentation-route="features"'))
};
for(const[kind,mutate]of Object.entries(mutations))test("finite CSS inverse rejects "+kind,()=>{
  assert.throws(()=>project(mutate(current),file),fail);
});
