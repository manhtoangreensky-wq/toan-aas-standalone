import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-usability-reviewed.json",import.meta.url),"utf8"));
const keys=["docPdfGuardUiTitle","docPdfGuardUiBody"],locales=["vi","en","zh"];
const copy={
  vi:{docPdfGuardUiTitle:"Chưa mở được công cụ PDF",docPdfGuardUiBody:"Không thể tải công cụ lúc này. Vui lòng tải lại trang."},
  en:{docPdfGuardUiTitle:"PDF tool could not be opened",docPdfGuardUiBody:"The tool could not be loaded right now. Please reload the page."},
  zh:{docPdfGuardUiTitle:"无法打开 PDF 工具",docPdfGuardUiBody:"目前无法加载工具，请重新加载页面。"}
};
const splitTail='/* Keep PDF split field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-split .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-split .portal-field-help {\n  color: var(--portal-muted);\n}\n';
export const PDF_USABILITY_COMPRESS_ADDITION='\n/* Keep PDF compression field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-optimize .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-optimize .portal-field-help {\n  color: var(--portal-muted);\n}\n';
const metadata='<div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div>';
const paragraphs=[
  "PDF Split chỉ bật khi cả Asset Vault và thư mục output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.",
  "PDF Merge chỉ bật khi cả Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.",
  "PDF Optimize chỉ bật khi cả Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider."
];
const guardEdits=["split","merge","optimize"].map((kind,index)=>{
  const head='      return `<article class="portal-page portal-pdf-'+kind+'">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div>';
  const tail='</div></div></section></article>`;';
  return {file:"static/portal/portal.js",old:head+"<h2>Document Operations đang ở chế độ an toàn</h2><p>"+paragraphs[index]+"</p>"+metadata+tail,
    new:head+'<h2>${safeText(uiText("docPdfGuardUiTitle", "Chưa mở được công cụ PDF"))}</h2><p>${safeText(uiText("docPdfGuardUiBody", "Không thể tải công cụ lúc này. Vui lòng tải lại trang."))}</p>'+tail,count:1};
});
const i18nOld="  verifyEqualKeysets();",i18nNew=locales.map(locale=>'  Object.assign(MESSAGES.'+locale+', {\n    docPdfGuardUiTitle: "'+copy[locale].docPdfGuardUiTitle+'",\n    docPdfGuardUiBody: "'+copy[locale].docPdfGuardUiBody+'"\n  });\n').join("")+"\n"+i18nOld;
const reviewed=[{file:"static/portal/portal-theme.css",old:splitTail,new:splitTail+PDF_USABILITY_COMPRESS_ADDITION,count:1},
  ...guardEdits,{file:"static/portal/portal-i18n.js",old:i18nOld,new:i18nNew,count:1}];
assert.deepEqual(fixture.changes,reviewed,"Unreviewed PDF usability fixture changes");
for(const locale of locales)assert.deepEqual(fixture[locale],copy[locale],"Unreviewed PDF usability fixture catalogue");
const hash=value=>createHash("sha256").update(value).digest("hex"),count=(value,part)=>value.split(part).length-1;
export function pdfUsabilityHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),"Unreviewed PDF usability locale");
  const scoped=entries.filter(([key])=>key.startsWith("docPdfGuardUi"));
  if(!scoped.length)return entries;
  assert.equal(scoped.length,2,"Unreviewed PDF usability missing/unknown/duplicate key");
  assert.deepEqual(scoped.map(([key])=>key),keys,"Unreviewed PDF usability key/order");
  assert.deepEqual(scoped,Object.entries(copy[locale]),"Unreviewed PDF usability value/order");
  assert.deepEqual(entries.slice(-2),scoped,"Unreviewed PDF usability keys must append");
  assert.equal(hash(JSON.stringify(scoped)),fixture.binding.catalogHashes[locale],"Unreviewed PDF usability catalogue hash");
  return entries.slice(0,-2);
}
function inverse(source,file){
  assert.equal(typeof source,"string","Unreviewed PDF usability source");
  const edits=reviewed.filter(edit=>edit.file===file);
  const historical=edits.every(edit=>count(source,edit.old)===1&&count(source,edit.new)===0);
  if(historical){assert.equal(source.includes("docPdfGuardUi"),false,"Unreviewed PDF usability residual key");return source;}
  assert.ok(edits.every(edit=>count(source,edit.new)===1),"Unreviewed PDF usability partial/changed/duplicate input");
  let value=source;
  for(const edit of [...edits].reverse())value=value.replace(edit.new,()=>edit.old);
  assert.equal(value.includes("docPdfGuardUi"),false,"Unreviewed PDF usability unknown/residual key");
  assert.ok(edits.every(edit=>count(value,edit.old)===1),"Unreviewed PDF usability duplicate baseline chunk");
  return value;
}
export const pdfUsabilityHistoricalPortalSource=value=>inverse(value,"static/portal/portal.js");
export const pdfUsabilityHistoricalI18nSource=value=>inverse(value,"static/portal/portal-i18n.js");
export function pdfUsabilityHistoricalCss(source){
  assert.equal(typeof source,"string","Unreviewed PDF usability CSS");
  const occurrences=count(source,PDF_USABILITY_COMPRESS_ADDITION);
  if(!occurrences)return source; // Unknown/changed bytes remain visible, never normalized away.
  assert.equal(occurrences,1,"Unreviewed PDF usability CSS duplicate addition");
  assert.ok(source.endsWith(PDF_USABILITY_COMPRESS_ADDITION),"Unreviewed PDF usability CSS location");
  const prior=source.slice(0,-PDF_USABILITY_COMPRESS_ADDITION.length);
  assert.ok(prior.endsWith(splitTail),"Unreviewed PDF usability CSS must follow the unchanged Split EOF block");
  return prior; // Strip Compress only. Split and all other bytes remain exact, including mixed line endings.
}
