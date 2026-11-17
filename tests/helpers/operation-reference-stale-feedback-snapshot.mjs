import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/operation-reference-stale-feedback-reviewed.json",import.meta.url),"utf8"));
const failure='        if (!refreshed) throw new Error(operationReferenceFeedbackText("failed", "Chưa tải được tệp. Hãy thử lại."));';
const edits=[
  {file:"static/portal/integration.js",count:1,
    old:"        const refreshed = await hydrateDocumentAssetReferences(kind, filter, offset, selections);\n"+failure,
    new:"        const feedbackSessionEpoch = assetVaultSessionEpoch;\n        const feedbackPath = currentPortalPath();\n        const feedbackEpoch = (documentAssetReferenceHydrationEpoch[kind] || 0) + 1;\n        const refreshed = await hydrateDocumentAssetReferences(kind, filter, offset, selections);\n        if (!documentAssetReferenceRequestIsCurrent(kind, feedbackEpoch, feedbackSessionEpoch, feedbackPath)) return;\n"+failure},
  {file:"static/portal/integration.js",count:1,
    old:"        const refreshed = await hydrateImageOperationAssetReferences(filter, offset, selections);\n"+failure,
    new:"        const feedbackSessionEpoch = assetVaultSessionEpoch;\n        const feedbackPath = currentPortalPath();\n        const feedbackEpoch = imageOperationAssetReferenceHydrationEpoch + 1;\n        const refreshed = await hydrateImageOperationAssetReferences(filter, offset, selections);\n        if (!imageOperationAssetReferenceRequestIsCurrent(feedbackEpoch, feedbackSessionEpoch, feedbackPath)) return;\n"+failure}
];
assert.deepEqual(fixture.changes,edits,"Unreviewed operation reference stale-feedback fixture");
const fail="Unreviewed operation reference stale feedback",count=(text,part)=>text.split(part).length-1;
const markers=["const feedbackSessionEpoch = assetVaultSessionEpoch;","const feedbackEpoch = (documentAssetReferenceHydrationEpoch[kind] || 0) + 1;",
  "const feedbackEpoch = imageOperationAssetReferenceHydrationEpoch + 1;",
  "documentAssetReferenceRequestIsCurrent(kind, feedbackEpoch, feedbackSessionEpoch, feedbackPath)",
  "imageOperationAssetReferenceRequestIsCurrent(feedbackEpoch, feedbackSessionEpoch, feedbackPath)"];
export function operationReferenceStaleFeedbackHistoricalIntegrationSource(source){
  assert.equal(typeof source,"string",fail);
  if(!markers.some(marker=>source.includes(marker)))return source;
  let result=source;
  for(const [index,edit]of edits.entries()){
    assert.equal(count(result,edit.new),1,fail+" partial/changed/duplicate chunk");
    const kind=index===0?"document":"image-operation";
    const owner='      if (["'+kind+'-asset-reference-filter", "'+kind+'-asset-reference-filter-clear", "'+kind+'-asset-reference-page"].includes(action)) {';
    assert.equal(count(result,owner),1,fail+" action owner");
    const start=result.indexOf(owner),end=result.indexOf("\n      if (",start+owner.length);
    assert.ok(end>start,fail+" action boundary");
    const section=result.slice(start,end);assert.equal(count(section,edit.new),1,fail+" misplaced chunk");
    result=result.slice(0,start)+section.replace(edit.new,()=>edit.old)+result.slice(end);
  }
  assert.equal(markers.some(marker=>result.includes(marker)),false,fail+" unknown/residual marker");
  return result; // Exact owned chunks only; unrelated feedbackPath/campaign variables stay untouched.
}
