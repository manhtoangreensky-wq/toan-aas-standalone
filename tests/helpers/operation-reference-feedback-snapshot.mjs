import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/operation-reference-feedback-reviewed.json",import.meta.url),"utf8"));
const rows=[["failed","Chưa tải được tệp. Hãy thử lại.","Files could not be loaded. Please try again.","无法加载文件。请重试。"],
  ["page","Đã tải danh sách tệp.","File list loaded.","已加载文件列表。"],["cleared","Đã xóa bộ lọc.","Filter cleared.","已清除筛选。"],
  ["filtered","Đã lọc danh sách tệp.","File list filtered.","已筛选文件列表。"]];
const marker="  verifyEqualKeysets();",locales=["vi","en","zh"],prefix="operationReferenceFeedback.";
const helperOld="  function operationAssetReferenceListPath(kind, filter, offset) {";
const helperNew='  function operationReferenceFeedbackText(key, fallback) {\n    const i18n = window.TOANAASI18n;\n    const value = i18n && typeof i18n.t === "function" ? i18n.t("operationReferenceFeedback." + key) : "";\n    return typeof value === "string" && value ? value : fallback;\n  }\n\n'+helperOld;
const failedNew='        if (!refreshed) throw new Error(operationReferenceFeedbackText("failed", "Chưa tải được tệp. Hãy thử lại."));';
const success=kind=>'        toast(action === "'+kind+'-asset-reference-page"\n          ? operationReferenceFeedbackText("page", "Đã tải danh sách tệp.")\n          : (clear ? operationReferenceFeedbackText("cleared", "Đã xóa bộ lọc.") : operationReferenceFeedbackText("filtered", "Đã lọc danh sách tệp.")));';
const oldSuccess=kind=>'        toast(action === "'+kind+'-asset-reference-page" ? "Đã tải trang reference từ API owner-scoped." : (clear ? "Đã xóa bộ lọc reference riêng tư." : "Đã lọc reference riêng tư."));';
const catalog=locales.map((locale,index)=>"  Object.assign(MESSAGES."+locale+", {\n"+rows.map(row=>"    "+JSON.stringify(prefix+row[0])+": "+JSON.stringify(row[index+1])).join(",\n")+"\n  });").join("\n\n")+"\n\n"+marker;
const edits=[
  {file:"static/portal/integration.js",count:1,old:helperOld,new:helperNew},
  {file:"static/portal/integration.js",count:1,old:'        if (!refreshed) throw new Error("Không thể tải reference Document Operations an toàn. Hãy thử lại.");',new:failedNew},
  {file:"static/portal/integration.js",count:1,old:oldSuccess("document"),new:success("document")},
  {file:"static/portal/integration.js",count:1,old:'        if (!refreshed) throw new Error("Không thể tải reference Image Operations an toàn. Hãy thử lại.");',new:failedNew},
  {file:"static/portal/integration.js",count:1,old:oldSuccess("image-operation"),new:success("image-operation")},
  {file:"static/portal/portal-i18n.js",count:1,old:marker,new:catalog}
];
assert.deepEqual(fixture.rows,rows,"Unreviewed operation reference feedback rows");assert.deepEqual(fixture.changes,edits,"Unreviewed operation reference feedback edits");
const count=(source,part)=>source.split(part).length-1,fail="Unreviewed operation reference feedback";
const once=(source,old,next)=>{assert.equal(count(source,old),1,fail+" missing/changed/duplicate chunk");return source.replace(old,()=>next);};
function scoped(source,kind,old,next){
  const anchor='      if (["'+kind+'-asset-reference-filter", "'+kind+'-asset-reference-filter-clear", "'+kind+'-asset-reference-page"].includes(action)) {';
  assert.equal(count(source,anchor),1,fail+" action owner");
  const start=source.indexOf(anchor),end=source.indexOf("\n      if (",start+anchor.length);assert.ok(end>start,fail+" action boundary");
  return source.slice(0,start)+once(source.slice(start,end),old,next)+source.slice(end);
}
export function operationReferenceFeedbackHistoricalIntegrationSource(source){
  assert.equal(typeof source,"string",fail);if(!source.includes("operationReferenceFeedback"))return source;
  assert.equal(count(source,failedNew),2,fail+" partial/misplaced/duplicate failed-read chunks");
  let value=source;
  for(let index=4;index>=1;index--)value=scoped(value,index<3?"document":"image-operation",edits[index].new,edits[index].old);
  value=once(value,helperNew,helperOld);assert.equal(value.includes("operationReferenceFeedback"),false,fail+" unknown/residual integration code");
  return value; // No whole action-region masking and no newline normalization.
}
export function operationReferenceFeedbackHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);if(!source.includes(prefix))return source;
  const value=once(source,catalog,marker);assert.equal(value.includes(prefix),false,fail+" partial/unknown/residual catalogue");return value;
}
export function operationReferenceFeedbackHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");const added=entries.filter(([key])=>key.startsWith(prefix));if(!added.length)return entries;
  const expected=rows.map(row=>[prefix+row[0],row[locales.indexOf(locale)+1]]);
  assert.deepEqual(added,expected,fail+" missing/unknown/changed/duplicate/order keys");assert.deepEqual(entries.slice(-4),expected,fail+" keys must append");
  return entries.slice(0,-4); // Keep every existing or unknown outside entry, in its original order.
}
