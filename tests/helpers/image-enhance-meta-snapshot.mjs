import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/image-enhance-meta-reviewed.json",import.meta.url));
assert.equal(createHash("sha256").update(raw).digest("hex"),"10b19e6677caea6c2f70b213aab524580321dcd07e6dbf6a4c48b0d41199d83e");
const fixture=JSON.parse(raw),edits=fixture.proposal.changes;
assert.equal(fixture.review.proposalExact,true);assert.equal(edits.length,5);
const fail="Unreviewed Image Enhance metadata",prefix="imageEnhanceMetaUi",count=(source,part)=>source.split(part).length-1;
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
        assert.equal(source.slice(start,end).includes('"/image/edit":'),false,fail+" partial shell");
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
export const imageEnhanceMetaHistoricalPortalSource=source=>inverse(source,"static/portal/portal.js");
export const imageEnhanceMetaHistoricalI18nSource=source=>inverse(source,"static/portal/portal-i18n.js");
export const imageEnhanceMetaHistoricalPagesSource=source=>inverse(source,"copyfast_pages.py");
export function imageEnhanceMetaHistoricalSnapshot(entries,locale){
  const copies={vi:["Chỉnh ảnh","Chọn ảnh đã lưu, chỉnh màu và độ nét rồi tải bản PNG mới. Tệp gốc được giữ nguyên."],
    en:["Edit images","Choose a saved image, adjust color and sharpness, then download a new PNG. The original file stays unchanged."],
    zh:["调整图像","选择已保存的图像，调整色彩和锐度，然后下载新的 PNG 文件。原文件保持不变。"]};
  assert.ok(Object.hasOwn(copies,locale),fail+" locale");
  const keys=[prefix+"Title",prefix+"Description"],owned=entries.filter(([key])=>key.startsWith(prefix));
  if(!owned.length)return entries;
  assert.equal(owned.length,2,fail+" partial/unknown catalogue");assert.deepEqual(owned.map(([key])=>key),keys,fail+" duplicate/reordered");
  assert.deepEqual(owned.map(([,value])=>value),copies[locale],fail+" changed catalogue");
  return entries.filter(([key])=>!keys.includes(key));
}
