import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-to-pdf-guard-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"57528c5cd1d37175cad203c9e40c30f816c4313f8589df776c3b572f0e7e21a3");
const authority=JSON.parse(raw),[edit]=authority.proposal.changes;
assert.equal(authority.review.proposalExact,true);
assert.equal(authority.proposal.specId,"IMAGE-TO-PDF-GUARD-CUSTOMER-COPY-20261118");
assert.equal(authority.proposal.changes.length,1);
assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);
assert.deepEqual(authority.proposal.deviations,[]);
const count=(source,part)=>source.split(part).length-1,fail="Unreviewed Image-to-PDF guard";
export function imageToPdfGuardHistoricalPortalSource(source){
  assert.equal(typeof source,"string",fail);
  const start=source.indexOf("  function renderImageToPdf(page, context) {");
  const old=count(source,edit.old),next=count(source,edit.new);
  if(start<0){
    assert.equal(old+next,0,fail+" detached");
    assert.equal(source.includes("portal-page portal-image-to-pdf"),false,fail+" partial owner");
    return source;
  }
  const end=source.indexOf("\n  function renderImageOperationHistory(",start);
  assert.ok(start>=0&&end>start,fail+" owner");
  const owner=source.slice(start,end);
  assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/changed/duplicate");
  const selected=next?edit.new:edit.old;
  assert.equal(count(owner,selected),1,fail+" detached");
  return next?source.replace(edit.new,()=>edit.old):source;
}
