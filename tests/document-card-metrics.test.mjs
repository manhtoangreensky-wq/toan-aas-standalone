import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {documentCardMetricsSources,documentCardMetricsRenderer} from "./helpers/document-card-metrics-runtime.mjs";
import {documentCardMetricsHistoricalSnapshot,documentCardMetricsHistoricalPortalSource,documentCardMetricsHistoricalI18nSource} from "./helpers/document-card-metrics-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/document-card-metrics-reviewed.json",import.meta.url),"utf8"));
const source=documentCardMetricsSources(),baseline=documentCardMetricsSources(true);
const actual=await documentCardMetricsRenderer(source),before=await documentCardMetricsRenderer(baseline);
const sessions=Object.fromEntries(["vi","en","zh"].map(locale=>[locale,{now:actual(locale,"/documents",{}),old:before(locale,"/documents",{})}]));
const kinds=["pdf_split","pdf_merge","pdf_optimize","image_to_pdf","pdf_to_images","pdf_to_word_text","image_ocr","pdf_ocr","pdf_ocr_word"];
const id="11111111-1111-4111-8111-111111111111",customer='CUSTOMER private verified media Studio Facebook TikTok <img src=x onerror="alert(1)">&.pdf';
const item=(kind,extra={})=>({id,kind,state:"completed",download_ready:true,original_filename:customer,source_page_count:2,output_page_count:2,
  source_count:3,selected_start_page:2,selected_end_page:4,byte_size:3072,input_byte_size:4096,saved_bytes:1024,saved_percent:25,
  language:"vi",completed_at:"2026-11-15T08:09:10Z",...extra});
