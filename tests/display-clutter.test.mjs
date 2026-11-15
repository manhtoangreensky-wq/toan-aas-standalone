import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {displayClutterSources,displayClutterRenderer} from "./helpers/display-clutter-runtime.mjs";
import {displayClutterHistoricalPortalSource} from "./helpers/display-clutter-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/display-clutter-reviewed.json",import.meta.url),"utf8"));
const source=displayClutterSources(),baseline=displayClutterSources(true);
const current=await displayClutterRenderer(source),before=await displayClutterRenderer(baseline);
const plain=value=>JSON.parse(JSON.stringify(value)),hash=value=>createHash("sha256").update(value).digest("hex");
const sessions=Object.fromEntries(["vi","en","zh"].map(locale=>[locale,{
  current:current(locale,"/features",{}),before:before(locale,"/features",{})
}]));
function render(session,locale,route,raw){
  // These are normalized component-context fixtures, not server bootstrap DTOs.
  const saved=JSON.stringify(raw),context={...session.context,...raw,path:route,interfaceLocale:locale};
  const page=session.qa.resolvePage(route),html=session.qa.renderPage(page,context);
  assert.equal(JSON.stringify(raw),saved);
  return {...session,context,page,html};
}
const loadingMeta='<div class="portal-state-meta"><span>Signed session</span><span>Không cache private</span><span>Không fallback browser</span></div>';
const failedMeta='<div class="portal-state-meta"><span>Không có cache</span><span>Không có Bot fallback</span><span>Không có URL công khai</span></div>';
const customer='CUSTOMER studio media Facebook TikTok <script>alert("x")</script>&';
for(const locale of ["vi","en","zh"]){
  test(`${locale}: document loading/error retain exact paragraphs, retry rights and all other markup without implementation-tag rows`,()=>{
    for(const route of ["/documents","/documents/pdf"])for(const state of ["loading","failed","ready"])for(const canView of [true,false,"true"])for(const refresh of [true,false,"true"]){
      const raw={capabilities:{"document-operation-view":canView,"document-operation-refresh":refresh},documentOperationsReadState:state,documentOperations:[]};
      const saved=JSON.stringify(raw),a=render(sessions[locale].current,locale,route,raw),b=render(sessions[locale].before,locale,route,raw);
      assert.equal(JSON.stringify(raw),saved);assert.deepEqual(plain(a.context),plain(b.context));
      const expected=canView===true&&state!=="ready"?b.html.replace(state==="loading"?loadingMeta:failedMeta,""):b.html;
      assert.equal(a.html,expected,"Only the redundant implementation row may disappear");
      if(canView===true&&state!=="ready"){
        assert.doesNotMatch(a.html,/portal-state-meta|Signed session|Bot fallback/);
        assert.ok(a.html.includes(a.messages[locale][state==="loading"?"docReadUiLoadingBody":"docReadUiFailedBody"]));
        assert.equal(a.html.includes('data-portal-action="document-operation-refresh"'),state==="failed"&&refresh===true);
      }
    }
  });
  test(`${locale}: catalogue removes only route notice, retains cards, customer content, navigation and immutable descriptors`,()=>{
    const descriptors=[undefined,{state:"deferred",catalog_version:"unconfigured",catalog_approval:"unconfigured",price_display:false},{state:"ready",price_display:true}];
    for(const routeEngine of descriptors){
      const raw={routeEngine,catalog:[{route:"/voice/tts",title:customer,description:customer,group:"voice",kind:"customer"}]};
      const saved=JSON.stringify(raw),a=render(sessions[locale].current,locale,"/features",raw),b=render(sessions[locale].before,locale,"/features",raw);
      const old=b.qa.renderRouteEngineBoundary(b.context);
      assert.ok(old.includes('role="status"'));assert.equal(a.qa.renderRouteEngineBoundary(a.context),"");
      assert.equal(a.html,b.html.replace(old,""));assert.equal(a.html.includes("portal-route-engine-notice"),false);
      assert.deepEqual(plain(a.qa.normalizeRouteEngineDescriptor(routeEngine)),plain(b.qa.normalizeRouteEngineDescriptor(routeEngine)));
      assert.deepEqual(plain(a.qa.customerCatalog(a.context)),plain(b.qa.customerCatalog(b.context)));
      assert.ok(a.html.includes('href="/voice/tts"'));
      assert.equal(JSON.stringify(raw),saved);
    }
  });
  test(`${locale}: family removes only audit details and route notice, keeps useful aside, routes and guards`,()=>{
    for(const capabilityHub of [undefined,{available:false,families:[]},{available:true,families:[{key:"voice",customerCommandCount:7,mappedRouteCount:4,guardedRouteCount:2,telegramOnlyCount:1}]}]){
      const raw={capabilityHub,routeEngine:{state:"deferred",catalog_version:"unconfigured",catalog_approval:"unconfigured",price_display:false},
        catalog:[{route:"/voice/tts",title:customer,description:customer,group:"voice",kind:"customer"}]};
      const saved=JSON.stringify(raw),a=render(sessions[locale].current,locale,"/features/voice",raw),b=render(sessions[locale].before,locale,"/features/voice",raw);
      const audit=b.qa.renderCapabilityHubFamilySummary(b.context,"voice"),notice=b.qa.renderRouteEngineBoundary(b.context);
      if(capabilityHub?.available===true)assert.ok(audit.includes("portal-capability-family-summary"));
      assert.equal(a.qa.renderCapabilityHubFamilySummary(a.context,"voice"),"");
      assert.equal(a.html,b.html.replace(audit,"").replace(notice,""));
      assert.doesNotMatch(a.html,/portal-capability-family-summary|portal-route-engine-notice/);
      assert.ok(a.html.includes("<aside")&&a.html.includes("portal-summary-list")&&a.html.includes('href="/voice/tts"'));
      assert.deepEqual(plain(a.qa.capabilityHubFamily(a.context,"voice")),plain(b.qa.capabilityHubFamily(b.context,"voice")));
      assert.deepEqual(plain(a.qa.registeredFeatureFamilyEntries(a.context,"voice")),plain(b.qa.registeredFeatureFamilyEntries(b.context,"voice")));
      assert.equal(JSON.stringify(raw),saved);
    }
  });
}
test("finite source inverse preserves outside data and rejects partial or changed proposal chunks",()=>{
  assert.equal(hash(baseline.portal),fixture.baselinePortal);assert.equal(hash(source.portal),fixture.candidatePortal);
  assert.equal(source.i18n,baseline.i18n);assert.equal(displayClutterHistoricalPortalSource(source.portal),baseline.portal);
  assert.equal(displayClutterHistoricalPortalSource(baseline.portal),baseline.portal);
  for(const edit of fixture.changes){
    const mutated=source.portal.replace(edit.new,edit.new+"/* UNKNOWN */");
    assert.notEqual(displayClutterHistoricalPortalSource(mutated),baseline.portal,"Outside mutations remain visible");
    assert.throws(()=>displayClutterHistoricalPortalSource(source.portal.replace(edit.new,edit.old)),/Unreviewed partial/);
  }
  const suffix="\n// CUSTOMER studio media TikTok";
  assert.ok(displayClutterHistoricalPortalSource(source.portal+suffix).endsWith(suffix));
});
