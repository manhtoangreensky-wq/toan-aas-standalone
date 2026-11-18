import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-resize-subtitle-wrap-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"48d3a038e51e355b15d24026d7585c09b42477634f424985f9e2c7176e6cfd50");
const fixture=JSON.parse(raw),[edit]=fixture.proposal.changes,fail="Unreviewed Resize subtitle wrapping",count=(source,part)=>source.split(part).length-1;
assert.equal(fixture.review.proposalExact,true);assert.equal(fixture.proposal.changes.length,1);assert.equal(edit.count,1);assert.equal(edit.file,"static/portal/portal-theme.css");assert.ok(edit.new.startsWith(edit.old));
const addition=edit.new.slice(edit.old.length),marker="/* Keep image result subtitles readable in Resize and history. */",selector=".portal-page:is(.portal-image-resize, .portal-image-operation-history) .portal-document-operation-card .portal-document-operation-title .portal-card-subtitle";
export function resizeSubtitleWrapHistoricalThemeSource(source){
  assert.equal(typeof source,"string",fail);
  if(!source.includes(marker)){assert.equal(count(source,selector),0,fail+" partial/unknown selector");return source;}
  assert.equal(count(source,marker),1,fail+" duplicate marker");assert.equal(count(source,selector),1,fail+" duplicate selector");
  assert.equal(count(source,addition),1,fail+" changed/partial/duplicate addition");assert.equal(count(source,edit.new),1,fail+" moved addition");
  return source.replace(addition,"");
}
