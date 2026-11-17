import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {resizeGuidanceRenderer,resizeGuidanceSources,resizeReadyContext,resizeVisibleGuidance,RESIZE_CUSTOMER} from "./helpers/image-resize-guidance-runtime.mjs";
import {imageResizeGuidanceHistoricalI18nSource as inverse,imageResizeGuidanceHistoricalSnapshot as catalogBack} from "./helpers/image-resize-guidance-snapshot.mjs";
import {pdfSplitMetaHistoricalI18nSource,pdfSplitMetaHistoricalPortalSource,pdfSplitMetaHistoricalSnapshot} from "./helpers/pdf-split-meta-snapshot.mjs";
import {resizePolishHistoricalPortalSource,resizePolishHistoricalI18nSource,resizePolishHistoricalThemeSource} from "./helpers/image-resize-polish-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-guidance-reviewed.json",import.meta.url),"utf8"));
const live=resizeGuidanceSources(),source={portal:resizePolishHistoricalPortalSource(live.portal),i18n:resizePolishHistoricalI18nSource(live.i18n)},lf=value=>value.replace(/\r\n/g,"\n"),hash=value=>createHash("sha256").update(value).digest("hex");
assert.match(fixture.base,/^[a-f0-9]{40}$/);
const baseline=Object.fromEntries([["portal","static/portal/portal.js"],["i18n","static/portal/portal-i18n.js"]]
  .map(([key,file])=>[key,lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:15e6}))]));
