import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pageMetaSources,pageMetaRenderer} from "./helpers/chat-page-meta-runtime.mjs";
import {resizeCopyContext} from "./helpers/image-resize-plain-copy-runtime.mjs";
import {resizeDecode} from "./helpers/image-resize-guidance-runtime.mjs";
import {imageSharedChanges,imageSharedHistoricalI18nSource,imageSharedHistoricalPortalSource,imageSharedHistoricalSnapshot} from "./helpers/image-shared-plain-copy-snapshot.mjs";
import {pdfCompressMetaHistoricalSources} from "./helpers/pdf-compress-meta-snapshot.mjs";
import {documentConvertCustomerHistoricalSource} from "./helpers/document-convert-customer-copy-snapshot.mjs";

const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-shared-plain-copy-reviewed.json",import.meta.url),"utf8"));
// Legacy historical-render comparator: stage later shell dictionaries before the pre-existing source projection.
const live=pageMetaSources(),historicalInput={...live,pages:documentConvertCustomerHistoricalSource(live.pages,"copyfast_pages.py")};
const physical=pdfCompressMetaHistoricalSources(historicalInput),render=await pageMetaRenderer(physical);
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
  execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n")]));
const prior=await pageMetaRenderer(baseline),locales=["vi","en","zh"];
const expected=(locale,key)=>fixture.rows.find(row=>row[0]===key)[locales.indexOf(locale)+1];
const controls=html=>[...html.matchAll(/<(?:form|input|select|textarea|button|option|a)\b[^>]*>/g)]
  .map(match=>match[0].replace(/\sdata-portal-confirm="[^"]*"/g,"").replace(/\saria-label="[^"]*"/g,""));
const states=html=>[...html.matchAll(/data-state="([^"]*)"/g)].map(match=>match[1]);
const emptyDivs=html=>[...html.matchAll(/<div[^>]*>\s*<\/div>/g)].map(match=>match[0]);