const hash=value=>createHash("sha256").update(value).digest("hex"),plain=value=>JSON.parse(JSON.stringify(value));
const esc=(session,value)=>session.qa.safeText(String(value));
const freeze=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
function render(session,record,cap=true){
  const records=freeze([record]),context=freeze({path:"/documents/pdf",capabilities:{"document-operation-export-to-asset-vault":cap,"content-handoff-create":cap}});
  const saved=JSON.stringify({records,context}),html=session.qa.renderDocumentOperationCards(records,context);
  assert.equal(JSON.stringify({records,context}),saved);return html;
}
function cells(html){const all=[...html.matchAll(/<dd>([\s\S]*?)<\/dd>/g)];assert.equal(all.length,4);return all;}
function outside(actual,prior){
  const now=cells(actual),old=cells(prior);let projected=actual;
  for(let k=2;k>=0;k--)projected=projected.slice(0,now[k].index)+old[k][0]+projected.slice(now[k].index+now[k][0].length);
  assert.equal(projected,prior,"Only three metric dd cells may differ; all customer/control/date/status/rights markup stays exact");
}
const text={
  vi:{pages:"2 trang",pdf:"3 tệp PDF · 2 trang",images:"3 ảnh · 2 trang",pdfPages:"2 trang PDF",selected:"1 ảnh đã chọn",docx:"Tệp DOCX",pngZip:"2 ảnh PNG trong tệp ZIP",txt:"Văn bản TXT",checking:"Đang kiểm tra",none:"Chưa có tệp",notReduced:"Chưa giảm được dung lượng"},
  en:{pages:"Pages: 2",pdf:"PDF files: 3 · Pages: 2",images:"Images: 3 · Pages: 2",pdfPages:"PDF pages: 2",selected:"1 selected image",docx:"DOCX file",pngZip:"2 PNG images in a ZIP file",txt:"TXT text file",checking:"Checking",none:"No file yet",notReduced:"File size has not been reduced"},
  zh:{pages:"2 页",pdf:"3 个 PDF 文件 · 2 页",images:"3 张图片 · 2 页",pdfPages:"2 页 PDF",selected:"已选 1 张图片",docx:"DOCX 文件",pngZip:"ZIP 文件中包含 2 张 PNG 图片",txt:"TXT 文字文件",checking:"正在检查",none:"暂无文件",notReduced:"文件大小尚未减小"}
};
function defaultMetrics(kind,copy){
  const source=kind==="pdf_optimize"?"4.0 KB":kind==="pdf_merge"?copy.pdf:kind==="image_to_pdf"?copy.images:
    ["pdf_to_images","pdf_to_word_text","pdf_ocr_word"].includes(kind)?copy.pdfPages:kind==="image_ocr"?copy.selected:copy.pages;
  const output=kind==="pdf_optimize"?"3.0 KB":["pdf_to_word_text","pdf_ocr_word"].includes(kind)?copy.docx:
    kind==="pdf_to_images"?copy.pngZip:["pdf_ocr","image_ocr"].includes(kind)?copy.txt:copy.pages;
  return [source,output,kind==="pdf_optimize"?"1.0 KB · 25%":"3.0 KB"];
}
for(const locale of ["vi","en","zh"]){
  const {now,old}=sessions[locale],copy=text[locale];
  test(`${locale}: all nine actual branches translate metrics without changing any other card content or rights`,()=>{
    for(const kind of kinds)for(const cap of [true,false,"true",undefined]){
      const record=item(kind),a=render(now,record,cap),b=render(old,record,cap);
      assert.deepEqual(cells(a).slice(0,3).map(match=>match[1]),defaultMetrics(kind,copy).map(value=>esc(now,value)));
      outside(a,b);assert.ok(a.includes(esc(now,customer)));assert.equal(a.includes("<img"),false);
      assert.equal(a.includes("&amp;lt;img"),false);
    }
  });
  test(`${locale}: failed/guarded/processing states do not claim a downloadable Word/image/text file`,()=>{
    for(const kind of kinds)for(const state of ["processing","guarded","failed","unavailable"])for(const ready of [true,false,"true"]){
      const record=item(kind,{state,download_ready:ready}),a=render(now,record),b=render(old,record);
      const expected=defaultMetrics(kind,copy);
      if(["pdf_to_word_text","pdf_ocr_word","pdf_to_images","pdf_ocr","image_ocr"].includes(kind))expected[1]=copy.none;
      assert.deepEqual(cells(a).slice(0,3).map(match=>match[1]),expected.map(value=>esc(now,value)));
      outside(a,b);assert.equal(now.qa.documentOperationDownloadPath(record),old.qa.documentOperationDownloadPath(record));
    }
  });
  test(`${locale}: numeric strings, zero, malformed counts/pages and byte/savings branches retain exact coercion policy`,()=>{
    const c=fixture[locale],t=(key,params={})=>Object.entries(params).reduce((value,[name,v])=>value.replace("{"+name+"}",v),c["docMetricUi"+key]);
    for(const [extra,count,pages]of [[{source_count:"1",source_page_count:"1",output_page_count:"1"},"1","1"],
      [{source_count:0,source_page_count:0,output_page_count:0},"1","0"],
      [{source_count:"BAD",source_page_count:"BAD",output_page_count:"BAD"},"1",null],
      [{source_count:-2,source_page_count:-2,output_page_count:-2},"1","-2"],
      [{source_count:1.5,source_page_count:1.5,output_page_count:1.5},"1.5",null]]){
      for(const kind of ["pdf_split","pdf_merge","image_to_pdf","pdf_to_images"]){
        const record=item(kind,extra),a=render(now,record),b=render(old,record),metric=cells(a);
        const wanted=kind==="pdf_merge"||kind==="image_to_pdf"?t(kind==="pdf_merge"?"PdfCount":"ImagesCount",{count})+(pages===null?"":t("PagesSuffix",{pages})):
          pages===null?copy.checking:t(kind==="pdf_to_images"?"PdfPages":"Pages",{pages});
        assert.equal(metric[0][1],esc(now,wanted));
        const output=kind==="pdf_to_images"?Number(extra.output_page_count)===1?c.docMetricUiPngImage:t("PngZip",{count:String(Number(extra.output_page_count)||0)}):
          pages===null?copy.none:t("Pages",{pages});
        assert.equal(metric[1][1],esc(now,output));outside(a,b);
      }
    }
    const cases=[
      [{input_byte_size:"BAD",source_page_count:"BAD",byte_size:0,saved_bytes:0,saved_percent:25},[copy.checking,copy.none,copy.notReduced]],
      [{input_byte_size:"BAD",source_page_count:2,byte_size:"BAD",saved_bytes:-1,saved_percent:25},[copy.pages,"—",copy.notReduced]],
      [{input_byte_size:null,byte_size:1023,saved_bytes:1024,saved_percent:"BAD"},["0 B","1023 B","1.0 KB"]],
      [{input_byte_size:-1,byte_size:1048576,saved_bytes:1024,saved_percent:0},["—","1.0 MB","1.0 KB · 0%"]]
    ];
    for(const [extra,wanted]of cases){const record=item("pdf_optimize",extra),a=render(now,record),b=render(old,record);assert.deepEqual(cells(a).slice(0,3).map(match=>match[1]),wanted.map(value=>esc(now,value)));outside(a,b);}
    for(const ready of [false,"true",undefined]){
      for(const kind of ["pdf_to_word_text","pdf_ocr_word","pdf_to_images","pdf_ocr","image_ocr"]){
        const record=item(kind,{download_ready:ready}),a=render(now,record),b=render(old,record);
        assert.equal(cells(a)[1][1],esc(now,copy.none));outside(a,b);
      }
    }
  });
  test(`${locale}: translated phrases are escaped once, live locale switches and fallback work, empty history is unchanged`,()=>{
    const hostile='<img src=x onerror="alert(1)"> \'&';
    const html=now.qa.withUiText((key,value)=>key.startsWith("docMetricUi")?hostile:value,()=>render(now,item("pdf_merge",{byte_size:0})));
    for(const match of cells(html).slice(0,3))assert.ok(match[1].includes(esc(now,hostile)));
    assert.equal(html.includes("<img"),false);assert.equal(html.includes("&amp;lt;img"),false);
    const next=locale==="vi"?"en":locale==="en"?"zh":"vi";
    try{now.setLocale(next);assert.deepEqual(cells(render(now,item("image_ocr"))).slice(0,3).map(match=>match[1]),defaultMetrics("image_ocr",text[next]).map(value=>esc(now,value)));}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>render(now,item("image_ocr")));
    assert.deepEqual(cells(fallback).slice(0,3).map(match=>match[1]),defaultMetrics("image_ocr",text.vi).map(value=>esc(now,value)));
    assert.equal(now.qa.renderDocumentOperationCards([]),old.qa.renderDocumentOperationCards([]));
  });
  test(`${locale}: thirteen ordered frozen keys retain prior catalogue; missing/unknown/value mutations are rejected`,()=>{
    const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale]));
    assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(entries.slice(0,prior.length),prior);
    assert.deepEqual(entries.slice(prior.length),Object.entries(fixture[locale]));
    assert.deepEqual(documentCardMetricsHistoricalSnapshot(entries,locale),prior);
    for(const key of Object.keys(fixture[locale])){
      assert.throws(()=>documentCardMetricsHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed document metrics/);
      assert.throws(()=>documentCardMetricsHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?"UNKNOWN":v]),locale),/Unreviewed document metrics/);
    }
    assert.throws(()=>documentCardMetricsHistoricalSnapshot([...entries,["docMetricUiUnknown","UNKNOWN"]],locale),/Unreviewed document metrics/);
  });
}
test("the exact finite four-edit inverse restores BASE and cannot swallow partial or outside changes",()=>{
  assert.equal(hash(source.portal),fixture.binding.candidatePortal);assert.equal(hash(source.i18n),fixture.binding.candidateI18n);
  assert.equal(documentCardMetricsHistoricalPortalSource(source.portal),baseline.portal);assert.equal(documentCardMetricsHistoricalI18nSource(source.i18n),baseline.i18n);
  assert.equal(documentCardMetricsHistoricalPortalSource(baseline.portal),baseline.portal);assert.equal(documentCardMetricsHistoricalI18nSource(baseline.i18n),baseline.i18n);
  assert.throws(()=>documentCardMetricsHistoricalPortalSource(source.portal.replace("docMetricUiChecking","UNKNOWN")),/Unreviewed document metrics/);
  assert.throws(()=>documentCardMetricsHistoricalI18nSource(source.i18n.replace("docMetricUiChecking:","UNKNOWN:")),/Unreviewed document metrics/);
  const suffix="\n// CUSTOMER private verified media TikTok";
  assert.ok(documentCardMetricsHistoricalPortalSource(source.portal+suffix).endsWith(suffix));
});