const render=await resizeGuidanceRenderer(source),beforeRender=await resizeGuidanceRenderer(baseline),locales=["vi","en","zh"];
const expected={
  vi:{form:"Chọn ảnh, kích thước và cách đặt ảnh cho tệp PNG mới.",ready:"Tệp gốc được giữ nguyên. Bạn có thể tải PNG sau khi tạo xong.",boundary:"Chọn cách cắt ảnh, thêm nền trắng hoặc làm mờ nền."},
  en:{form:"Choose an image, size and placement for the new PNG.",ready:"The original stays unchanged. Download the PNG when it is ready.",boundary:"Choose center cropping, white padding or a blurred background."},
  zh:{form:"为新 PNG 选择图像、尺寸和布局。",ready:"原文件将保持不变。PNG 创建完成后即可下载。",boundary:"选择居中裁剪、白色留边或模糊背景。"}
};
for(const locale of locales){
  for(const key of ["form","ready","boundary"])test(locale+" actual ready Resize "+key+" gives useful customer guidance",()=>{
    const context=resizeReadyContext(),saved=JSON.stringify(context),result=render(locale,"/image/resize",context);
    assert.equal(JSON.stringify(context),saved);
    assert.equal(resizeVisibleGuidance(result.html)[key],expected[locale][key]);
    assert.ok(result.html.includes('data-portal-action="image-operation-resize"'));
    assert.ok(result.html.includes('name="source_asset_id"'));assert.ok(result.html.includes('name="target_width"'));
    assert.equal(context.vaultItems[0].display_name,RESIZE_CUSTOMER);
  });
  test(locale+" only the three ready copy slots change, with every control/customer byte preserved",()=>{
    const context=resizeReadyContext(),now=render(locale,"/image/resize",context),old=beforeRender(locale,"/image/resize",context);
    const previous=resizeVisibleGuidance(old.html);let restored=now.html;
    for(const key of ["form","ready","boundary"]){
      const value=expected[locale][key];assert.equal(restored.split(value).length-1,1);
      restored=restored.replace(value,()=>previous[key]);
    }
    assert.equal(restored,old.html,"No empty panel, route, selection, permission, markup or customer-content change");
    assert.equal(now.title,old.title);assert.deepEqual(JSON.parse(JSON.stringify(now.context)),JSON.parse(JSON.stringify(old.context)));
  });
  test(locale+" non-ready states and denied/empty controls remain actual BASE behavior",()=>{
    for(const state of ["loading","failed","denied","empty","noRun"]){
      const context=resizeReadyContext();
      if(state==="loading"||state==="failed")context.assetVaultReadState=state;
      if(state==="denied")context.capabilities["image-operation-view"]=false;
      if(state==="empty"){context.vaultItems=[];context.imageOperationAssetReferences.items=[];}
      if(state==="noRun")context.capabilities["image-operation-resize"]=false;
      const saved=JSON.stringify(context),now=render(locale,"/image/resize",context),old=beforeRender(locale,"/image/resize",context);
      let restored=now.html;
      for(const [key,suffix]of [["form","resize.form.description"],["boundary","resize.boundary.description"]]){
        if(restored.includes(expected[locale][key])){
          const row=fixture.rows.find(row=>row.key===suffix);restored=restored.replace(expected[locale][key],()=>row.old[locales.indexOf(locale)]);
        }
      }
      assert.equal(restored,old.html);assert.equal(JSON.stringify(context),saved);
      assert.equal(now.html.includes(expected[locale].ready),false,"No ready promise in non-runnable states");
    }
  });
  test(locale+" frozen catalogue keeps every key/order/outside value and rejects partial mutations",()=>{
    const now=render(locale,"/image/resize",resizeReadyContext()),old=beforeRender(locale,"/image/resize",resizeReadyContext());
    assert.ok(Object.isFrozen(now.messages[locale]));
    const entries=pdfSplitMetaHistoricalSnapshot(Object.entries(now.messages[locale]),locale),prior=Object.entries(old.messages[locale]);
    assert.deepEqual(catalogBack(entries,locale),prior);assert.deepEqual(catalogBack(prior,locale),prior);
    assert.equal(entries.length,prior.length);
    for(const row of fixture.rows){
      const key="imageOperationUi."+row.key;
      assert.throws(()=>catalogBack(entries.filter(([name])=>name!==key),locale),/Unreviewed Image Resize guidance/);
      assert.throws(()=>catalogBack(entries.map(([name,value])=>[name,name===key?"UNKNOWN":value]),locale),/Unreviewed Image Resize guidance/);
      assert.throws(()=>catalogBack([...entries,entries.find(([name])=>name===key)],locale),/Unreviewed Image Resize guidance/);
    }
    const outside=["CUSTOMER_UNKNOWN","media studio Facebook TikTok literal"];
    assert.deepEqual(catalogBack([...entries,outside],locale),[...prior,outside]);
  });
}
test("the actual full catalogue is exactly the three worker rows and all other application files remain BASE",()=>{
  assert.equal(fixture.changes.length,3);assert.equal(fixture.rows.length,3);
  let expectedSource=baseline.i18n;
  for(const edit of fixture.changes){assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);assert.equal(expectedSource.split(edit.old).length-1,1);expectedSource=expectedSource.replace(edit.old,()=>edit.new);}
  const historicalI18n=pdfSplitMetaHistoricalI18nSource(source.i18n);
  assert.equal(historicalI18n,expectedSource);assert.equal(hash(historicalI18n),fixture.binding.candidateI18n);
  assert.equal(hash(baseline.i18n),fixture.binding.baselineI18n);assert.equal(inverse(source.i18n),baseline.i18n);assert.equal(inverse(baseline.i18n),baseline.i18n);
  for(const[file,key]of [["static/portal/portal.js","portal"],["static/portal/integration.js","integration"],["static/portal/portal-theme.css","theme"]]){
    const raw=lf(fs.readFileSync(file,"utf8")),old=lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:15e6}));
    const current=key==="portal"?pdfSplitMetaHistoricalPortalSource(raw):key==="theme"?resizePolishHistoricalThemeSource(raw):raw;
    assert.equal(current,old);assert.equal(hash(current),fixture.binding[key]);
  }
});
test("finite source projection rejects changed, partial, duplicate, moved or reordered rows and preserves CRLF outside",()=>{
  for(const edit of fixture.changes){
    assert.throws(()=>inverse(source.i18n.replace(edit.new,edit.old)),/Unreviewed Image Resize guidance/);
    assert.throws(()=>inverse(source.i18n+"\n"+edit.new),/Unreviewed Image Resize guidance/);
    assert.throws(()=>inverse(source.i18n.replace(edit.new,edit.new.replace('", "','", "UNKNOWN'))),/Unreviewed Image Resize guidance/);
    assert.throws(()=>inverse(source.i18n.replace(edit.new,"")+"\n"+edit.new),/Unreviewed Image Resize guidance/);
  }
  const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* media studio Facebook TikTok */";
  assert.equal(inverse(prefix+source.i18n+suffix),prefix+baseline.i18n+suffix);
  assert.equal(inverse(prefix+suffix),prefix+suffix);
  const first=fixture.changes[0],second=fixture.changes[1];
  assert.throws(()=>inverse(source.i18n.replace(first.new,"TEMP").replace(second.new,first.new).replace("TEMP",second.new)),/Unreviewed Image Resize guidance/);
});
