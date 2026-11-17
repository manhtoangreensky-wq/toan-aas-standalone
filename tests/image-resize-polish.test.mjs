import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {resizeReadyContext,RESIZE_CUSTOMER} from "./helpers/image-resize-guidance-runtime.mjs";
import {resizePlainHistoricalI18nSource} from "./helpers/image-resize-plain-copy-snapshot.mjs";
import {resizePolishHistoricalPortalSource,resizePolishHistoricalI18nSource,
  resizePolishHistoricalPagesSource,resizePolishHistoricalThemeSource,resizePolishHistoricalSnapshot} from "./helpers/image-resize-polish-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-polish-reviewed.json",import.meta.url),"utf8"));
const live=pageMetaSources(),source={...live,i18n:resizePlainHistoricalI18nSource(live.i18n)},render=await pageMetaRenderer(source),lf=x=>x.replace(/\r\n/g,"\n"),hash=x=>createHash("sha256").update(x).digest("hex");
const files={pages:"copyfast_pages.py",portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",theme:"static/portal/portal-theme.css",integration:"static/portal/integration.js"};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:30e6}))]));
const beforeRender=await pageMetaRenderer(baseline),locales=["vi","en","zh"];
const copy={
  vi:{title:"Đổi kích thước ảnh",description:"Chọn ảnh đã lưu, đặt kích thước và tạo bản PNG mới. Tệp gốc được giữ nguyên."},
  en:{title:"Resize images",description:"Choose a saved image, set its size and create a new PNG. The original stays unchanged."},
  zh:{title:"调整图像尺寸",description:"选择已保存的图像，设置尺寸并创建新的 PNG。原文件将保持不变。"}
};
const controls=html=>[...html.matchAll(/<(?:input|select|textarea|button|form|option)\b[^>]*>/g)].map(m=>m[0]);
for(const locale of locales){
  test(locale+" Resize actual outer title uses interface language",()=>{
    const r=render(locale,"/image/resize",resizeReadyContext());
    assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy[locale].title);
    assert.equal(r.title,copy[locale].title+" · TOAN AAS");
    assert.ok(r.qa.renderHeader(r.page,r.context).includes(copy[locale].title));
  });
  test(locale+" Resize actual description gives useful instructions",()=>{
    const r=render(locale,"/image/resize",resizeReadyContext());
    assert.equal(r.qa.localizedPageDescription(r.page),copy[locale].description);
    assert.ok(r.html.includes(copy[locale].description));
  });
  test(locale+" ready Resize omits complete internal footer and preserves real form controls",()=>{
    const context=resizeReadyContext(),saved=JSON.stringify(context),now=render(locale,"/image/resize",context),old=beforeRender(locale,"/image/resize",context);
    assert.equal(now.html.includes('<section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info">'),false);
    assert.equal(now.html.includes('portal-panel-list'),false);
    assert.deepEqual(controls(now.html),controls(old.html));
    assert.equal(JSON.stringify(context),saved);assert.equal(context.vaultItems[0].display_name,RESIZE_CUSTOMER);
    assert.equal(/<section[^>]*>\s*<\/section>/.test(now.html),false);
  });
  test(locale+" denied/loading/failed/empty/no-run keep actual guard and control state",()=>{
    for(const state of ["denied","loading","failed","empty","noRun"]){
      const context=resizeReadyContext();
      if(state==="denied")context.capabilities["image-operation-view"]=false;
      if(state==="loading"||state==="failed")context.assetVaultReadState=state;
      if(state==="empty"){context.vaultItems=[];context.imageOperationAssetReferences.items=[];}
      if(state==="noRun")context.capabilities["image-operation-resize"]=false;
      const saved=JSON.stringify(context),now=render(locale,"/image/resize",context),old=beforeRender(locale,"/image/resize",context);
      assert.deepEqual(controls(now.html),controls(old.html),state);
      assert.deepEqual([...now.html.matchAll(/data-state="([^"]+)"/g)].map(m=>m[1]),[...old.html.matchAll(/data-state="([^"]+)"/g)].map(m=>m[1]),state);
      assert.equal(JSON.stringify(context),saved,state);
      if(["denied","loading","failed"].includes(state))assert.equal(now.html.includes('data-portal-action="image-operation-resize"'),false,state);
      else assert.ok(/type="submit" disabled/.test(now.html),state);
    }
  });
  test(locale+" other route HTML/header/title and customer content remain BASE",()=>{
    const context={profile:{locale,displayName:RESIZE_CUSTOMER}},saved=JSON.stringify(context);
    for(const route of ["/documents/split","/documents/merge","/documents/compress","/documents","/chat","/dashboard","/image/enhance"]){
      const now=render(locale,route,context),old=beforeRender(locale,route,context);
      assert.equal(now.html,old.html,route);assert.equal(now.title,old.title,route);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context),route);
    }
    assert.equal(JSON.stringify(context),saved);
  });
  test(locale+" actual frozen catalogue adds only two localized entries; finite projection rejects mutations",()=>{
    const now=render(locale,"/image/resize",resizeReadyContext()),old=beforeRender(locale,"/image/resize",resizeReadyContext());
    const entries=Object.entries(now.messages[locale]),prior=Object.entries(old.messages[locale]);
    const added=[["imageResizeMetaUiTitle",copy[locale].title],["imageResizeMetaUiDescription",copy[locale].description]];
    assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(entries.slice(-2),added);
    assert.deepEqual(entries.slice(0,-2),prior);assert.deepEqual(resizePolishHistoricalSnapshot(entries,locale),prior);
    for(const[key]of added){
      assert.throws(()=>resizePolishHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed Image Resize polish/);
      assert.throws(()=>resizePolishHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?"UNKNOWN":value]),locale),/Unreviewed Image Resize polish/);
    }
    assert.throws(()=>resizePolishHistoricalSnapshot([...entries,added[0]],locale),/Unreviewed Image Resize polish/);
    const outside=["CUSTOMER_UNKNOWN","media studio Facebook TikTok literal"];
    assert.deepEqual(resizePolishHistoricalSnapshot([...entries,outside],locale),[...prior,outside]);
  });
}
const inverses={portal:resizePolishHistoricalPortalSource,i18n:resizePolishHistoricalI18nSource,pages:resizePolishHistoricalPagesSource,theme:resizePolishHistoricalThemeSource};
test("physical application equals exactly seven worker changes and protected integration stays byte-exact",()=>{
  const expected={...baseline};assert.equal(fixture.changes.length,7);
  for(const edit of fixture.changes){
    const key=Object.keys(files).find(k=>files[k]===edit.file);assert.ok(key);assert.equal(edit.count,1);
    assert.equal(expected[key].split(edit.old).length-1,1);expected[key]=expected[key].replace(edit.old,()=>edit.new);
  }
  for(const[key,file]of Object.entries(files)){
    const physical=lf(fs.readFileSync(file,"utf8")),raw=key==="i18n"?resizePlainHistoricalI18nSource(physical):physical,suffix=key[0].toUpperCase()+key.slice(1);
    assert.equal(raw,expected[key]);assert.equal(hash(raw),fixture.binding["candidate"+suffix]);
    assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);
    if(inverses[key]){assert.equal(inverses[key](raw),baseline[key]);assert.equal(inverses[key](baseline[key]),baseline[key]);}
  }
});
test("historical source projections fail closed on partial/duplicate changes and retain outside bytes",()=>{
  for(const[key,inverse]of Object.entries(inverses)){
    const raw=lf(fs.readFileSync(files[key],"utf8")),prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* media studio Facebook TikTok */";
    assert.equal(inverse(prefix+raw+suffix),prefix+baseline[key]+suffix);
    const edit=fixture.changes.find(e=>e.file===files[key]&&e.new);
    assert.throws(()=>inverse(raw+"\n"+edit.new),/Unreviewed Image Resize polish/);
    const mutated=key==="pages"?edit.new.replace("/image/resize","/image/UNKNOWN"):key==="theme"?edit.new.replace("var(--portal-text)","var(--UNKNOWN)"):edit.new.replace("imageResizeMetaUi","imageResizeMetaUnknown");
    assert.throws(()=>inverse(raw.replace(edit.new,mutated)),/Unreviewed Image Resize polish/);
  }
});
