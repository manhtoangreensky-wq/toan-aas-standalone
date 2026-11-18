import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {imageEnhanceMetaHistoricalPortalSource,imageEnhanceMetaHistoricalI18nSource,imageEnhanceMetaHistoricalPagesSource,imageEnhanceMetaHistoricalSnapshot} from "./image-enhance-meta-snapshot.mjs";
const raw=fs.readFileSync(new URL("../fixtures/image-to-pdf-meta-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"6168254dabd2ba87f5364368ea3bf6383bb1a00cb3d746bb9250af913516c08f");
const fixture=JSON.parse(raw),edits=fixture.proposal.changes;
assert.equal(fixture.review.proposalExact,true);assert.equal(edits.length,5);
const fail="Unreviewed Image-to-PDF metadata",prefix="imageToPdfMetaUi",count=(source,part)=>source.split(part).length-1;
function inverse(source,file){
  assert.equal(typeof source,"string",fail);
  const selected=edits.filter(edit=>edit.file===file),catalog=file.endsWith("portal-i18n.js");
  const additions=selected.map(edit=>catalog?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length));
  const found=additions.map(part=>count(source,part));
  if(found.every(value=>value===0)){
    if(file.endsWith(".py")){
      for(const edit of selected){
        const start=source.indexOf(edit.old),end=source.indexOf("\n}",start);
        if(start<0)continue;
        assert.ok(end>start,fail+" dictionary");
        assert.equal(source.slice(start,end).includes('"/documents/image-to-pdf":'),false,fail+" partial shell");
      }
    }else assert.equal(source.includes(prefix),false,fail+" partial/unknown source");
    return source;
  }
  assert.ok(found.every(value=>value===1),fail+" partial/duplicate addition");
  for(const[index,edit]of selected.entries()){
    const part=additions[index],point=source.indexOf(part);
    if(catalog)assert.ok(source.slice(point+part.length).startsWith(edit.old),fail+" moved catalogue");
    else if(file.endsWith(".py"))assert.equal(source.slice(point-edit.old.length,point),edit.old,fail+" moved shell");
    else{
      const owner=index===0?"  function localizedPageTitle(":"  function localizedPageDescription(";
      const start=source.indexOf(owner),end=source.indexOf("\n  function ",start+owner.length);
      assert.ok(start>=0&&point>start&&end>point,fail+" moved branch");
    }
  }
  let result=source;for(const part of additions)result=result.replace(part,"");
  if(!file.endsWith(".py"))assert.equal(result.includes(prefix),false,fail+" unknown namespace");
  return result;
}
export const imageToPdfMetaHistoricalPortalSource=source=>inverse(imageEnhanceMetaHistoricalPortalSource(source),"static/portal/portal.js");
export const imageToPdfMetaHistoricalI18nSource=source=>inverse(imageEnhanceMetaHistoricalI18nSource(source),"static/portal/portal-i18n.js");
export const imageToPdfMetaHistoricalPagesSource=source=>inverse(imageEnhanceMetaHistoricalPagesSource(source),"copyfast_pages.py");
export function imageToPdfMetaHistoricalSnapshot(entries,locale){
  entries=imageEnhanceMetaHistoricalSnapshot(entries,locale);
  const copies={vi:["Ảnh thành PDF","Chọn ảnh và ghép thành một tệp PDF. Ảnh gốc được giữ nguyên."],
    en:["Images to PDF","Choose images and combine them into one PDF file. The original images stay unchanged."],
    zh:["图像转 PDF","选择图像并合成为一个 PDF 文件。原图像保持不变。"]};
  assert.ok(Object.hasOwn(copies,locale),fail+" locale");
  const keys=[prefix+"Title",prefix+"Description"],owned=entries.filter(([key])=>key.startsWith(prefix));
  if(!owned.length)return entries;
  assert.equal(owned.length,2,fail+" partial/unknown catalogue");assert.deepEqual(owned.map(([key])=>key),keys,fail+" duplicate/reordered");
  assert.deepEqual(owned.map(([,value])=>value),copies[locale],fail+" changed catalogue");
  return entries.filter(([key])=>!keys.includes(key));
}
