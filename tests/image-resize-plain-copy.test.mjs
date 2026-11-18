import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {resizeCopyContext,resizeCopySlot,resizeCopyStateForKey} from "./helpers/image-resize-plain-copy-runtime.mjs";
import {resizePlainChanges,resizePlainHistoricalI18nSource as inverse,resizePlainHistoricalSnapshot as catalogBack} from "./helpers/image-resize-plain-copy-snapshot.mjs";
import {imageSharedHistoricalI18nSource,imageSharedHistoricalPortalSource} from "./helpers/image-shared-plain-copy-snapshot.mjs";
import {resizeControlHeightHistoricalThemeSource} from "./helpers/image-resize-control-height-snapshot.mjs";
import {pdfCompressMetaHistoricalPagesSource} from "./helpers/pdf-compress-meta-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-resize-plain-copy-reviewed.json",import.meta.url),"utf8"));
const physical=pageMetaSources(),source={...physical,i18n:imageSharedHistoricalI18nSource(physical.i18n),portal:imageSharedHistoricalPortalSource(physical.portal)},render=await pageMetaRenderer(source),locales=["vi","en","zh"],cache=new Map();
const lf=x=>x.replace(/\r\n/g,"\n"),hash=x=>createHash("sha256").update(x).digest("hex");
const base={...source,i18n:lf(execFileSync("git",["show",fixture.base+":static/portal/portal-i18n.js"],{encoding:"utf8",maxBuffer:30e6}))};
const priorRender=await pageMetaRenderer(base);
function view(locale,state){
  const key=locale+":"+state;
  if(!cache.has(key)){const context=resizeCopyContext(state),saved=JSON.stringify(context),result=render(locale,"/image/resize",context);assert.equal(JSON.stringify(context),saved);cache.set(key,result);}
  return cache.get(key);
}
for(const locale of locales)for(const[index,row]of fixture.rows.entries()){
  test((index>=12?"new-row ":"prior-row ")+locale+" actual "+row[0],()=>{
    const state=resizeCopyStateForKey(row[0]),expected=row[locales.indexOf(locale)+1].replace("{count}","1");
    assert.equal(resizeCopySlot(view(locale,state).html,row[0]),expected);
  });
}
const controls=html=>[...html.matchAll(/<(form|input|select|textarea|button|option)\b([^>]*)>/g)].map(m=>({
  tag:m[1],attributes:m[2].replace(/\sdata-portal-confirm="[^"]*"/g,"")
}));
for(const locale of locales){
  test(locale+" Image history updates only the three intended Resize labels and keeps behavior",()=>{
    const context=resizeCopyContext("card");
    context.imageHistoryReadState="ready";context.imageHistoryOperations=context.imageOperations;
    const now=render(locale,"/image/history",context),old=priorRender(locale,"/image/history",context);
    let restored=now.html;
    for(const key of ["resize.form.title","resize.fallbackName","field.resize.fit.crop"]){
      const edit=resizePlainChanges.find(e=>e.key===key),index=locales.indexOf(locale)+1;
      assert.ok(restored.includes(edit.newRow[index]),"History consumes "+key);
      restored=restored.replaceAll(edit.newRow[index],edit.oldRow[index]);
    }
    assert.equal(restored,old.html);assert.deepEqual(controls(now.html),controls(old.html));assert.equal(now.title,old.title);
  });
  test(locale+" actual controls, options, constraints, routes and guard states retain BASE semantics",()=>{
    for(const state of ["ready","guard","loading","failed","empty","noRun","disabled","card"]){
      const context=resizeCopyContext(state),now=view(locale,state),old=priorRender(locale,"/image/resize",context);
      assert.deepEqual(controls(now.html),controls(old.html),state);
      assert.deepEqual([...now.html.matchAll(/data-state="([^"]+)"/g)].map(m=>m[1]),[...old.html.matchAll(/data-state="([^"]+)"/g)].map(m=>m[1]),state);
      assert.equal(now.title,old.title);assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      assert.equal(/<section[^>]*>\s*<\/section>/.test(now.html),false);
      assert.equal(now.html.includes('portal-notice--info'),false);
    }
    const ready=view(locale,"ready").html;
    for(const name of ["target_width","target_height"]){
      const tag=ready.match(new RegExp('<input[^>]*name="'+name+'"[^>]*>'))?.[0];assert.ok(tag);
      assert.ok(tag.includes('min="128"')&&tag.includes('max="4096"')&&tag.includes('step="1"'));
    }
  });
  test(locale+" frozen catalogue preserves keys/order/customer entries and inverse rejects partial changes",()=>{
    const now=view(locale,"ready"),old=priorRender(locale,"/image/resize",resizeCopyContext());
    const entries=Object.entries(now.messages[locale]),previous=Object.entries(old.messages[locale]);
    assert.ok(Object.isFrozen(now.messages[locale]));assert.equal(entries.length,previous.length);
    assert.deepEqual(entries.map(([key])=>key),previous.map(([key])=>key));
    assert.deepEqual(catalogBack(entries,locale),previous);
    for(const row of fixture.rows){
      const key="imageOperationUi."+row[0];
      assert.throws(()=>catalogBack(entries.filter(([name])=>name!==key),locale),/Unreviewed Image Resize plain copy/);
      assert.throws(()=>catalogBack(entries.map(([name,value])=>[name,name===key?"UNKNOWN":value]),locale),/Unreviewed Image Resize plain copy/);
    }
    const outside=["CUSTOMER_UNKNOWN","media studio Facebook TikTok literal"];
    assert.deepEqual(catalogBack([...entries,outside],locale),[...previous,outside]);
  });
  test(locale+" other routes outside Image Operations and literal customer content stay unchanged",()=>{
    for(const route of ["/documents/split","/documents/merge","/documents/compress","/documents","/chat","/dashboard"]){
      const context={profile:{locale,displayName:'CUSTOMER media studio Facebook TikTok <img src=x onerror="literal">&'}},saved=JSON.stringify(context);
      const now=render(locale,route,context),old=priorRender(locale,route,context);
      assert.equal(now.html,old.html,route);assert.equal(now.title,old.title,route);assert.equal(JSON.stringify(context),saved);
    }
    const now=view(locale,"ready");assert.equal(now.html.includes('<img src=x'),false);assert.ok(now.html.includes("&lt;img"));
  });
}
test("actual catalogue equals exactly 33 reviewed rows and every other application file is exact BASE",()=>{
  let expected=base.i18n;
  for(const edit of resizePlainChanges){assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(source.i18n,expected);assert.equal(hash(base.i18n),fixture.binding.baselineI18n);assert.equal(hash(source.i18n),fixture.binding.candidateI18n);
  assert.equal(inverse(source.i18n),base.i18n);assert.equal(inverse(base.i18n),base.i18n);
  for(const[suffix,file]of [["Portal","static/portal/portal.js"],["Pages","copyfast_pages.py"],["Integration","static/portal/integration.js"],["Theme","static/portal/portal-theme.css"]]){
    const physical=lf(fs.readFileSync(file,"utf8")),raw=suffix==="Portal"?imageSharedHistoricalPortalSource(physical):suffix==="Theme"?resizeControlHeightHistoricalThemeSource(physical):suffix==="Pages"?pdfCompressMetaHistoricalPagesSource(physical):physical,before=lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:30e6}));
    assert.equal(raw,before,file);assert.equal(hash(raw),fixture.binding["candidate"+suffix]);
  }
});
test("finite row inverse rejects partial/duplicate/reordered/changed rows and preserves unknown outside bytes",()=>{
  const raw=source.i18n,prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* media studio Facebook TikTok */";
  assert.equal(inverse(prefix+raw+suffix),prefix+base.i18n+suffix);
  for(const edit of resizePlainChanges){
    if(edit.old!==edit.new)assert.throws(()=>inverse(raw.replace(edit.new,edit.old)),/Unreviewed Image Resize plain copy/);
    assert.throws(()=>inverse(raw+"\n"+edit.new),/Unreviewed Image Resize plain copy/);
    const row=[...edit.newRow];row[1]="UNKNOWN";const changed="    ["+row.map(v=>JSON.stringify(v)).join(", ")+"],";
    assert.throws(()=>inverse(raw.replace(edit.new,changed)),/Unreviewed Image Resize plain copy/);
  }
  const a=resizePlainChanges[0],b=resizePlainChanges[1];
  assert.throws(()=>inverse(raw.replace(a.new,"TEMP").replace(b.new,a.new).replace("TEMP",b.new)),/Unreviewed Image Resize plain copy/);
});
