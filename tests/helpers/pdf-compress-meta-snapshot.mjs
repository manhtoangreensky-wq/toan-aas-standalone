import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {imageToPdfGuardHistoricalPortalSource} from "./image-to-pdf-guard-snapshot.mjs";
import {imageEnhanceHelpHistoricalI18nSource,imageEnhanceHelpHistoricalSnapshot} from "./image-enhance-help-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-compress-meta-reviewed.json",import.meta.url),"utf8"));
const hash=value=>createHash("sha256").update(value).digest("hex");
assert.equal(hash(fixture.expectedRaw),"b3d1bd271b4d2ae39a7873d9906c6aa20429da68eea4f5ddee624781d7632ab2");
assert.equal(hash(fixture.proposalRaw),"225227707e2b7179359e62614a33b956d4b0439f426f955577522cfedb33506b");
const edits=JSON.parse(fixture.expectedRaw),proposal=JSON.parse(fixture.proposalRaw);
assert.deepEqual(proposal.changes,edits);assert.equal(edits.length,5);
const fail="Unreviewed PDF Compress metadata",prefix="pdfCompressMetaUi";
const count=(source,part)=>source.split(part).length-1;
function inverse(source,file){
  assert.equal(typeof source,"string",fail);
  const selected=edits.filter(edit=>edit.file===file);
  const additions=selected.map(edit=>file.endsWith("portal-i18n.js")?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length));
  const found=additions.map(part=>count(source,part));
  if(found.every(value=>value===0)){
    if(file.endsWith(".py")){
      for(const edit of selected){
        const start=source.indexOf(edit.old),end=source.indexOf("\n}",start);
        assert.ok(start>=0&&end>start,fail+" dictionary");
        assert.equal(source.slice(start,end).includes('"/documents/compress":'),false,fail+" partial shell");
      }
    }else assert.equal(source.includes(prefix),false,fail+" partial/unknown source");
    return source;
  }
  assert.ok(found.every(value=>value===1),fail+" partial/duplicate addition");
  for(const[index,edit]of selected.entries()){
    const part=additions[index],point=source.indexOf(part);
    if(file.endsWith("portal-i18n.js")){
      assert.ok(source.slice(point+part.length).startsWith(edit.old),fail+" moved catalogue");
    }else if(file.endsWith(".py")){
      assert.equal(source.slice(point-edit.old.length,point),edit.old,fail+" moved shell");
    }else{
      const owner=index===0?"  function localizedPageTitle(":"  function localizedPageDescription(";
      const start=source.indexOf(owner),end=source.indexOf("\n  function ",start+owner.length);
      assert.ok(start>=0&&point>start&&end>point,fail+" moved branch");
    }
  }
  let result=source;
  for(const part of additions)result=result.replace(part,"");
  if(!file.endsWith(".py"))assert.equal(result.includes(prefix),false,fail+" unknown namespace");
  return result;
}
export const pdfCompressMetaHistoricalPortalSource=source=>inverse(imageToPdfGuardHistoricalPortalSource(source),"static/portal/portal.js");
export const pdfCompressMetaHistoricalI18nSource=source=>inverse(imageEnhanceHelpHistoricalI18nSource(source),"static/portal/portal-i18n.js");
export const pdfCompressMetaHistoricalPagesSource=source=>inverse(source,"copyfast_pages.py");
export const pdfCompressMetaHistoricalSources=source=>({...source,
  portal:pdfCompressMetaHistoricalPortalSource(source.portal),
  i18n:pdfCompressMetaHistoricalI18nSource(source.i18n),
  pages:pdfCompressMetaHistoricalPagesSource(source.pages)});
const copies={
  vi:["Nén PDF","Giảm dung lượng PDF khi có thể. Tệp gốc được giữ nguyên."],
  en:["Compress PDF","Reduce a PDF's file size where possible. The original stays unchanged."],
  zh:["压缩 PDF","在可行时减小 PDF 文件大小。原文件将保持不变。"]
};
export function pdfCompressMetaHistoricalSnapshot(entries,locale){
  entries=imageEnhanceHelpHistoricalSnapshot(entries,locale);
  assert.ok(Object.hasOwn(copies,locale),fail+" locale");
  const keys=[prefix+"Title",prefix+"Description"],owned=entries.filter(([key])=>key.startsWith(prefix));
  if(!owned.length)return entries;
  assert.equal(owned.length,2,fail+" partial/unknown catalogue");
  assert.deepEqual(owned.map(([key])=>key),keys,fail+" duplicate/reordered catalogue");
  assert.deepEqual(owned.map(([,value])=>value),copies[locale],fail+" changed catalogue");
  return entries.filter(([key])=>!keys.includes(key));
}
