import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-enhance-step-color-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"5d3257a1b37ae709ff293cab1fe6537f35d401ee386287d7644d757e90b4b581");
const fixture=JSON.parse(raw),[edit]=fixture.proposal.changes;
assert.equal(fixture.review.proposalExact,true);assert.equal(fixture.proposal.changes.length,1);
assert.equal(edit.file,"static/portal/portal-theme.css");assert.equal(edit.count,1);assert.ok(edit.new.startsWith(edit.old));
const addition=edit.new.slice(edit.old.length),marker="/* Keep Enhance step text readable in the light theme. */";
const selectors=['html:not([data-portal-theme="dark"]) .portal-page.portal-image-enhance .portal-project-steps strong',
  'html:not([data-portal-theme="dark"]) .portal-page.portal-image-enhance .portal-project-steps span'];
const fail="Unreviewed Enhance step color",count=(source,part)=>source.split(part).length-1;
export function enhanceStepColorHistoricalThemeSource(source){
  assert.equal(typeof source,"string",fail);
  if(!source.includes(marker)){for(const selector of selectors)assert.equal(count(source,selector),0,fail+" partial/unknown selector");return source;}
  assert.equal(count(source,marker),1,fail+" duplicate marker");
  assert.equal(count(source,addition),1,fail+" changed/partial/duplicate addition");
  for(const selector of selectors)assert.equal(count(source,selector),1,fail+" duplicate selector");
  assert.equal(count(source,edit.new),1,fail+" moved addition");
  return source.replace(addition,"");
}
