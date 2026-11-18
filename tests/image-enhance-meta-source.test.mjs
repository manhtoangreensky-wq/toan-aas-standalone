import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageEnhanceMetaHistoricalPortalSource,imageEnhanceMetaHistoricalI18nSource,imageEnhanceMetaHistoricalPagesSource,imageEnhanceMetaHistoricalSnapshot} from "./helpers/image-enhance-meta-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-enhance-meta-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const base="b9815725d9e04ec4c6d3d5e8b854a71920688c54",lf=value=>value.replace(/\r\n/g,"\n");
const inverses={"static/portal/portal.js":imageEnhanceMetaHistoricalPortalSource,"static/portal/portal-i18n.js":imageEnhanceMetaHistoricalI18nSource,"copyfast_pages.py":imageEnhanceMetaHistoricalPagesSource};
test("Enhance metadata source equals five exact additions with every outside byte unchanged",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6}));let expected=before;
    for(const edit of edits.filter(row=>row.file===file)){assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
    const current=lf(fs.readFileSync(file,"utf8"));assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
  }
});
test("Enhance metadata inverses reject partial/unknown/duplicate/moved changes and preserve customer bytes",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    const source=lf(fs.readFileSync(file,"utf8")),selected=edits.filter(row=>row.file===file),edit=selected[0];
    const part=file.endsWith("portal-i18n.js")?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length);
    const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
    assert.equal(inverse(prefix+source+suffix),prefix+inverse(source)+suffix);
    assert.throws(()=>inverse(source+"\n"+part),/Unreviewed Image Enhance metadata/);
    assert.throws(()=>inverse(source.replace(part,part.replace("/image/edit","/image/UNKNOWN").replace("imageEnhanceMetaUiTitle","imageEnhanceMetaUiUNKNOWN"))),/Unreviewed Image Enhance metadata/);
    if(selected.length>1)assert.throws(()=>inverse(source.replace(part,"")),/Unreviewed Image Enhance metadata/);
    assert.throws(()=>inverse(source.replace(part,"")+"\n"+part),/Unreviewed Image Enhance metadata/);
  }
  const entries=[["customer","literal"],["imageEnhanceMetaUiTitle","Chỉnh ảnh"],["imageEnhanceMetaUiDescription","Chọn ảnh đã lưu, chỉnh màu và độ nét rồi tải bản PNG mới. Tệp gốc được giữ nguyên."]];
  assert.deepEqual(imageEnhanceMetaHistoricalSnapshot(entries,"vi"),[entries[0]]);
  assert.throws(()=>imageEnhanceMetaHistoricalSnapshot(entries.slice(0,2),"vi"),/Unreviewed Image Enhance metadata/);
});
