import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pageMetaRenderer,pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {resizePolishHistoricalPortalSource,resizePolishHistoricalI18nSource,resizePolishHistoricalPagesSource} from "./helpers/image-resize-polish-snapshot.mjs";
import {pdfSplitMetaHistoricalPortalSource, pdfSplitMetaHistoricalI18nSource,
  pdfSplitMetaHistoricalPagesSource,pdfSplitMetaHistoricalSnapshot} from "./helpers/pdf-split-meta-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-split-meta-reviewed.json",import.meta.url),"utf8"));
const live=pageMetaSources(),source={portal:resizePolishHistoricalPortalSource(live.portal),i18n:resizePolishHistoricalI18nSource(live.i18n),pages:resizePolishHistoricalPagesSource(live.pages)},render=await pageMetaRenderer(source),lf=value=>value.replace(/\r\n/g,"\n");
assert.match(fixture.base,/^[a-f0-9]{40}$/);
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,lf(execFileSync("git",["show",fixture.base+":"+file],{encoding:"utf8",maxBuffer:30e6}))]));
const priorRender=await pageMetaRenderer(baseline),hash=value=>createHash("sha256").update(value).digest("hex");
const copy={
  vi:{title:"Tách PDF",description:"Tạo tệp PDF từ một trang hoặc dải trang liên tiếp trong tài liệu đã lưu."},
  en:{title:"Split PDF",description:"Create a PDF from one page or a consecutive page range in a saved document."},
  zh:{title:"拆分 PDF",description:"从已保存的文档中提取单页或连续页面，创建 PDF。"}
};
for(const locale of ["vi","en","zh"]){
  test(locale+" actual Split PDF title and header use the interface language",()=>{
    const r=render(locale,"/documents/split");
    assert.equal(r.qa.localizedPageTitle(r.page,r.context),copy[locale].title);
    assert.equal(r.title,copy[locale].title+" · TOAN AAS");
    const header=r.qa.renderHeader(r.page,r.context);
    assert.ok(header.includes(copy[locale].title),"Visible header must agree with title");
  });
  test(locale+" actual Split PDF description is useful and localized",()=>{
    const r=render(locale,"/documents/split");
    assert.equal(r.qa.localizedPageDescription(r.page),copy[locale].description);
    assert.ok(r.html.includes(copy[locale].description),"Hero must use the same localized description");
  });
  test(locale+" outside route HTML/title and customer text stay unchanged",()=>{
    const customer='CUSTOMER media studio Facebook TikTok <img src=x onerror="literal">&';
    for(const route of ["/documents","/documents/merge","/image/resize","/chat","/dashboard"]){
      const context={profile:{locale,displayName:customer}},saved=JSON.stringify(context);
      const now=render(locale,route,context),old=priorRender(locale,route,context);
      assert.equal(now.title,old.title);assert.equal(now.html,old.html);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      assert.equal(JSON.stringify(context),saved);
    }
  });
  test(locale+" two frozen catalogue entries append exactly and preserve every prior entry",()=>{
    const now=render(locale,"/documents/split"),old=priorRender(locale,"/documents/split");
    const entries=Object.entries(now.messages[locale]),previous=Object.entries(old.messages[locale]);
    const added=[["docPdfMetaUiSplitTitle",copy[locale].title],["docPdfMetaUiSplitDescription",copy[locale].description]];
    assert.ok(Object.isFrozen(now.messages[locale]));
    assert.deepEqual(entries.slice(0,-2),previous);assert.deepEqual(entries.slice(-2),added);
    assert.deepEqual(pdfSplitMetaHistoricalSnapshot(entries,locale),previous);
    for(const[key]of added){
      assert.throws(()=>pdfSplitMetaHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed PDF Split metadata/);
      assert.throws(()=>pdfSplitMetaHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?"UNKNOWN":value]),locale),/Unreviewed PDF Split metadata/);
    }
    assert.throws(()=>pdfSplitMetaHistoricalSnapshot([...entries,added[0]],locale),/Unreviewed PDF Split metadata/);
    assert.throws(()=>pdfSplitMetaHistoricalSnapshot([...previous,...added.toReversed()],locale),/Unreviewed PDF Split metadata/);
    assert.throws(()=>pdfSplitMetaHistoricalSnapshot([...entries,["docPdfMetaUiUnknown","UNKNOWN"]],locale),/Unreviewed PDF Split metadata/);
    const outside=["customerOutside","media studio Facebook TikTok"];
    assert.deepEqual(pdfSplitMetaHistoricalSnapshot([...entries,outside],locale),[...previous,outside]);
  });
}
test("actual three source files equal exactly five worker substitutions, all outside bytes protected",()=>{
  assert.equal(fixture.changes.length,5);const expected={...baseline};
  for(const edit of fixture.changes){
    const key=Object.keys(files).find(key=>files[key]===edit.file);assert.ok(key);assert.equal(edit.count,1);
    assert.equal(expected[key].split(edit.old).length-1,1);expected[key]=expected[key].replace(edit.old,()=>edit.new);
  }
  assert.deepEqual(source,expected);
  for(const[key,inverse]of [["portal",pdfSplitMetaHistoricalPortalSource],["i18n",pdfSplitMetaHistoricalI18nSource],["pages",pdfSplitMetaHistoricalPagesSource]]){
    const suffix=key[0].toUpperCase()+key.slice(1);
    assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);
    assert.equal(inverse(source[key]),baseline[key]);assert.equal(inverse(baseline[key]),baseline[key]);
  }
});
test("finite source inverses reject partial/changed/duplicated/misplaced additions and retain outside CRLF",()=>{
  const inverses={portal:pdfSplitMetaHistoricalPortalSource,i18n:pdfSplitMetaHistoricalI18nSource,pages:pdfSplitMetaHistoricalPagesSource};
  for(const edit of fixture.changes){
    const key=Object.keys(files).find(key=>files[key]===edit.file),inverse=inverses[key];
    if(key==="i18n"){
      const partial=edit.new.replace('    docPdfMetaUiSplitTitle: "Tách PDF",\n',"");
      assert.throws(()=>inverse(source[key].replace(edit.new,partial)),/Unreviewed PDF Split metadata/);
    }else assert.throws(()=>inverse(source[key].replace(edit.new,edit.old)),/Unreviewed PDF Split metadata/);
    assert.throws(()=>inverse(source[key]+"\n"+edit.new),/Unreviewed PDF Split metadata/);
    const changed=key==="pages"?edit.new.replace("/documents/split","/documents/UNKNOWN"):edit.new.replace("docPdfMetaUi","docPdfMetaUnknown");
    assert.throws(()=>inverse(source[key].replace(edit.new,changed)),/Unreviewed PDF Split metadata/);
    if(key==="portal")assert.throws(()=>inverse(source[key].replace(edit.new,edit.old)+"\n"+edit.new),/Unreviewed PDF Split metadata/);
  }
  for(const[key,inverse]of Object.entries(inverses)){
    const prefix="\r\n/* CUSTOMER prefix */\r\n",suffix="\r\n/* CUSTOMER media studio Facebook TikTok */";
    assert.equal(inverse(prefix+source[key]+suffix),prefix+baseline[key]+suffix);
  }
});
