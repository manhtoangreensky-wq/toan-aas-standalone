import fs from "node:fs";
import assert from "node:assert/strict";
import {pdfSplitMetaHistoricalPortalSource} from "./pdf-split-meta-snapshot.mjs";
import {operationReferenceFeedbackHistoricalI18nSource,operationReferenceFeedbackHistoricalSnapshot} from "./operation-reference-feedback-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-merge-fields-reviewed.json",import.meta.url),"utf8"));
const rows=[
  ["docPdfMergeUiSourceLabel","PDF thứ {position}","PDF {position}","第 {position} 个 PDF"],
  ["docPdfMergeUiSourceOptionalLabel","PDF thứ {position} (tùy chọn)","PDF {position} (optional)","第 {position} 个 PDF（可选）"],
  ["docPdfMergeUiSelect","Chọn PDF thứ {position}","Choose PDF {position}","选择第 {position} 个 PDF"],
  ["docPdfMergeUiNoExtra","Không thêm PDF","No additional PDF","不添加 PDF"],
  ["docPdfMergeUiOrderHelp","PDF được gộp theo thứ tự từ trên xuống dưới. Chọn các tệp trong kho tệp của bạn.","PDFs are merged from top to bottom. Choose files from your file vault.","PDF 将按从上到下的顺序合并。请从文件库中选择文件。"],
  ["docPdfMergeUiMinimumHelp","Chọn ít nhất hai PDF khác nhau.","Choose at least two different PDFs.","请至少选择两个不同的 PDF。"],
  ["docPdfMergeUiOptionalHelp","Để trống nếu không cần thêm tệp. Mỗi PDF chỉ được chọn một lần.","Leave this empty if no more files are needed. Each PDF can be selected only once.","无需添加更多文件时可留空。每个 PDF 只能选择一次。"]
];
const oldLabel='        label: `PDF nguồn ${position}${required ? "" : " (tùy chọn)"}`,';
const newLabel='        label: required\n          ? uiText("docPdfMergeUiSourceLabel", `PDF thứ ${position}`, { position })\n          : uiText("docPdfMergeUiSourceOptionalLabel", `PDF thứ ${position} (tùy chọn)`, { position }),';
const oldHelp='        emptyLabel: required ? `Chọn PDF thứ ${position}` : "Không thêm PDF",\n        required,\n        help: position === 1\n          ? "Thứ tự slot quyết định thứ tự trang output. Chỉ PDF active thuộc signed Web account hiện tại được liệt kê."\n          : position === 2\n            ? "Cần tối thiểu hai nguồn khác nhau. Không dùng URL, path hoặc file browser trong bước này."\n            : "Tùy chọn; để trống nếu không cần thêm nguồn. Một PDF chỉ có thể xuất hiện một lần."';
const newHelp='        emptyLabel: required\n          ? uiText("docPdfMergeUiSelect", `Chọn PDF thứ ${position}`, { position })\n          : uiText("docPdfMergeUiNoExtra", "Không thêm PDF"),\n        required,\n        help: position === 1\n          ? uiText("docPdfMergeUiOrderHelp", "PDF được gộp theo thứ tự từ trên xuống dưới. Chọn các tệp trong kho tệp của bạn.")\n          : position === 2\n            ? uiText("docPdfMergeUiMinimumHelp", "Chọn ít nhất hai PDF khác nhau.")\n            : uiText("docPdfMergeUiOptionalHelp", "Để trống nếu không cần thêm tệp. Mỗi PDF chỉ được chọn một lần.")';
const locales=["vi","en","zh"],keys=rows.map(row=>row[0]),marker="  verifyEqualKeysets();";
const addition=locales.map((locale,index)=>"  Object.assign(MESSAGES."+locale+", {\n"+rows.map(row=>"    "+row[0]+": "+JSON.stringify(row[index+1])).join(",\n")+"\n  });").join("\n\n")+"\n\n"+marker;
const edits=[{file:"static/portal/portal.js",count:1,old:oldLabel,new:newLabel},{file:"static/portal/portal.js",count:1,old:oldHelp,new:newHelp},{file:"static/portal/portal-i18n.js",count:1,old:marker,new:addition}];
assert.deepEqual(fixture.rows,rows,"Unreviewed PDF Merge fields rows");assert.deepEqual(fixture.changes,edits,"Unreviewed PDF Merge fields edits");
const count=(value,part)=>value.split(part).length-1,fail="Unreviewed PDF Merge fields";
const once=(value,old,next)=>{assert.equal(count(value,old),1,fail+" missing/changed/duplicate chunk");return value.replace(old,()=>next);};
export function pdfMergeFieldsHistoricalPortalSource(source){
  assert.equal(typeof source,"string",fail);
  source=pdfSplitMetaHistoricalPortalSource(source);
  if(!source.includes("docPdfMergeUi"))return source;
  const anchor="  function pdfMergeFormFields(";assert.equal(count(source,anchor),1,fail+" owner");
  const start=source.indexOf(anchor),end=source.indexOf("\n  function ",start+anchor.length);assert.ok(end>start,fail+" boundary");
  let part=source.slice(start,end);
  for(const edit of edits.slice(0,2).reverse()){
    assert.equal(count(source,edit.new),1,fail+" misplaced/duplicate new chunk");part=once(part,edit.new,edit.old);
  }
  const restored=source.slice(0,start)+part+source.slice(end);
  assert.equal(restored.includes("docPdfMergeUi"),false,fail+" partial/unknown/residual key");
  for(const edit of edits.slice(0,2))assert.equal(count(restored,edit.old),1,fail+" duplicate old chunk");
  return restored; // Exact scoped text only; no source normalization or whole-function masking.
}
export function pdfMergeFieldsHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);source=operationReferenceFeedbackHistoricalI18nSource(source);if(!source.includes("docPdfMergeUi"))return source;
  const result=once(source,addition,marker);
  assert.equal(result.includes("docPdfMergeUi"),false,fail+" partial/unknown/residual catalogue");return result;
}
export function pdfMergeFieldsHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");
  entries=operationReferenceFeedbackHistoricalSnapshot(entries,locale);
  const added=entries.filter(([key])=>key.startsWith("docPdfMergeUi"));if(!added.length)return entries;
  const expected=rows.map(row=>[row[0],row[locales.indexOf(locale)+1]]);
  assert.deepEqual(added,expected,fail+" missing/unknown/value/order/duplicate key");
  assert.deepEqual(entries.slice(-keys.length),expected,fail+" keys must append");
  return entries.slice(0,-keys.length); // Preserve all previous entries/order, including unknown outside keys.
}
