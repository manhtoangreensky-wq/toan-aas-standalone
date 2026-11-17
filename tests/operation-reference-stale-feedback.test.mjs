import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {operationReferenceFeedbackRuntime as runtime} from "./helpers/operation-reference-feedback-runtime.mjs";
import {operationReferenceStaleFeedbackHistoricalIntegrationSource as inverse} from "./helpers/operation-reference-stale-feedback-snapshot.mjs";
import {imageResizeGuidanceHistoricalI18nSource} from "./helpers/image-resize-guidance-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/operation-reference-stale-feedback-reviewed.json",import.meta.url)));
const paths={integration:"static/portal/integration.js",i18n:"static/portal/portal-i18n.js",portal:"static/portal/portal.js",theme:"static/portal/portal-theme.css"};
const lf=value=>value.replace(/\r\n/g,"\n"),hash=value=>createHash("sha256").update(value).digest("hex");
// Read actual source directly: the historical copy loader must not remove the new guard under test.
const source=Object.fromEntries(Object.entries(paths).map(([key,file])=>[key,lf(fs.readFileSync(new URL("../"+file,import.meta.url),"utf8"))]));
assert.match(fixture.base,/^[a-f0-9]{40}$/);
const baseline=Object.fromEntries(Object.entries(paths).map(([key,file])=>[key,lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:30e6}))]));
for(const route of ["/documents/split","/image/resize"]){
  for(const failed of [false,true]){
    test(route+" current read preserves truthful "+(failed?"failure":"success")+" feedback",async()=>{
      const r=runtime("vi",route,source),job=r.run("filter",{asset_reference_q:"CURRENT"});
      assert.equal(r.network.length,1);assert.equal(r.toasts.length,0);
      r.settle(0,{failed});await job;
      assert.equal(r.toasts.length,1);assert.equal(r.toasts[0].attributes.role,failed?"alert":"status");
      assert.equal(r.toasts[0].textContent,failed?"Chưa tải được tệp. Hãy thử lại.":"Đã lọc danh sách tệp.");
    });
    for(const reason of ["route","session","request","logout"]){
      test(route+" "+reason+" stale "+(failed?"failure":"success")+" must not show feedback",async()=>{
        const r=runtime("vi",route,source),job=r.run("filter",{asset_reference_q:"OLD"});
        assert.equal(r.network.length,1);assert.equal(r.toasts.length,0);r.mutate(reason);
        const protectedState=JSON.stringify(r.state);
        r.settle(0,{failed});await job;
        assert.equal(JSON.stringify(r.state),protectedState,"Existing stale data guards remain effective");
        assert.equal(r.toasts.length,0,"A stale read must not alert or claim success on the current page/session");
      });
    }
  }
  for(const oldFailed of [false,true])for(const currentFailed of [false,true]){
    test(route+" newer "+currentFailed+" settles before older "+oldFailed+" without a second toast",async()=>{
      const r=runtime("vi",route,source);
      const older=r.run("filter",{asset_reference_q:"OLDER"}),current=r.run("filter",{asset_reference_q:"CURRENT"});
      assert.equal(r.network.length,2);assert.equal(r.toasts.length,0);
      r.settle(1,{failed:currentFailed});await current;
      assert.equal(r.toasts.length,1);assert.equal(r.toasts[0].attributes.role,currentFailed?"alert":"status");
      const state=JSON.stringify(r.state),toasts=JSON.stringify(r.observe().toasts);
      r.settle(0,{failed:oldFailed});await older;
      assert.equal(JSON.stringify(r.state),state);
      assert.equal(JSON.stringify(r.observe().toasts),toasts,"The older read may not append an obsolete alert");
    });
  }
}
test("exact two worker edits and scoped inverse bind actual source and every outside byte",()=>{
  assert.equal(fixture.changes.length,2);let expected=baseline.integration;
  for(const edit of fixture.changes){assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(source.integration,expected);assert.equal(hash(source.integration),fixture.binding.candidateIntegration);
  assert.equal(hash(baseline.integration),fixture.binding.baselineIntegration);assert.equal(inverse(source.integration),baseline.integration);
  assert.equal(inverse(baseline.integration),baseline.integration);
  for(const key of ["i18n","portal","theme"]){const current=key==="i18n"?imageResizeGuidanceHistoricalI18nSource(source[key]):source[key];assert.equal(current,baseline[key]);assert.equal(hash(current),fixture.binding[key]);}
  const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* CUSTOMER Facebook TikTok suffix */";
  assert.equal(inverse(prefix+source.integration+suffix),prefix+baseline.integration+suffix);
});
test("finite stale inverse rejects partial/changed/duplicate/misplaced chunks without masking other feedback code",()=>{
  for(const edit of fixture.changes){
    assert.throws(()=>inverse(source.integration.replace(edit.new,edit.old)),/Unreviewed operation reference stale feedback/);
    assert.throws(()=>inverse(source.integration+"\n"+edit.new),/Unreviewed operation reference stale feedback/);
    assert.throws(()=>inverse(source.integration.replace(edit.new,edit.new.replace("feedbackEpoch","UNKNOWN"))),/Unreviewed operation reference stale feedback/);
    assert.throws(()=>inverse(source.integration.replace(edit.new,edit.old)+"\n"+edit.new),/Unreviewed operation reference stale feedback/);
  }
  const unrelated='/* feedbackPath belongs to another feature */\r\nconst feedbackSessionEpoch = campaignSessionEpoch;\r\n';
  assert.equal(inverse(unrelated),unrelated);
});