for(const locale of locales){
  const ready=render(locale,"/image/resize",resizeCopyContext());
  for(const row of fixture.rows){
    test(locale+" shared Image catalogue resolves "+row[0],()=>{
      assert.equal(ready.messages[locale]["imageOperationUi."+row[0]],row[locales.indexOf(locale)+1]);
    });
  }
  test(locale+" Resize actual source picker and vault navigation use plain words",()=>{
    const html=ready.html;
    for(const key of ["field.source.label","field.source.empty","field.source.help","common.openVault"]){
      assert.ok(resizeDecode(html).includes(expected(locale,key)),key);
    }
    assert.ok(html.includes('name="source_asset_id"'));
    assert.ok(html.includes('href="/asset-vault"'));
  });
  for(const state of ["guard","loading","failed"]){
    test(locale+" Resize "+state+" omits technical chips but keeps actual message, state and retry",()=>{
      const context=resizeCopyContext(state),saved=JSON.stringify(context);
      const now=render(locale,"/image/resize",context),old=prior(locale,"/image/resize",context);
      assert.equal(now.html.includes("portal-state-meta"),false);
      assert.ok(now.html.includes("<h2>")&&now.html.includes("<p>"));
      assert.deepEqual(states(now.html),states(old.html));
      assert.deepEqual(controls(now.html),controls(old.html));
      assert.equal(now.html.includes('data-portal-action="image-operation-resize"'),false);
      if(state==="failed"){
        assert.ok(resizeDecode(now.html).includes(expected(locale,"common.formRetry")));
        assert.ok(now.html.includes('data-portal-action="image-operation-refresh"'));
      }
      if(state==="loading")assert.ok(resizeDecode(now.html).includes(expected(locale,"common.state.loadingTitle")));
      if(state==="failed")assert.ok(resizeDecode(now.html).includes(expected(locale,"common.state.failedTitle")));
      assert.equal(JSON.stringify(context),saved);
      assert.deepEqual(emptyDivs(now.html),emptyDivs(old.html),"No added empty replacement; existing hero-actions stays exact");
    });
  }
  test(locale+" Resize card metadata and download feedback consume shared copy",()=>{
    for(const [state,key]of [["processing","common.downloadVerified"],["failed","common.downloadFailed"],["guarded","common.downloadGuarded"]]){
      const context=resizeCopyContext("card");context.imageOperations[0].state=state;
      const html=render(locale,"/image/resize",context).html;
      assert.ok(resizeDecode(html).includes(expected(locale,"common.canvas")));
      assert.ok(resizeDecode(html).includes(expected(locale,key)),state);
    }
  });
  test(locale+" actual completed-image download/save/handoff controls use plain labels and keep eligibility",()=>{
    const context=resizeCopyContext("card");
    context.capabilities["image-operation-export-to-asset-vault"]=true;
    context.capabilities["content-handoff-create"]=true;
    context.imageOperations[0].state="completed";context.imageOperations[0].download_ready=true;
    const now=render(locale,"/image/resize",context),old=prior(locale,"/image/resize",context);
    for(const key of ["common.downloadPng","common.saveVault","common.exportConfirm","common.prepareHandoff","common.handoffConfirm","common.continueConfirm"]){
      assert.ok(resizeDecode(now.html).includes(expected(locale,key)),key);
      assert.equal(resizeDecode(old.html).includes(expected(locale,key)),false,"Authentic BASE lacks new "+key);
    }
    assert.deepEqual(controls(now.html),controls(old.html));
    context.imageOperations[0].download_ready=false;
    const denied=render(locale,"/image/resize",context).html;
    assert.equal(denied.includes('data-portal-action="image-operation-export-to-asset-vault"'),false);
    assert.equal(denied.includes('data-portal-action="image-operation-export-to-content-handoff"'),false);
  });
  test(locale+" denied/ready/empty/no-run controls and literal customer content retain BASE semantics",()=>{
    for(const state of ["ready","guard","loading","failed","empty","noRun","disabled","card"]){
      const context=resizeCopyContext(state),now=render(locale,"/image/resize",context),old=prior(locale,"/image/resize",context);
      assert.deepEqual(controls(now.html),controls(old.html),state);
      assert.deepEqual(states(now.html),states(old.html),state);
      assert.equal(now.title,old.title,state);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context),state);
      assert.equal(now.html.includes("<img src=x"),false);
    }
  });
  test(locale+" unrelated document/chat/dashboard routes remain byte-exact",()=>{
    for(const route of ["/documents","/documents/split","/documents/compress","/chat","/dashboard"]){
      const context={profile:{locale,displayName:"CUSTOMER media studio Facebook TikTok <b>literal</b>"}};
      assert.equal(render(locale,route,context).html,prior(locale,route,context).html,route);
    }
  });
}
test("catalogue keys/order and all non-target values remain exactly the delivered BASE",()=>{
  for(const locale of locales){
    const now=render(locale,"/image/resize",resizeCopyContext()).messages[locale];
    const old=prior(locale,"/image/resize",resizeCopyContext()).messages[locale];
    assert.deepEqual(Object.keys(now),Object.keys(old));
    const target=new Set(fixture.rows.map(row=>"imageOperationUi."+row[0]));
    for(const key of Object.keys(now))if(!target.has(key))assert.equal(now[key],old[key],locale+":"+key);
  }
  assert.equal(physical.pages,baseline.pages);
});
test("new shared-copy source comparator restores only exact worker edits",()=>{
  const sha=value=>createHash("sha256").update(value).digest("hex");
  assert.equal(sha(physical.i18n),"45e5b9ba90fde2ba7af006df7c5b76505350283a8faa96706db48503692601eb");
  assert.equal(sha(physical.portal),"ff4eee9b0b7a1dd55704e3e97d7074389398b089c001f07b166346c36da9e881");
  assert.equal(imageSharedHistoricalI18nSource(physical.i18n),baseline.i18n);
  assert.equal(imageSharedHistoricalPortalSource(physical.portal),baseline.portal);
  for(const locale of locales){
    assert.deepEqual(imageSharedHistoricalSnapshot(Object.entries(render(locale,"/image/resize",resizeCopyContext()).messages[locale]),locale),
      Object.entries(prior(locale,"/image/resize",resizeCopyContext()).messages[locale]));
  }
});
test("new shared-copy source comparator rejects partial/unknown/duplicate/reordered edits and retains outside bytes",()=>{
  const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* media studio Facebook TikTok */";
  for(const [raw,inverse,old]of [[physical.i18n,imageSharedHistoricalI18nSource,baseline.i18n],[physical.portal,imageSharedHistoricalPortalSource,baseline.portal]]){
    assert.equal(inverse(prefix+raw+suffix),prefix+old+suffix);
  }
  for(const edit of imageSharedChanges){
    assert.throws(()=>imageSharedHistoricalI18nSource(physical.i18n.replace(edit.new,edit.old)),/Unreviewed Image shared plain copy/);
    assert.throws(()=>imageSharedHistoricalI18nSource(physical.i18n+"\n"+edit.new),/Unreviewed Image shared plain copy/);
    assert.throws(()=>imageSharedHistoricalI18nSource(physical.i18n.replace(edit.new,edit.new.replace(edit.newRow[1],"UNKNOWN"))),/Unreviewed Image shared plain copy/);
  }
  const [a,b]=imageSharedChanges;
  assert.throws(()=>imageSharedHistoricalI18nSource(physical.i18n.replace(a.new,"TEMP").replace(b.new,a.new).replace("TEMP",b.new)),/Unreviewed Image shared plain copy/);
  const section=physical.portal.slice(physical.portal.indexOf("  function renderImageResize("),physical.portal.indexOf("  function renderImageEnhance("));
  const line=section.split("\n").find(value=>value.includes('data-state="guarded"')&&value.includes("return"));
  assert.throws(()=>imageSharedHistoricalPortalSource(physical.portal+"\n"+line),/Unreviewed Image shared plain copy/);
});
